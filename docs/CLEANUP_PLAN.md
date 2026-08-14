# Maintenance plan

The large V2 cleanup that produced the current React/Django architecture is complete. This file now records maintenance rules rather than a speculative migration plan.

## Current priorities

1. Keep documentation synchronized with runtime behaviour; `ARCHITECTURE.md`, `VOICE_PIPELINE.md` and `MODELS.md` are authoritative.
2. Keep model ownership centralized in `ModelRuntime` / `RealModelSuite`.
3. Keep WebSocket protocol changes explicit in `types.ts`, `useInterview.ts`, `consumers.py` and tests.
4. Preserve raw-audio privacy: process in memory, persist confirmed text only.
5. Tune turn-taking thresholds from measured interview sessions before adding more heuristics.
6. Avoid unrelated refactors while modifying latency-sensitive speech/model paths.
7. Keep generated migrations, build output, caches and local databases out of patch archives.

## Deferred architecture work

See `TODO.md` for RAG/company knowledge, full-duplex barge-in and broader inference-serving changes.
