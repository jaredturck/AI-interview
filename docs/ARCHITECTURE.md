# Architecture

## Browser and accounts

React is the candidate-facing application. Django provides account/session APIs, interview persistence, WebSocket orchestration and Django admin.

Candidates must be signed in before starting an interview. Django sessions authenticate both HTTP requests and Channels WebSockets. Each `InterviewSession` belongs directly to the authenticated Django user.

## Live interview

Voice answers are recorded as one browser utterance and sent as a binary WebSocket frame. Django uses ffmpeg to decode the recording to 16 kHz mono PCM before Qwen3-ASR transcribes it. Typed answers skip ASR and enter the same text pipeline.

The live pipeline is:

```text
candidate text
    -> Qwen3Guard input safety
    -> Qwen3.5-4B accumulated misuse classification
    -> Qwen3.5-9B adaptive interviewer
    -> Qwen3Guard output safety
    -> text response + Qwen3-TTS WAV audio
```

The job description guides the interviewer but is not a fixed interview script.

Every confirmed candidate/interviewer message is stored as an ordered text turn. Raw microphone audio is processed in memory and is not stored by the application.

## Interview completion

The interview ends when:

- the candidate chooses to end it;
- the 30-minute interview limit is reached; or
- the separate misuse monitor identifies sustained clear misuse strongly enough to terminate the live conversation.

There are no arbitrary question-count or turn-count termination rules.

Network disconnection does not fail or automatically evaluate the candidate. The worker reservation is released and the authenticated candidate can resume the active interview later.

## Final evaluation

After the live interview ends, the realtime models are unloaded and Qwen3.6-27B is loaded in INT8 across both RTX 3090 GPUs.

Each configured evaluation question receives its own reasoning pass with the complete job description and transcript. The resulting concise criterion assessments are stored in the database.

A final reasoning pass then receives the original evidence plus all criterion assessments. A final constrained decoding pass can emit only:

```text
PROGRESS
NOT_PROGRESS
```

Only this final subsystem makes the progression decision.

## Persistence

The database stores runtime data only:

```text
Django User
InterviewSession
ConversationTurn
EvaluationAnswer
HumanReviewRequest
```

The job description, evaluator criteria and prompts remain ordinary editable project files rather than duplicated database configuration.
