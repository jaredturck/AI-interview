# Security

## Session access

Each interview receives a random browser access token. Only its SHA-256 hash is stored. Status and review endpoints require the matching token.

WebSockets are checked against Django's allowed-host origin policy before interview authentication.

## AI safety

Candidate input is checked by Qwen3Guard before the interviewer responds. Generated interviewer text is checked again before speech synthesis.

The separate misuse model watches the accumulated transcript for sustained abuse of the interview process. It can request a redirect or end the live interview, but it cannot decide whether the candidate progresses.

Transcript content is always treated as untrusted candidate content by the final evaluator rather than as model instructions.

## Resource limits

The backend limits text size, uploaded audio bytes, total interview duration and concurrent ownership of the single dual-GPU worker.

Disconnected interviews receive a short reconnect window before the backend closes and evaluates the session.

## Candidate decisions

Only the final evaluator returns `PROGRESS` or `NOT_PROGRESS`. Infrastructure failure uses the separate operational status `evaluation_failed` rather than fabricating a candidate outcome.

Candidates can submit a human-review request through the website after automated processing.

## Production configuration

Create `config/runtime.toml` with a production secret key, production hosts/origins and `debug = false`. Serve Django and the built frontend behind TLS and a production ASGI deployment rather than Django's development server.
