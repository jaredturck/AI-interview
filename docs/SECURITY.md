# Security

## Candidate authentication and ownership

Candidates use Django's built-in password hashing and server-side session framework. Interviews are linked directly to the authenticated Django user.

All interview start, status and review APIs require authentication and enforce interview ownership. Channels uses `AuthMiddlewareStack`, and every WebSocket verifies that the requested interview belongs to `scope['user']`.

Django CSRF middleware protects state-changing HTTP requests. WebSockets are wrapped in `AllowedHostsOriginValidator` to prevent cross-origin use of an authenticated session.

## AI safety

Candidate text is checked by Qwen3Guard before the interviewer responds. Generated interviewer text is checked again before TTS.

A separate transcript-level misuse model can return `CONTINUE`, `REDIRECT` or `TERMINATE`. It can end the live conversation but cannot produce the hiring outcome.

Evaluator prompts explicitly treat transcript instructions as untrusted candidate content. Raw model thinking is not exposed through HTTP/WebSocket APIs and is not stored as candidate-facing output.

## Resource protection

- candidate text is capped before storage and inference;
- WebSocket audio is capped at 20 MB per utterance;
- ffmpeg decoding is capped to 10 minutes of decoded audio and a 60-second subprocess timeout;
- the interview has a 30-minute total limit;
- one live interview or evaluator owns the dual-GPU worker at a time;
- TTS audio uses binary WebSocket frames instead of base64 JSON.

## Failure handling

A model/infrastructure failure does not invent a candidate outcome. Failed final inference uses `evaluation_failed`, after which the candidate can request human review.

If the Django process dies while a background evaluation is running, the in-memory evaluation job cannot survive the restart. The next account/status access detects a stale `evaluating` record and changes it to `evaluation_failed` rather than leaving the candidate permanently stuck.

Completed WebSockets retain the model reservation until the evaluator thread takes ownership. Ordinary unfinished disconnects release the live reservation immediately. This prevents another interview from racing the evaluator during the live-to-final model handoff.

## Production requirements

Before public deployment:

- use TLS;
- use a strong `DJANGO_SECRET_KEY`;
- set `DJANGO_DEBUG=false`;
- configure production allowed hosts and CSRF trusted origins;
- run a production ASGI server behind a reverse proxy;
- rate-limit signup/login and other abuse-prone endpoints at the deployment boundary;
- define transcript/account/evaluation data retention and deletion policies;
- keep operating-system, CUDA, PyTorch and Python dependencies patched;
- review candidate-facing privacy and automated-decision notices with appropriate legal/data-protection specialists.
