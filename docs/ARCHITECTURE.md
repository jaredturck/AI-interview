# Architecture

## System map

```mermaid
flowchart LR
    Browser[React + TypeScript] -->|JSON API| API[Django]
    Browser <-->|Authenticated WebSocket| WS[Django Channels]
    API --> DB[(SQLite / application DB)]
    WS --> Runtime[Resident model suite]
    Runtime --> DB
    DB --> Eval[Resident Qwen3.5-9B evaluation]
    Admin[Django Admin] --> API
```

| Boundary | Responsibility |
| --- | --- |
| React | Candidate routing, microphone/media state, transcript UI and accessibility controls. |
| Django JSON APIs | Authentication, jobs, applications, interview setup/status and review requests. |
| Channels | One live interview connection, audio turn state and model orchestration. |
| Model runtime | Serialized inference ownership over one permanently resident dual-GPU model suite. |
| Database | Recruitment state, confirmed transcript text, criterion assessments and outcomes. |

Django does not render candidate pages. Production serves the React SPA and proxies `/api`, `/ws` and `/admin` to Django.

## Recruitment data

```mermaid
flowchart TD
    User[Django User] --> Application[JobApplication]
    Job[Job] --> Application
    Application --> Interview[InterviewSession]
    Interview --> Turns[ConversationTurn]
    Interview --> Answers[EvaluationAnswer]
    Interview --> Review[HumanReviewRequest]
```

`Job` is an immutable recruitment snapshot containing candidate-facing metadata, the authored description and evaluation rubric. Updating `config/` affects new jobs only.

## Live interview

Typed input enters interview policy directly. Voice input first passes the turn-detection pipeline documented in [VOICE_PIPELINE.md](VOICE_PIPELINE.md).

```mermaid
flowchart LR
    Input[Confirmed candidate text] --> GuardIn[Qwen3Guard]
    GuardIn --> Misuse[Qwen3.5-4B misuse]
    Misuse --> Interviewer[Qwen3.5-9B shared model]
    Interviewer --> GuardOut[Qwen3Guard]
    GuardOut --> Text[Assistant transcript]
    GuardOut --> TTS[Qwen3-TTS WAV]
```

The opening question uses a non-persisted internal user instruction so the model receives a valid chat shape without inventing candidate evidence.

## Runtime ownership

```mermaid
stateDiagram-v2
    [*] --> Idle
    Idle --> Interview: reserve interview
    Interview --> Idle: unfinished disconnect
    Interview --> Evaluation: interview completes
    Evaluation --> Idle: evaluation finishes
```

All models remain loaded in every state. `ModelRuntime` only serializes active inference so one live interview or one final evaluation generates at a time. Development `runserver` preloads the complete stack in the serving child; other ASGI processes can lazy-load it on first use.

## Evaluation

```mermaid
flowchart LR
    Input[Job + transcript + criteria] --> Batch[Criterion microbatches]
    Batch --> Qwen[Resident Qwen3.5-9B INT8]
    Qwen --> Answers[EvaluationAnswer rows]
    Answers --> Reason[Final reasoning]
    Reason --> Choice[Constrained PROGRESS / NOT_PROGRESS]
```

The evaluator uses Transformers directly. Criteria are independent and processed in small batches to bound dynamic VRAM while the auxiliary stack remains resident. The final decision still depends on all completed criterion assessments. Inference failure becomes `evaluation_failed`; it never fabricates a recruitment outcome.

## Persistence and privacy boundary

Persisted: accounts, jobs, applications, interview state, confirmed transcript text, evaluation answers, outcome and review requests.

Not persisted: raw microphone audio, temporary transcript typing indicators, model chain-of-thought.
