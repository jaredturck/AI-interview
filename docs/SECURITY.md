# Security review

## Controls implemented

- Django CSRF protection protects HTTP mutations.
- WebSockets are origin-checked with `AllowedHostsOriginValidator`.
- Each interview receives a cryptographically random access token; only its SHA-256 hash is persisted.
- Status and candidate-review endpoints require that interview token.
- Candidate text is length-limited server-side.
- Microphone uploads are size-limited before decoding.
- Raw microphone audio is decoded in memory and not persisted by the application.
- Interviews have a hard maximum duration.
- The Django admin exposes transcript/evaluation/review records read-only to reduce accidental evidence alteration.
- Production-mode Django enables secure cookies, HTTPS redirect, HSTS, clickjacking denial and content-type sniffing protection.

## AI safety boundaries

Immediate candidate input is checked by Qwen3Guard before the interviewer can answer it. Interviewer output is checked again before it reaches TTS.

A separate misuse monitor sees the accumulated transcript and can `CONTINUE`, `REDIRECT` or `TERMINATE`. Its prompt requires strong sustained evidence for termination rather than treating a single strange interaction as abuse.

The final evaluator is separately prompted to treat all transcript text as interview evidence rather than instructions. This limits a candidate's ability to place instructions in the transcript that target the later reasoning model.

The final outcome is generated through token-level constrained decoding rather than trusting the model to follow an output-format instruction.

## Lifecycle and capacity

The active interview retains ownership of the GPU worker until evaluation atomically takes over. This avoids a race where another candidate could reserve the live models between the closing turn and evaluator load.

Unexpected disconnects receive a configurable reconnect grace period (120 seconds by default). If no connection returns, the interview is closed and evaluated so an abandoned browser cannot reserve the GPU worker until the full interview deadline. Timeout paths re-read current database/runtime state before closing so a stale socket cannot overwrite a session that subsequently completed or reconnected.

## Operational failures

`PROGRESS` and `NOT_PROGRESS` remain the only candidate outcomes. `evaluation_failed` is an operational status used only when the evaluator cannot complete; the UI then offers the existing candidate-requested human review route rather than silently presenting a hiring outcome that was never produced. `run_backend.sh` also recovers evaluations interrupted by a previous process restart into this status.

## Production work still required

- Replace the example secret/configuration.
- Terminate TLS at a hardened reverse proxy.
- Add HTTP and WebSocket rate limits.
- Use PostgreSQL for production persistence.
- Define access controls and retention/deletion for recruitment data.
- Keep Django admin behind appropriate authentication/network restrictions.
- Log operational failures without logging raw sensitive candidate text unnecessarily.
- Patch dependencies and model packages as part of a controlled release process.
- Red-team content moderation, prompt injection, misuse thresholds and unusual legitimate communication.
- Perform dependency/SBOM/vulnerability scanning in the deployment environment.
- Obtain appropriate legal/data-protection review before real hiring use.

## Threat-model assumptions

V1 assumes one trusted organisation controls the job description, prompts and company RAG documents. Those files/admin records are privileged configuration and must not be writable by candidates.

The system is designed for one active interview per dual-GPU worker. Running multiple ASGI processes against the same GPUs is unsupported and can defeat process-local capacity control.
