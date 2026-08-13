# Adaptive AI Interviewer

A local-first stage-one technical interview platform built with Django, Channels, React and Tailwind. It deliberately separates live interviewing, safety/misuse control and final candidate evaluation so each model has one narrow responsibility.

## System overview

```text
Candidate browser
    ├─ microphone ──> Qwen3-ASR-1.7B ─┐
    └─ typed text ──────────────────────┤
                                        v
                              Qwen3Guard-Gen-4B
                                        |
                              Qwen3.5-4B misuse monitor
                                        |
                              Qwen3.5-9B interviewer
                                        |
                              Qwen3Guard-Gen-4B
                                        |
                              Qwen3-TTS-0.6B
                                        |
                         text + audio back to browser

After the interview:
    job description + complete transcript
                |
         Qwen3.6-27B INT8
                |
      one reasoning pass per criterion
                |
          synthesis reasoning pass
                |
        constrained binary choice
                |
       PROGRESS / NOT_PROGRESS
```

The live interviewer never decides whether a candidate progresses. The safety subsystem can redirect or end the live session, but the final evaluator independently makes the stage-one decision from the available evidence.

## V1 capabilities

- Voice interview over a single WebSocket connection.
- Typed answers as a first-class alternative to speech.
- Every interviewer response provided as both visible text and audio.
- Optional candidate confirmation/correction of ASR text before it reaches the interviewer.
- Replay, rephrase, pause and interviewer-voice controls.
- Adjustable local speech playback speed.
- Adaptive interviewer prompt: job description as a compass, not a script.
- Lightweight local BM25 RAG over editable company documents.
- QwenGuard input/output moderation plus a separate forgiving misuse monitor.
- Simple ordered transcript storage; microphone audio is not persisted.
- Fixed role-specific evaluation rubric with a separate reasoning pass per criterion.
- Qwen3.6-27B INT8 final evaluator using both RTX 3090s.
- Mechanically constrained final output: `PROGRESS` or `NOT_PROGRESS` only.
- Candidate-triggered human-review request form.
- Mock model mode for application development and automated tests without downloading model weights.

## Accessibility

Accessibility is part of the normal interaction rather than a separate disability mode. Candidates can speak, type or switch between both; questions are presented in text and audio; microphone turns end only when the candidate explicitly presses **Finish speaking**; and the interviewer is prompted to change question specificity when the current style is not helping the candidate communicate useful information.

The UI also uses semantic controls, visible keyboard focus, large control targets, ARIA status/live regions, reduced-motion support, question replay/rephrasing and optional transcript correction. See `docs/ACCESSIBILITY.md`.

## Repository layout

```text
backend/                  Django, Channels, models, APIs, WebSocket and model services
frontend/                 React, Tailwind and accessible interview interface
config/                   Runtime example, demo role, rubric and company knowledge
prompts/                  Short prompts for the dedicated AI roles
docs/                     Architecture, accessibility, security, models and testing
scripts/                  Setup, run and validation helpers
```

## Quick start — mock mode

Python 3.12 is recommended because it matches the Qwen ASR guidance and the intended production environment.

```bash
./scripts/setup_dev.sh
./scripts/run_backend.sh
```

In another terminal:

```bash
./scripts/run_frontend.sh
```

Open `http://127.0.0.1:5173`.

`setup_dev.sh` creates `config/runtime.toml` from the safe example file, creates `.venv`, installs the web/test dependencies, migrates the database, seeds the demo role/company documents and installs the frontend packages.

The repository itself does **not** ship `config/runtime.toml`; it is ignored so deployment secrets/settings do not accidentally enter version control.

## Real model mode

Install the AI dependencies in the same Python 3.12 environment:

```bash
cd backend
../.venv/bin/pip install -r requirements-ai.txt
```

Then edit `config/runtime.toml`:

```toml
[models]
mode = "real"
```

The selected live stack is:

- `Qwen/Qwen3-ASR-1.7B` — BF16, GPU 1
- `Qwen/Qwen3.5-9B` — INT8, non-thinking, GPU 0
- `Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice` — BF16, GPU 0
- `Qwen/Qwen3Guard-Gen-4B` — INT8, GPU 1
- `Qwen/Qwen3.5-4B` — INT8, non-thinking misuse monitor, GPU 1

The final evaluator is `Qwen/Qwen3.6-27B`, INT8, thinking enabled. It receives both GPUs after the interview ends.

In real mode the ASGI process preloads the live model suite before accepting interviews. Model downloads therefore happen during startup rather than during a candidate's first turn. `run_backend.sh` also marks any evaluation interrupted by a previous backend process restart as an operational failure so candidates are not left permanently waiting.

## GPU lifecycle

V1 intentionally treats one dual-3090 machine as one exclusive interview/evaluation worker:

```text
load live models
      ↓
conduct one interview
      ↓
finish closing audio
      ↓
atomically hand worker to evaluator
      ↓
unload live models
      ↓
load Qwen3.6-27B INT8 across both GPUs
      ↓
criterion passes + synthesis + binary choice
      ↓
unload evaluator
      ↓
reload live models
      ↓
capacity reopens
```

Run exactly one Daphne process for one dual-GPU worker. Horizontal scaling should add GPU workers instead of spawning multiple Daphne processes that independently believe they own the same GPUs.

## Audio behaviour

The browser sends MediaRecorder chunks over the WebSocket while the candidate is speaking. V1 deliberately waits for **Finish speaking** before decoding/transcribing the utterance; it does not use aggressive silence-based turn detection. This gives candidates unrestricted pauses inside a speaking turn.

If the browser disconnects unexpectedly, the backend allows a short configurable reconnect grace period (120 seconds by default). If the candidate does not reconnect, the existing transcript is closed and sent to evaluation so an abandoned tab cannot monopolize the GPU worker for the full interview limit.

Qwen3-TTS supports streaming, but the included simple production adapter currently synthesizes each short interviewer reply as one WAV before returning it. The model's own turns are intentionally short, so this is a reasonable V1 tradeoff and keeps the integration simpler. Incremental TTS is a future latency optimization, not a prerequisite for the architecture.

## Conversation and evidence

The durable interview evidence stays intentionally simple:

```text
assistant: "Could you tell me about a project you've worked on recently?"
user: "I built an internal Django API with PostgreSQL."
assistant: "What part of that API did you personally build?"
```

The database stores ordered conversation turns and timestamps. Separate tables hold criterion assessments, the binary result and candidate-requested review submissions. The application does not build a hidden disability/personality profile.

## Job and company configuration

Edit:

- `config/job_description.md`
- `config/evaluation_questions.txt`
- `config/company/*.md`

Then reseed:

```bash
cd backend
../.venv/bin/python manage.py seed_demo
```

Company documents use lightweight BM25 retrieval so company questions do not consume another embedding model or GPU allocation.

## Prompt configuration

Prompts live in `prompts/` and are intentionally short:

- `interviewer.txt`
- `misuse.txt`
- `evaluator_question.txt`
- `evaluator_synthesis.txt`
- `final_choice.txt`

The interviewer prompt contains desired interviewing behaviour rather than a large blacklist. Immediate safety is handled externally by QwenGuard. Misuse is handled by its own transcript monitor. The final evaluator treats transcript content as evidence rather than instructions.

See `docs/PROMPTS.md`.

## Evaluation flow

For every rubric item the evaluator receives the full job description, complete transcript and one criterion. It reasons about only that criterion and stores a concise assessment, not raw chain-of-thought.

After all criteria, the model performs a separate synthesis pass. A final non-thinking pass uses token-level constrained decoding so only `PROGRESS` or `NOT_PROGRESS` can be emitted.

The decision threshold is deliberately: **is a stage-two human technical interview worthwhile?** It is not a final hiring decision.

## Tests and static checks

```bash
./scripts/check.sh
```

With dependencies installed this runs:

- Python compilation/static project validation;
- Django system checks;
- pytest backend/API/WebSocket tests using mock models;
- the production frontend build when `node_modules` exists.

See `docs/TESTING.md` for what was validated during generation of this repository and what still must be tested on the actual GPU workstation.

## Production checklist

Before real hiring deployment:

- replace the example Django secret and configure real hosts/origins;
- place Django behind TLS and a reverse proxy with HTTP/WebSocket rate limits;
- use PostgreSQL rather than SQLite for production durability/concurrency;
- define transcript/evaluation/review retention and deletion policies;
- run accessibility testing with disabled and neurodivergent participants;
- benchmark real ASR/TTS/LLM latency and VRAM on the target workstation;
- benchmark the INT8 evaluator against a representative labelled interview set;
- red-team the guard/misuse boundaries and transcript prompt-injection resistance;
- obtain appropriate UK employment/data-protection review for notices, automated decisions and the candidate review process;
- establish an operational process for candidate-requested human reviews.

See `docs/SECURITY.md` and `docs/DEPLOYMENT.md`.
