# Adaptive AI Interviewer Style and Code Quality Guide

## Purpose

This guide defines how maintained code and documentation should look in this repository. It is written for developers and AI programming assistants so project conventions survive across separate work sessions.

Read it with:

- `ARCHITECTURE.md` for system boundaries;
- `VOICE_PIPELINE.md` for realtime speech flow;
- `MODELS.md` for model/device ownership.

This guide is **not** permission to rewrite unrelated code. Apply it to the requested change and directly connected cleanup only.

## 1. Priority order

When concerns conflict:

1. Correct runtime behaviour and existing contracts.
2. The agreed task scope.
3. Architecture/framework/model requirements.
4. Readability and this guide.
5. Linter/formatter preferences.

Prefer simple, direct code whose intent is obvious. Do not make working code worse to satisfy a tool.

## 2. Change discipline

Before changing behaviour:

- inspect the real implementation and direct callers;
- trace browser -> WebSocket -> backend -> model -> persistence when touching interview flow;
- preserve async ordering, side effects and error behaviour;
- inspect GPU/model lifecycle before changing model code;
- preserve measured or clearly hot-path behaviour unless performance is part of the task;
- avoid speculative abstractions, defensive code and unrelated refactors.

Prefer the smallest complete patch rather than a broad redesign hidden inside a bug fix.

## 3. Python baseline

Strong defaults:

- no Python type hints;
- `snake_case` variables/functions/methods;
- `CamelCase` classes;
- `UPPER_SNAKE_CASE` constants;
- single-quoted strings;
- top-level imports unless runtime ordering/lazy loading requires otherwise;
- no wildcard imports;
- avoid nested functions;
- avoid recursion unless it is genuinely the clearest algorithm;
- avoid broad `try`/`except` blocks;
- avoid explicit `raise` unless an existing contract requires it;
- avoid walrus expressions;
- avoid unnecessary classes/helper layers;
- avoid temporary files unless an external API requires them;
- avoid environment-variable-driven behaviour unless process-start configuration genuinely belongs there;
- avoid `argparse`/`sys.argv` outside real CLI/management scripts.

Framework/runtime constraints beat style rules.

## 4. Python strings and docstrings

Normal strings use single quotes:

```python
model_name = 'Qwen/Qwen3.5-9B'
message = f'Loading {model_name}'
```

Docstrings are one physical line, triple-single-quoted and concise:

```python
def turn_complete(self, audio, sample_rate):
    ''' Return whether accumulated speech has reached a conversational handoff point. '''
```

A docstring states purpose, not arguments, return types or line-by-line implementation.

## 5. Imports

Keep imports compact and readable.

Preferred:

```python
import asyncio, json, logging

import numpy as np
import torch
from django.utils import timezone
```

Multiple ordinary modules on one line are allowed. Do not use parenthesized import blocks merely because a formatter prefers them.

Long imports may use compact continuation:

```python
from interviews.services.interview import INTERVIEW_MAX_MINUTES, MAX_TEXT_CHARS, add_turn, closing_message, finish_interview, \
    interview_timed_out, opening_message, process_candidate_text, rephrase_message
```

Preserve deliberate delayed imports used to avoid model loading during migrations/tests or to satisfy Django startup ordering.

## 6. Line width and vertical space

Use approximately 140 characters as a visual guideline, not a hard limit. Keep logically indivisible model IDs, URLs, protocol strings and regexes intact when splitting them would be harder to read.

Use one blank line between structures and logical phases. Avoid double blank lines in maintained Python.

Vertical space should communicate structure, not formatter preference.

## 7. Function signatures and calls

Keep function/method signatures on one physical line when practical.

Preferred:

```python
def generate(self, messages, max_tokens, thinking, temperature, top_p):
```

Keep simple calls compact:

```python
self.processor = AutoProcessor.from_pretrained(model_name)
```

If a call must wrap, keep related arguments together rather than putting every argument on its own line.

## 8. Collections and dictionaries

Short flat runtime collections stay horizontal:

```python
choices = ['CONTINUE', 'REDIRECT', 'TERMINATE']
```

Non-trivial dictionaries use JSON-like indentation:

```python
model_kwargs = {
    'device_map': device_map_for('cuda:1'),
    'dtype': torch.float16,
    'low_cpu_mem_usage': True,
    'quantization_config': BitsAndBytesConfig(load_in_8bit=True)
}
```

Configuration constants may use one entry per line when developers need to compare/tune values directly.

## 9. Control flow

Prefer code that reads top-to-bottom.

Prepare meaningful booleans instead of vertically exploding one large condition:

```python
pending_turn = bool(self.pending_turn_audio)
should_finalize = pending_turn and not self.speech_resumed_since_probe

if should_finalize:
    ...
```

Use early returns when they make the normal path clearer. Do not split straightforward orchestration into tiny helpers solely to reduce function length.

## 10. Comprehensions

Simple comprehensions are fine:

```python
turns = [{'role': turn.role, 'text': turn.text} for turn in interview.turns.all()]
```

Use explicit loops when a comprehension includes multiple loops, complex conditions, side effects or nested structures.

## 11. Error handling

Handle observed/expected failures at the boundary that can recover from them.

Good boundaries include:

- browser permission/media failures;
- ffmpeg decoding;
- model loading/inference;
- WebSocket protocol parsing;
- background evaluation.

Broad exception handling is acceptable only at a genuine terminal boundary that must convert arbitrary library failures into a controlled application state. Keep those handlers narrow in scope and log the underlying error.

Do not catch exceptions simply to return a made-up successful result.

## 12. Comments

Comments explain **why**, not **what**.

Useful comments cover:

- framework/model constraints;
- intentional workarounds;
- non-obvious performance/device choices;
- subtle ordering requirements;
- narrow lint exceptions.

Do not narrate obvious statements.

## 13. Django

- Use Django ORM/query APIs rather than handwritten SQL unless there is a measured reason.
- Preserve session/CSRF/ownership checks on candidate resources.
- Keep recruitment persistence in Django models; do not add ad-hoc JSON/text state files.
- Do not rewrite generated migrations for style.
- Keep staff workflows in Django Admin unless a separate staff frontend is explicitly designed.
- Avoid schema migrations during unrelated style/cleanup work.

## 14. Channels and async code

`InterviewConsumer` is the realtime orchestration boundary.

Rules:

- never run blocking ORM/model/ffmpeg work directly on the event loop;
- use `sync_to_async(..., thread_sensitive=False)` for independent heavy inference/decoding;
- keep per-connection state on the consumer instance;
- preserve WebSocket message ordering assumptions;
- cancel connection-owned tasks on disconnect/end;
- avoid concurrent calls into the same GPU model unless the runtime is explicitly designed for it;
- update backend protocol, frontend types and tests together.

A protocol message must have one clear meaning. Do not overload a status string to represent unrelated state if a dedicated message is clearer.

## 15. Model and GPU code

Model ownership is centralized:

```text
ModelRuntime -> RealModelSuite -> concrete model wrappers
```

Do not instantiate heavyweight models in views, consumers or request helpers.

For every model change, know:

- exact checkpoint/model file;
- device;
- weight precision;
- activation/compute precision where relevant;
- load/unload lifecycle;
- whether it is live-only or evaluator-only.

Keep these facts synchronized with `MODELS.md`.

Do not silently move models between CPU/GPU or change precision to suppress warnings. Fix actual configuration mismatches and document intentional placement.

## 16. Performance-sensitive code

Treat these as hot or latency-sensitive until measured otherwise:

- microphone/turn detection;
- ffmpeg decode;
- ASR;
- interviewer/safety/misuse inference;
- TTS;
- GPU load/unload transitions;
- evaluator generation.

Before changing them, understand call frequency, allocations, device transfers and synchronization. Benchmark material changes on the target dual-RTX-3090 host.

Readability remains the default, but a proven performance optimization may justify more complex code.

## 17. Audio and turn-taking

The browser RMS threshold is a recording trigger only. It must not become the authoritative end-of-turn rule.

Backend voice order is:

```text
ffmpeg -> Silero VAD -> pending turn -> Smart Turn -> Qwen3-ASR
```

Keep responsibilities separate:

- Silero: speech vs non-speech;
- Smart Turn: conversational completion;
- ASR: transcription;
- interviewer model: conversation content.

Do not add text heuristics such as rejecting single Unicode characters as a substitute for correct speech detection; multilingual speech makes those heuristics unsafe.

Push-to-talk is an explicit end-of-turn signal but still passes speech validation.

## 18. TypeScript and React

TypeScript typing is expected. Keep types useful and local rather than building elaborate generic abstractions.

- `snake_case` is acceptable for project state/functions to match the existing frontend style.
- Keep component responsibilities narrow.
- Put shared API/WebSocket payload types in `frontend/src/types.ts`.
- Prefer React state for renderable state and refs for mutable browser/media handles that should not trigger renders.
- Do not duplicate the same mutable media state in several components.
- Effects must clean up timers, animation frames, media streams, audio contexts and sockets they own.
- Avoid new state-management libraries while hooks/local state remain sufficient.

Example:

```typescript
const websocket_ref = useRef<WebSocket | null>(null);
const [candidate_pending, set_candidate_pending] = useState(false);
```

## 19. Browser media

`useInterview.ts` owns browser microphone/audio playback state.

- request microphone permission only through explicit user interaction;
- keep the open `MediaStream` alive until the user closes it/session ends;
- stop every track during cleanup;
- distinguish browser autoplay denial from interrupted/stale playback;
- preserve push-to-talk fallback;
- keep visible recording/listening state synchronized with the real stream/recorder;
- do not persist raw browser audio on the frontend.

## 20. Frontend UI state

Temporary activity indicators are transient UI state, not transcript evidence.

```text
candidate ... -> candidate message
interviewer ... -> assistant message
```

Do not insert placeholder messages into the persisted `messages` array or backend `ConversationTurn` table.

Accessibility state must remain meaningful even when animation is reduced/disabled.

## 21. CSS

Follow the existing component-oriented stylesheet rather than introducing a second styling system.

- reuse existing visual tokens/colors where practical;
- keep selectors local to the component/feature;
- preserve responsive/mobile transcript behaviour;
- ensure new animation works with the existing `prefers-reduced-motion` override;
- do not use CSS to hide broken application state.

## 22. Tests

Every behavioural patch should add focused regression coverage near the affected subsystem.

For realtime speech changes, test protocol/state behaviour with fake model methods rather than loading CUDA models in pytest.

Verification order:

```text
Python parse/check
Django check
migration drift check
pytest
TypeScript build
production Vite build
```

Do not claim real CUDA/model verification unless it was actually run on the target host.

## 23. Documentation style

Documentation is engineering reference material, not prose padding.

Prefer, in order:

1. diagrams for flows/state/lifecycle;
2. tables for facts;
3. short code/protocol examples;
4. prose only for non-obvious rationale.

Rules:

- state each idea once;
- keep one authoritative location for each fact and link to it elsewhere;
- document current behaviour, not aspirations, unless clearly labelled future work;
- update docs in the same patch when architecture/protocol/model placement changes;
- use Mermaid for editable diagrams;
- remove stale documentation rather than stacking new explanations on top of obsolete ones.

## 24. Patch discipline

When producing an overlay patch archive:

- include only added/changed files;
- preserve repository-relative folder structure;
- do not include caches, `node_modules`, `.venv`, build output or databases;
- keep unrelated formatting churn out of the archive;
- review the final diff before packaging.

## 25. Quick review checklist

Before finalizing a change:

- Is the requested behaviour correct?
- Did the patch stay inside scope?
- Did I inspect the real call path?
- Are Python strings/docstrings/imports consistent with this guide?
- Did I avoid unnecessary abstractions and defensive branches?
- Are async/model calls correctly isolated from the event loop?
- Is GPU/model ownership still centralized?
- Did WebSocket changes update both ends and tests?
- Are temporary UI states kept out of persisted transcript data?
- Did I preserve accessibility and cleanup browser media resources?
- Are architecture/model/voice docs still accurate?
- Did I run the checks that are possible in the current environment?

## Final principle

Prefer the smallest clear implementation that preserves contracts and makes the system easier to reason about. Complexity is justified only when correctness, architecture or measured performance requires it.
