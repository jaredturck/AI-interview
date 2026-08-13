# Adaptive AI Interviewer

A first-stage technical interview application built with React, Tailwind CSS, Django, Channels and a fixed local Qwen model stack.

The project is intentionally purpose-built rather than configurable as a generic model platform. The live interviewer gathers technical evidence, the safety subsystem protects the conversation, and the final evaluator makes the binary stage-one progression decision.

## Core flow

```text
Candidate browser
    |
    | voice or typed text
    v
React + Tailwind
    |
    | HTTP + authenticated WebSocket
    v
Django + Channels
    |
    +-- Qwen3-ASR-1.7B-hf        speech -> text
    +-- Qwen3.5-9B               adaptive interviewer
    +-- Qwen3-TTS-1.7B           text -> speech
    +-- Qwen3Guard-Gen-4B        immediate content safety
    +-- Qwen3.5-4B               accumulated misuse monitoring
    |
    v
Stored text transcript
    |
    | live models unload after the interview
    v
Qwen3.6-27B INT8
    |
    +-- one deep reasoning pass per evaluation criterion
    +-- one final reasoning pass across the whole assessment
    +-- constrained PROGRESS / NOT_PROGRESS output
```

The job description and evaluation questions are ordinary files under `config/`. Prompts live under `prompts/`. RAG/company knowledge is deliberately not implemented in this version; it is listed in `TODO.md` for a separate design pass.

## Project structure

```text
backend/                    Django application
config/                     Job description and evaluator criteria
docs/                       Architecture, security, performance and testing notes
frontend/                   React application source
prompts/                    AI prompts
package.json                Root Node development/build/test interface
requirements.txt            Python dependencies
vite.config.js              Vite/Tailwind configuration
```

The SQLite database stores runtime application data: accounts, interview sessions, transcript turns, criterion assessments, outcomes and candidate-requested human reviews.

## Requirements

- Python 3.12+
- Node.js and npm
- ffmpeg, git and cmake
- NVIDIA CUDA toolkit (`nvcc`) and PyTorch support
- two RTX 3090 GPUs for the intended real-model deployment

On Arch Linux:

```bash
sudo pacman -S ffmpeg cmake git
```

## Python setup

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Qwen3-TTS runs through the native `qwentts.cpp` shared library so the Python environment can remain on Transformers 5. The application uses the source-faithful BF16 GGUF conversion of `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice` and the `vivian` English female speaker.

Build the pinned qwentts.cpp ABI used by the Python binding:

```bash
mkdir -p ~/.cache/adaptive-ai-interviewer
git clone --recurse-submodules https://github.com/ServeurpersoCom/qwentts.cpp.git ~/.cache/adaptive-ai-interviewer/qwentts.cpp
cd ~/.cache/adaptive-ai-interviewer/qwentts.cpp
git checkout a8a7716b530e49fed537c57711247c12fbbb903c
git submodule update --init --recursive
cmake -S . -B build -DGGML_CUDA=ON -DQWEN_SHARED=ON -DCMAKE_CUDA_ARCHITECTURES=86
cmake --build build -j "$(nproc)"
```

Download the matching BF16 talker and codec:

```bash
mkdir -p ~/.cache/adaptive-ai-interviewer/qwen3-tts
hf download Serveurperso/Qwen3-TTS-GGUF \
    qwen-talker-1.7b-customvoice-BF16.gguf \
    qwen-tokenizer-12hz-BF16.gguf \
    --local-dir ~/.cache/adaptive-ai-interviewer/qwen3-tts
```

The Django process loads `libqwen.so` directly with `ctypes`; there is no second Python environment or local TTS server. If CUDA rejects Arch's current host compiler, configure CMake with a CUDA-supported GCC using `-DCMAKE_CUDA_HOST_COMPILER=/path/to/g++`.

## Frontend setup

```bash
npm install
```

There is one root `package.json`; the frontend does not have a separate package file.

## Database setup

Run Django migrations normally:

```bash
python backend/manage.py migrate
```

To create an admin account:

```bash
python backend/manage.py createsuperuser
```

The Django admin is available at `/admin/` through the backend server.

## Run the application

```bash
npm run dev
```

This starts Django and Vite together:

- Django: `http://127.0.0.1:8000`
- React/Vite: `http://127.0.0.1:5173`

Open:

```text
http://127.0.0.1:5173
```

Vite proxies `/api` and `/ws` to Django. Candidates create an account, sign in, and conduct the complete interview through the browser.

## Build

```bash
npm run build
```

The production frontend bundle is written to `frontend/dist/`.

## Tests

```bash
npm test
```

This runs Django checks, the Python test suite and a production Vite build. Tests inject deterministic fake model objects directly; production code has no mock-model mode.

## Editable interview content

Change the role and final evaluation rubric without changing Python code:

```text
config/job_description.md
config/evaluation_questions.txt
```

Prompts:

```text
prompts/interviewer.txt
prompts/misuse.txt
prompts/evaluator_question.txt
prompts/final_choice.txt
prompts/final_output.txt
```

## Candidate accounts

Candidates must create an account before starting an interview. Django's normal authentication/session system is used for HTTP and WebSocket ownership. Each interview belongs to its authenticated account and appears on the candidate account page.

After an automated outcome, the candidate can request human review through the application. Django admin provides internal access to interview sessions, transcripts, criterion evaluations and review requests.

## Accessibility

Candidates can answer by voice, typing, or switch between the two. Interviewer responses are presented as both text and speech.

The interface also provides:

- visible transcript/captions;
- optional ASR transcript confirmation and correction;
- replay and rephrase controls;
- an `I need a moment` control;
- interviewer voice mute;
- adjustable speech playback speed;
- keyboard-operable controls;
- screen-reader status announcements;
- reduced-motion support.

See `docs/ACCESSIBILITY.md`.

## Model lifecycle

The live stack is lazy-loaded on the first interview and stays resident while the system is interviewing. A normal disconnected-but-unfinished interview releases the worker but leaves the live weights resident for fast reuse.

Once an interview finishes, the evaluator atomically takes ownership of the dual-GPU worker, unloads the live models and loads Qwen3.6-27B in INT8 across both GPUs. After evaluation, the evaluator unloads and the worker returns to idle.

One dual-3090 host supports one live interview or one final evaluation at a time in this V1 architecture.

See `docs/MODELS.md`, `docs/ARCHITECTURE.md` and `docs/PERFORMANCE.md`.

## Production notes

The checked-in Django settings are development defaults. Production deployment requires a strong `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=false`, production hosts/origins, TLS, a production ASGI server, rate limiting at the deployment boundary, and an explicit privacy/retention policy for candidate data.

See `docs/DEPLOYMENT.md` and `docs/SECURITY.md`.
