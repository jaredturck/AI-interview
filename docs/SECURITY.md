# Security

## Trust boundaries

| Boundary | Control |
| --- | --- |
| Candidate HTTP | Django session authentication, CSRF and object ownership. |
| Interview WebSocket | `AuthMiddlewareStack`, origin validation and interview ownership before model work. |
| Candidate/model text | React/Django escaping; no `dangerouslySetInnerHTML` for untrusted content. |
| Recruitment decision | Safety/misuse models cannot emit `PROGRESS` / `NOT_PROGRESS`; only final evaluation can. |

## Voice data

Raw microphone audio is untrusted input. It is size-limited, decoded by ffmpeg with a timeout, held only in process memory and not persisted by the application.

Silero rejects segments without meaningful speech before Qwen3-ASR. Smart Turn controls conversational handoff only; a manual push-to-talk submit can bypass Smart Turn but **not** VAD, ASR, safety, misuse or interview policy.

## Resource limits

- Candidate text is length-capped.
- Each WebSocket audio frame is capped at 20 MB.
- ffmpeg decoding is bounded to 600 seconds and a 60-second process timeout.
- Interviews are capped at 30 minutes.
- `ModelRuntime` grants exclusive ownership of the live/evaluator GPU worker.

## Failure behaviour

Operational model failures produce explicit errors. Evaluation failure becomes `evaluation_failed`; no hiring outcome is invented. Raw model chain-of-thought is neither returned nor stored.

## Production requirements

Use TLS, strong secrets, production host/origin settings, endpoint rate limiting, dependency/OS patching, monitoring and an explicit candidate retention/privacy policy. Recruitment and automated-decision notices require jurisdiction-specific legal review.
