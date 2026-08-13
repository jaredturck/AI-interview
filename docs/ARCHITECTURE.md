# Architecture

## Browser to backend

React captures candidate microphone audio with `MediaRecorder` and sends ordered audio chunks over the interview WebSocket. Django decodes the completed utterance to 16 kHz mono PCM with ffmpeg and sends it to Qwen3-ASR.

Typed candidate messages enter the same interview pipeline after skipping ASR.

The interviewer returns short text responses. The text is sent to the browser immediately and Qwen3-TTS produces a WAV response for playback.

## Live interview subsystem

The live subsystem contains:

- `Qwen/Qwen3-ASR-1.7B` for speech recognition through Hugging Face Transformers.
- `Qwen/Qwen3.5-9B` for the short adaptive interviewer with thinking disabled.
- `Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice` for interviewer speech.
- `Qwen/Qwen3Guard-Gen-4B` for immediate content safety.
- `Qwen/Qwen3.5-4B` for transcript-level misuse monitoring with thinking disabled.

The job description guides the interviewer but does not define a rigid question sequence. Company questions can retrieve a few relevant paragraphs from `config/company/`.

## Transcript

Each confirmed candidate or interviewer message is stored as one ordered text turn. Speech and typed input become the same text evidence after transcription/confirmation.

The application does not create hidden candidate personality or disability profiles.

## Final evaluation subsystem

When the interview ends, the live models are unloaded and `Qwen/Qwen3.6-27B` is loaded in INT8 across both GPUs.

Each line in `config/evaluation_questions.txt` receives its own reasoning pass with the complete job description and transcript. Those assessments are then synthesized. A final dedicated reasoning pass considers the whole record before a constrained decoding pass returns exactly `PROGRESS` or `NOT_PROGRESS`.

The evaluation model is the only subsystem that decides progression.

## Configuration

Role and company content is file-backed:

```text
config/job_description.md
config/evaluation_questions.txt
config/company/*.md
```

Runtime interview state is database-backed:

```text
InterviewSession
ConversationTurn
EvaluationAnswer
HumanReviewRequest
```
