# Security

## Trust boundaries

| Boundary | Control |
| --- | --- |
| Candidate HTTP | Django session authentication, CSRF and object ownership. |
| Interview WebSocket | `AuthMiddlewareStack`, origin validation and interview ownership before model work. |
| Candidate/model text | React/Django escaping; no `dangerouslySetInnerHTML` for untrusted content. |
| Hidden recruitment policy | Candidate APIs expose the public Job description but not essential requirements, verification requirements or evaluator criteria. |
| Recruitment decision | Safety/misuse models cannot emit hiring outcomes; Python enforces hard gates and only final evaluation can emit constrained `PROGRESS` / `NOT_PROGRESS`. |

## Prompt manipulation and unsupported claims

Candidate transcript content is untrusted data, even when it contains instructions addressed to a model. Interviewer, misuse and evaluator policy lives in system prompts and explicitly treats transcript instructions as candidate content rather than controlling instructions.

The system does not claim to detect lies. Unsupported candidate statements are not treated as established competence, and important role claims should be probed with relevant examples, detail and reasoning. Material inconsistencies can be clarified neutrally and recorded as weak or contradictory evidence.

Externally verifiable credentials are deliberately represented as `CLAIMED`, `NOT_CLAIMED` or `UNCLEAR`. A claim such as professional registration is never stored as independently verified merely because the candidate said it. Production recruitment processes must verify required credentials through an appropriate external or human process.

## Recruitment snapshot integrity

Staff author Job specifications through authenticated Django Admin. Once a Job has an application, the description and internal assessment criteria become read-only. `JobApplication.job` uses database protection against deleting a Job that has historical applications. The optional sample reset command also refuses to rewrite used sample snapshots.

## Voice data

Raw microphone audio is untrusted input. Candidate transfers are limited to 20 MB, sent as bounded 256 KiB WebSocket messages, decoded by ffmpeg with a timeout, held only in process memory and not persisted by the application. Interviewer WAV output uses the same bounded-message transport so logical audio duration is not coupled to Daphne's single-message payload limit.

Silero rejects segments without meaningful speech before Qwen3-ASR. Smart Turn controls conversational handoff only; a manual push-to-talk submit can bypass Smart Turn but **not** VAD, ASR, safety, misuse or interview policy.

## Resource limits

- Candidate text is length-capped.
- WebSocket audio messages are bounded to 256 KiB and candidate logical audio transfers are capped at 20 MB.
- ffmpeg decoding is bounded to 600 seconds and a 60-second process timeout.
- Interviews are capped at 30 minutes.
- `ModelRuntime` grants exclusive active inference ownership while the full GPU model stack remains resident.

## Failure behaviour

Operational model failures produce explicit errors. Evaluation failure becomes `evaluation_failed`; no hiring outcome is invented. Invalid or incomplete structured evaluator output is rejected rather than converted into a successful decision. Raw model chain-of-thought is neither returned nor stored.

## Production requirements

Use TLS, strong secrets, production host/origin settings, endpoint rate limiting, dependency/OS patching, monitoring and an explicit candidate retention/privacy policy. Recruitment, automated-decision, credential-verification and employment-law requirements need jurisdiction-specific legal review before production use.
