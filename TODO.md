# Remaining work

Reconciled against `main` at commit `e8fae619` (15 August 2026). The items below are not implemented at that commit.

## Product and architecture

- Design company knowledge/RAG as a separate subsystem: authoritative sources, freshness, permissions, retrieval quality and prompt-injection boundaries.
- Add true full-duplex barge-in so candidate speech can cancel interviewer generation/TTS after a turn has already been committed.

## Validation and tuning

- Gather real interview turn-taking data and tune RMS, Silero, Smart Turn and hold/grace thresholds from observed false accepts/rejects.
- Profile live inference on the target dual-RTX-3090 host before changing batching, model sizes, quantization or GPU placement.
- Run the target-host CUDA/model checks and behavioural acceptance set in `docs/TESTING.md` before treating runtime performance and model judgement as production-validated.

## Production readiness

- Complete the deployment/security work called out in `docs/DEPLOYMENT.md` and `docs/SECURITY.md`: production secrets/hosts/origins and TLS, rate limiting and monitoring, retention/privacy policy, and jurisdiction-specific recruitment/legal review.

## Reconciled as complete

The following recent work is already present in code and should not be reopened as TODO work:

- admin-authored immutable recruitment specifications, optional sample-job seeding, structured evidence evaluation and Python-enforced hard requirements (`4c2c7784`);
- bounded bidirectional WebSocket audio framing and reassembly for large candidate/TTS audio (`345afb5f`);
- repaired responsive Django Admin layout and authorized record deletion (`fd86eaef`);
- server-authoritative semantic stopping, persisted wrap-up state, 13-minute wrap-up threshold, 15-minute hard deadline and live countdown (`e8fae619`).
