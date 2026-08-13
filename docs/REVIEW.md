# Cleanup Review

This file summarizes the implementation review performed after the cleanup plan in `docs/CLEANUP_PLAN.md` was written.

## Scope cleanup completed

The cleanup removed application features that were not part of the agreed V1 design or did not justify their complexity:

- runtime model selection and model/device configuration;
- product-level mock/real mode;
- RAG, keyword routing and placeholder company knowledge documents;
- arbitrary turn-count/auto-end heuristics;
- candidate-selectable interview language;
- pre-interview name/email fields;
- custom interview access tokens;
- custom Django management commands for interview/evaluation/seeding;
- redundant evaluator synthesis stage;
- pseudo-streaming audio chunks that were only buffered server-side;
- base64 TTS audio transport;
- stale build/cache/database artifacts.

The cleanup retained features that provide clear product, accessibility, reliability or security value: Django admin, accounts/sessions, CSRF/origin protection, transcript correction, adaptive interview controls, the separate safety/misuse layers, GPU ownership, explicit evaluator failure state and candidate-requested human review.

## Bugs found and fixed

- Candidate text is normalized/capped before the UI echo, database write and model inference so all three see the same evidence.
- Completion-page restoration now preserves evaluation-in-progress and evaluation-failed states rather than losing the candidate's result view after refresh.
- The interview timeout task avoids cancelling itself while starting evaluation.
- A completed WebSocket no longer releases the GPU reservation during the live-to-evaluator handoff. This closes a race where another candidate could reserve the worker before final evaluation began.
- Evaluation worker exceptions release any stale live reservation and persist `evaluation_failed` instead of leaving the worker/session stuck.
- Multiple simultaneous WebSockets for the same worker are rejected rather than permitting overlapping model calls and transcript races.
- Dead MIME/disconnect-task state and unused response metadata were removed.

## Security review

The reviewed V1 uses normal Django session authentication and ownership checks for candidate data. CSRF remains enabled for HTTP mutations, WebSocket origins are validated, transcript/audio sizes are bounded, ffmpeg has a timeout, Django admin remains staff-protected, and model reasoning is not exposed to candidates.

The main production controls intentionally left to deployment are TLS, endpoint rate limiting, production secrets/hosts, monitoring and a formal privacy/retention policy. These are documented in `docs/SECURITY.md` and `docs/DEPLOYMENT.md` rather than implemented as speculative application frameworks.

## Performance review

The live GPU placement is intentionally asymmetric: the 9B interviewer and 0.6B TTS share GPU 0, while ASR, guard and misuse models share GPU 1. INT8 is used for the larger text models; speech models remain BF16.

The realtime path still performs several sequential model calls per candidate turn, so real hardware profiling is required. Removing RAG routing and auto-end classification reduces unnecessary calls. The interviewer is non-thinking and output-capped to keep response latency low.

The final evaluator deliberately prioritizes decision quality over latency. With the example 12-criterion rubric it performs 12 focused reasoning calls, one final reasoning call and one tiny constrained-choice call. Repeated transcript prefill is currently the largest obvious optimization opportunity; prefix/KV reuse should be considered only after profiling the real Qwen3.6 runtime.

The first live interview after process startup will pay model-load latency. Production should warm the live stack before accepting candidates if that startup delay is unacceptable.

## Validation limitations

Python source was compiled and repository-wide structural/style checks were run in the build environment. Full Django/Channels/React tests and real CUDA/Qwen inference could not be executed there because the environment did not contain the project dependencies/model weights. `npm test` is the required first full application validation on the target development machine, followed by real-model hardware profiling.
