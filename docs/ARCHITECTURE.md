# Architecture

## Responsibilities

The project uses three logical AI subsystems.

### 1. Realtime interviewer

- Browser microphone or typed text enters the same interview session.
- Spoken input is decoded to 16 kHz mono PCM and transcribed by Qwen3-ASR-1.7B.
- The candidate turn is moderated before generation.
- The misuse monitor evaluates the accumulated transcript.
- Qwen3.5-9B generates a short adaptive interviewer turn.
- The generated turn is moderated before speech synthesis.
- Qwen3-TTS-0.6B generates the audible interviewer response.
- The assistant text is always sent to the browser independently of audio playback.

The interviewer gathers evidence; it never decides progression.

### 2. Safety and misuse

Qwen3Guard-Gen-4B handles immediate content safety on candidate input and interviewer output.

Qwen3.5-4B separately evaluates the transcript as one of three actions:

- `CONTINUE`
- `REDIRECT`
- `TERMINATE`

The misuse prompt deliberately requires sustained, strong evidence before termination. A redirect only injects a temporary instruction into the next interviewer generation. A termination produces a normal friendly closing turn and ends the live connection; it does not itself create a candidate result.

### 3. Final evaluator

Qwen3.6-27B runs only after the live interview has ended.

For each role-specific rubric question:

```text
job description + full transcript + one criterion
                       ↓
                 reasoning pass
                       ↓
              concise assessment
```

After all assessments:

```text
job description + transcript + all assessments
                       ↓
                  synthesis pass
                       ↓
                    synthesis
                       ↓
       constrained non-thinking choice pass
                       ↓
             PROGRESS / NOT_PROGRESS
```

Raw reasoning text inside model thinking blocks is discarded rather than persisted.

## Application services

Django owns durable state and orchestration. Model code sits behind `ModelRuntime` / model-suite methods so mock and real inference use the same application paths.

The WebSocket owns the live interaction protocol. HTTP is used for bootstrap, interview creation, result/status polling and candidate review submissions.

## Capacity model

One Python ASGI process owns one dual-GPU worker. Capacity is process-local by design in V1.

`ModelRuntime` provides an atomic handoff from the active interview to final evaluation so a second interview cannot claim the GPUs between the closing turn and evaluator startup.

The frontend polls `/api/bootstrap/` while the worker is busy and enables new interviews after capacity returns.

## Persistence

The core transcript table stores only:

- interview reference;
- `user` or `assistant` role;
- text;
- timestamp.

Candidate name/email are optional session fields. Evaluation answers and human-review requests are separate records because they belong to later workflow stages rather than conversation profiling.

Raw microphone audio is not persisted by the application.
