# V2 Migration Review

The V2 migration changes the product model and presentation without replacing the working local-model pipeline.

## Major changes

- Added immutable `Job` snapshots and candidate `JobApplication` records.
- Moved interviews under applications and made evaluation read the linked Job snapshot.
- Added staff-only job creation/open/close workflow to a custom recruitment-focused Django admin site.
- Rebuilt the candidate application as React + TypeScript with React Router DOM and JSON APIs.
- Added jobs, job detail, application/dashboard and routed interview/setup pages.
- Rebuilt the interview presentation as a Teams-style call surface using the supplied static interviewer image, transcript rail and compact floating controls.
- Removed generic technical-role assumptions from prompts, UI fallbacks and tests.
- Added Django and React internationalization for English, French, German, Spanish, Italian, Portuguese, Dutch and Polish static UI.
- Fixed fresh-interview Qwen opening generation by supplying a non-persisted internal user instruction.
- Replaced internal WebSocket failure close code usage with an application-range code.

## Preserved systems

Django sessions/CSRF, Channels transport, ASR/TTS, transcript confirmation, safety/misuse separation, evidence persistence, constrained evaluator output, human review and exclusive GPU ownership remain the foundations of the application.

## Scope guardrails

This migration does not add RAG/company knowledge, multi-tenancy, CV parsing, scheduling, recruiter messaging, new state-management frameworks or a separate React staff application. The custom staff UI remains Django admin with project-owned templates/CSS.
