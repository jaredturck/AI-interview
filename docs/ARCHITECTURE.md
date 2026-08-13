# Architecture

## Product boundaries

The candidate product and staff product intentionally use different presentation layers:

```text
Candidate: React + TypeScript + Tailwind + React Router
           -> Django JSON APIs
           -> Django Channels WebSocket

Staff:     custom Django AdminSite
           -> Django templates + project admin CSS
```

Django does not render candidate pages. Production web serving must return the React SPA for candidate routes while proxying `/api`, `/ws` and `/admin` to Django.

## Recruitment domain

The persistent relationship is:

```text
Django User
    -> JobApplication
        -> Job
        -> InterviewSession
            -> ConversationTurn
            -> EvaluationAnswer
            -> HumanReviewRequest
```

`Job` is an immutable recruitment snapshot containing candidate-facing metadata, the exact job description and the exact evaluation rubric. Staff create a new Job from the current files under `config/`; changing those files later cannot mutate an existing interview's context.

A candidate can have at most one `JobApplication` per Job. Each application has at most one `InterviewSession`.

## Candidate API and routing

React Router owns `/login`, `/signup`, `/jobs`, job detail, account, application/setup and interview routes. Authentication uses normal Django sessions and CSRF protection through JSON APIs. The resource UUID in the URL identifies the selected job/application/interview rather than browser session storage.

Candidate APIs enforce ownership through `JobApplication.user`. Closed jobs are hidden from new candidates but remain readable to candidates who already applied.

## Live interview

Voice answers are recorded as one browser utterance and sent as a binary WebSocket frame. ffmpeg decodes the recording to 16 kHz mono PCM before Qwen3-ASR. Typed answers enter the same text pipeline directly.

```text
candidate text
    -> Qwen3Guard input safety
    -> Qwen3.5-4B accumulated misuse classification
    -> Qwen3.5-9B adaptive role-neutral interviewer
    -> Qwen3Guard output safety
    -> text response + Qwen3-TTS WAV audio
```

The opening turn includes an internal, non-persisted user instruction asking Qwen to begin with one job-relevant question. This satisfies the model chat template without inventing candidate evidence.

Confirmed candidate/interviewer text is stored. Raw microphone audio is processed in memory and not stored by the application.

## Completion and evaluation

An interview ends by candidate choice, the 30-minute limit, or sustained misuse. Ordinary network loss releases the live worker without ending the interview, allowing the candidate to resume the same URL later.

After completion, Qwen3.6-27B receives the linked Job snapshot and transcript. Each stored evaluation criterion gets an independent reasoning pass and persisted `EvaluationAnswer`. A final reasoning pass plus constrained decoding can emit only `PROGRESS` or `NOT_PROGRESS`.

Infrastructure/model failures use `evaluation_failed`; they do not fabricate an outcome. The application status is then complete and the candidate can request human review.
