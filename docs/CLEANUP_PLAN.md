# Cleanup Plan

## Goal

Turn the current prototype into a focused first-stage AI interview application that implements the requirements discussed for this project without carrying generic framework features, placeholder subsystems, or configuration that is not needed.

The cleanup must preserve the useful operational and accessibility work already present while reducing moving parts and making the codebase easier to reason about.

## 1. Project scope and runtime configuration

- Remove `config/runtime.toml` and `backend/ai_interviewer/runtime_config.py`.
- Hard-code the agreed Qwen model IDs, GPU placement, precision choices, generation limits, interview time limit, and TTS voice behaviour in the implementation.
- Keep only genuine deployment configuration where a secret or deployment boundary requires it. Django's development settings remain suitable for local use and production-sensitive settings will be documented rather than exposed as a general application configuration framework.
- Remove mock/real model mode from production code. Tests will replace the model suite with test doubles directly.
- Remove dynamic `importlib` loading of model implementations.

## 2. Fixed model pipeline

Keep the agreed model stack and build directly around it:

- ASR: `Qwen/Qwen3-ASR-1.7B` through the official `qwen-asr` Transformers-backed runtime.
- Interviewer: `Qwen/Qwen3.5-9B`, non-thinking, INT8, GPU 0.
- TTS: `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice`, BF16, GPU 0 through qwentts.cpp.
- Content safety: `Qwen/Qwen3Guard-Gen-4B`, INT8, GPU 1.
- Misuse monitor: `Qwen/Qwen3.5-4B`, non-thinking, INT8, GPU 1.
- Final evaluator: `Qwen/Qwen3.6-27B`, INT8 across both RTX 3090 GPUs with thinking enabled.

Keep lazy model loading and exclusive live/evaluator GPU ownership because the hardware cannot run the final evaluator alongside the live stack.

## 3. Remove RAG completely

- Delete `backend/interviews/services/rag.py`.
- Delete `config/company/` and all placeholder company knowledge documents.
- Remove RAG imports and prompt/context injection.
- Remove `rank-bm25` from Python dependencies.
- Remove RAG tests and documentation.
- Add a short future-work item noting that company knowledge/RAG requires a separate design conversation before implementation.

## 4. Candidate accounts and authentication

- Keep Django auth, sessions, messages, templates, admin, and CSRF middleware.
- Require account creation and login before an interview can be started.
- Add signup, login, logout, current-account, and account-interview-history endpoints.
- Use Django's built-in `User` model with the normalized email address as the username to avoid an unnecessary custom user model.
- Add React signup/login/account views.
- Associate every new `InterviewSession` with the authenticated user.
- Remove candidate name/email collection from interview setup.
- Remove the separate interview access-token mechanism. HTTP and WebSocket authorization will use the authenticated Django session instead.
- Use `AuthMiddlewareStack` for Channels WebSocket authentication and verify interview ownership in the consumer.
- Human review requests will belong to the authenticated interview owner and only need the explanation text; account identity supplies the email.

## 5. Database cleanup

- Keep SQLite as the local development database.
- Do not package generated `db.sqlite3` in the source archive.
- Keep runtime models only: interview session, conversation turn, criterion evaluation, and human review request.
- Update the initial migration for the cleaned pre-production schema.
- Keep useful Django admin views and register every maintained application model.
- Keep evaluation answers because they are useful evidence for final synthesis and later candidate-requested review.

## 6. Interview flow cleanup

- Remove candidate-selectable interview language and the `language` database field.
- Let ASR identify language automatically and let the interviewer follow the candidate's language naturally.
- Keep the short adaptive interviewer prompt and direct job-description context.
- Remove numerical auto-ending logic (`min_candidate_turns_before_auto_end`, cadence checks, and `should_end`).
- Keep legitimate end conditions: candidate ends interview, 30-minute hard time limit, or sustained high-confidence misuse termination.
- Keep transcript correction as an optional per-interview accessibility choice selected on the setup screen.
- Keep replay, rephrase, pause, text input, voice input, interviewer mute, and speech-speed controls.

## 7. Safety and misuse

- Preserve pre-generation user safety classification with Qwen3Guard.
- Preserve post-generation interviewer safety classification before TTS.
- Preserve the separate accumulated misuse model with `CONTINUE`, `REDIRECT`, and `TERMINATE` choices.
- Keep misuse deliberately forgiving and separate from the final progression decision.
- Remove unused termination metadata from internal return values unless a caller genuinely consumes it.

## 8. WebSocket and reconnect simplification

- Preserve WebSocket origin validation and authenticated session ownership.
- Remove hashed interview access tokens.
- Remove disconnect grace timers and automatic evaluation after network loss.
- On disconnect, release the live GPU reservation when the final connection disappears while leaving the interview active and resumable.
- Allow the authenticated candidate to resume an active interview from their account/browser session.
- Keep a small connection count only because it prevents one tab disconnect from releasing a worker still used by another socket.
- Remove dead connection state such as unused MIME/disconnect task fields.

## 9. Audio transport

- Keep browser `MediaRecorder` and FFmpeg decoding.
- Simplify recording to one completed utterance Blob sent as a binary WebSocket message rather than 250 ms chunks that are only buffered server-side.
- Keep a small JSON control message describing the start/end of an utterance only where needed.
- Send TTS audio back as a binary WebSocket frame instead of base64-encoding WAV bytes into JSON.
- Preserve the text interviewer message separately so accessibility does not depend on audio playback.
- Keep audio byte limits as implementation constants for denial-of-service protection.

## 10. Model runtime simplification

- Replace generic configurable model wrappers with fixed-purpose loaders using constants for the agreed models.
- Retain small reusable text-generation helpers where they genuinely reduce duplicate Hugging Face code.
- Keep model loading lazy to avoid loading large weights during migrations/tests and to avoid Django development autoreload problems.
- After evaluation, unload the evaluator and leave the runtime idle; do not eagerly reload all live models when no interview is waiting.
- Remove dead `release_interview`/state paths or make them part of the simplified disconnect flow where needed.

## 11. Final evaluator

- Keep one deep-reasoning pass per configured evaluation question.
- Store each concise criterion assessment.
- Remove the redundant `evaluator_synthesis.txt` and separate synthesis pass.
- Run one fresh final reasoning pass over the job description, full transcript, and all criterion assessments.
- Run one tiny constrained decoding pass that can return only `PROGRESS` or `NOT_PROGRESS`.
- Keep an explicit `evaluation_failed` operational state rather than inventing a hiring outcome when inference fails.
- Keep final evaluation separate from live safety/misuse decisions.

## 12. Frontend structure

- Keep root `npm run dev`, `npm run build`, and `npm test` as the normal application commands.
- `npm run dev` continues to launch Django and Vite together.
- Keep normal Django administration commands such as `python backend/manage.py migrate`; do not duplicate them through npm.
- Add lightweight routing/state for login, signup, account, interview setup, interview, and completion screens without introducing a routing library unless necessary.
- Remove worker-capacity polling. Starting an interview will simply report a busy-worker response if the single GPU worker is occupied.
- Keep accessible semantic controls, visible status, transcript, keyboard operation, and screen-reader announcements.

## 13. Security review targets

- Require authentication for all candidate interview/status/review endpoints.
- Require interview ownership for HTTP and WebSocket access.
- Preserve CSRF protection for state-changing HTTP requests.
- Preserve `AllowedHostsOriginValidator` for WebSockets.
- Use Django's password hashing and session cookies rather than custom authentication tokens.
- Validate and size-limit user text, review explanations, and audio input.
- Ensure candidate transcript content is always treated as untrusted data in evaluator prompts.
- Keep admin protected by Django staff/superuser authentication.
- Review session-cookie and production TLS settings.
- Avoid exposing model reasoning/chain-of-thought through APIs or stored application records.

## 14. Performance review targets

- Confirm approximate VRAM fit of the live model placement on dual RTX 3090 GPUs.
- Confirm evaluator INT8 placement leaves adequate KV-cache headroom on both GPUs.
- Remove unnecessary model calls such as auto-end classification and RAG routing/retrieval.
- Keep interviewer output short and non-thinking.
- Avoid eager live-model reload immediately after evaluation.
- Reduce WebSocket overhead by sending complete utterances and binary TTS audio.
- Identify first-model-load latency as a deployment/warmup concern rather than hiding it.
- Document that one dual-3090 worker supports one live interview or one final evaluation at a time.

## 15. Repository-wide style cleanup

Apply the supplied style guide to all maintained Python source, not only changed files:

- no Python type hints;
- single-quoted Python strings;
- one-line triple-single-quoted docstrings;
- compact imports and calls;
- one blank line between structures;
- one-line function signatures where practical;
- no nested functions, walrus expressions, wildcard imports, or speculative abstraction;
- simple direct control flow;
- descriptive snake_case variables/functions and CamelCase classes;
- generated Django migrations are excluded from style rewriting.

Apply the same simplicity/readability philosophy to JavaScript/React without mechanically forcing Python-only conventions onto JSX.

## 16. Tests and validation

- Rewrite tests around authenticated users and fixed production model runtime with test doubles injected only by tests.
- Test signup/login/logout/account ownership.
- Test interview creation requires authentication.
- Test users cannot access another user's interviews over HTTP or WebSocket.
- Test typed interview turns, transcript correction, safety redirect, repeated misuse termination, manual end, and evaluation.
- Test human review submission after automated processing.
- Test final result is exactly binary when evaluation succeeds.
- Run Django checks, pytest, Python compilation, frontend production build, and static searches for removed RAG/runtime/mock/dead paths.
- Perform a final bug, security, and performance review after implementation and fix issues found before packaging.

## 17. Documentation and packaging

- Rewrite README around the actual simplified setup and runtime.
- Update architecture, models, prompts, testing, security, accessibility, and deployment docs.
- Add `TODO.md` with deferred RAG/company-knowledge work.
- Remove generated caches, bytecode, build output, local SQLite database, and stale configuration files from the packaged source.
- Produce a final ZIP and SHA-256 hash.

## Post-audit implementation note

The dependency review performed during verification found that the original `qwen-asr` wrapper pins an older Transformers generation that does not match the current Qwen3.5/Qwen3.6 runtime. The implementation therefore uses the official native Hugging Face `Qwen/Qwen3-ASR-1.7B-hf` checkpoint instead. Qwen3-TTS now runs through qwentts.cpp in the same Django process, keeping the Python Transformers 5 stack unchanged without the incompatible `qwen-tts` package.

The reconnect implementation was also simplified further than the initial plan: the cleaned V1 permits one live WebSocket per interview rather than maintaining a connection count. This prevents overlapping model calls and transcript races on the single dual-GPU worker.
