# Adaptive AI Interviewer

A first-stage technical interview application built with React, Tailwind CSS, Django, Channels and local Qwen models.

The application separates live interviewing, safety/misuse monitoring and final candidate evaluation so each model has one focused responsibility.

## Architecture

```text
Candidate browser
    |
    | voice or typed text
    v
React + Tailwind
    |
    | WebSocket / HTTP
    v
Django + Channels
    |
    +-- Qwen3-ASR-1.7B             speech -> text
    +-- Qwen3.5-9B                 realtime interviewer
    +-- Qwen3-TTS-0.6B             text -> speech
    +-- Qwen3Guard-Gen-4B          immediate content safety
    +-- Qwen3.5-4B                 accumulated misuse monitoring
    |
    v
Interview transcript
    |
    | live models unload after interview
    v
Qwen3.6-27B INT8
    |
    +-- one reasoning pass per evaluation question
    +-- synthesis reasoning pass
    +-- final decision reasoning pass
    +-- constrained PROGRESS / NOT_PROGRESS output
```

The job description, evaluator questions, company knowledge and prompts are ordinary project files. They are not copied into the database.

## Project structure

```text
backend/                    Django application
config/                     Editable role, company and runtime configuration
config/company/             Company RAG documents
docs/                       Technical documentation
frontend/                   React application source
prompts/                    AI system prompts
package.json                Root Node entry point
requirements.txt            All normal Python dependencies
vite.config.js              Root Vite/Tailwind configuration
```

The database stores only runtime application data such as interview sessions, transcript turns, criterion assessments, results and candidate review requests.

## Requirements

- Python 3.12+
- Node.js and npm
- ffmpeg
- NVIDIA CUDA/PyTorch support for real-model mode
- Two RTX 3090 GPUs are the target real-model configuration

On Arch Linux, install the audio system tools if needed:

```bash
sudo pacman -S ffmpeg sox
```

## Python setup

Create and activate the virtual environment from the project root:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install the Python dependencies:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Qwen speech package compatibility

The agreed ASR and TTS models currently publish conflicting exact Transformers pins: `qwen-asr` 0.0.6 requires Transformers 4.57.6, while `qwen-tts` 0.1.1 declares Transformers 4.57.3. The Qwen ASR package uses Hugging Face Transformers as its backend and is retained here because it lets the complete Qwen stack stay on the compatible Transformers 4.57.x line.

`requirements.txt` installs Qwen3-ASR and Transformers 4.57.6. Install Qwen3-TTS afterwards without dependency resolution so pip does not downgrade Transformers:

```bash
pip install --no-deps qwen-tts==0.1.1
```

This is the only model-specific installation exception. It keeps the agreed Qwen models unchanged while avoiding the current upstream metadata conflict.

## Frontend setup

Install the root Node dependencies:

```bash
npm install
```

There is no separate `frontend/package.json`.

## Database setup

Run normal Django migrations directly when required:

```bash
python backend/manage.py migrate
```

For schema development, use Django normally:

```bash
python backend/manage.py makemigrations
python backend/manage.py migrate
```

There are no custom seed/evaluate/interview management commands. Interviewing and evaluation are part of the normal web application flow.

## Run the application

Development uses one command from the project root:

```bash
npm run dev
```

The root command uses `./.venv/bin/python` for Django, so the virtual environment does not need to be activated again just to start the application.

This starts:

- Django on `http://127.0.0.1:8000`
- Vite on `http://127.0.0.1:5173`

Open:

```text
http://127.0.0.1:5173
```

Vite proxies `/api` and `/ws` to Django, so the browser interacts with the project as one application.

## Build

Build the React frontend from the project root:

```bash
npm run build
```

The production frontend bundle is written to `frontend/dist/`.

## Tests

Run the project checks with:

```bash
npm test
```

This runs Django checks, the Python test suite and a production Vite build.

## Runtime configuration

The checked-in development defaults live in:

```text
config/runtime.example.toml
```

For local changes create:

```text
config/runtime.toml
```

`runtime.toml` is ignored by Git and overrides the example automatically.

The project defaults to mock models so the full web flow can be tested without downloading model weights:

```toml
[models]
mode = "mock"
```

For real inference change it to:

```toml
[models]
mode = "real"
```

## Editable interview content

Change the role without touching Python code:

```text
config/job_description.md
config/evaluation_questions.txt
```

Company RAG knowledge lives in:

```text
config/company/*.md
```

The application reads these files directly.

AI prompts live in:

```text
prompts/interviewer.txt
prompts/misuse.txt
prompts/evaluator_question.txt
prompts/evaluator_synthesis.txt
prompts/final_choice.txt
prompts/final_output.txt
```

## Accessibility

The candidate can answer by microphone or by typing and can switch between them during the same interview. Interviewer responses are available as both text and speech.

The UI also provides transcript display, optional speech-transcription confirmation, replay, question rephrasing, extra thinking time, interviewer voice muting, speech-speed control, keyboard operation and screen-reader-friendly status updates.

See `docs/ACCESSIBILITY.md` for the design details.

## Model lifecycle

In real mode the live interview models remain loaded while an interview is active. Once the interview finishes, the live suite is unloaded and Qwen3.6-27B is loaded in INT8 across both GPUs for extended reasoning.

After evaluation, the evaluator unloads and the live models are restored for the next interview.

See `docs/MODELS.md` and `docs/ARCHITECTURE.md` for details.
