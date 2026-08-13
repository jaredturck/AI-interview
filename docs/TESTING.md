# Testing

Run the project test command from the repository root:

```bash
npm test
```

It runs:

1. `python backend/manage.py check`
2. `python backend/manage.py makemigrations --check --dry-run`
3. `python -m pytest backend`
4. `npm run build`

The test suite directly injects a deterministic fake model suite into the process-wide model runtime. The production code has no mock-model configuration or mock-model mode.

Tests cover candidate account creation, authentication requirements, interview ownership, account history, review requests, normal interviewer turns, safety redirection, accumulated misuse termination, multi-criterion evaluation and authenticated Channels WebSocket behavior.

Real-model verification must be performed separately on the target dual-RTX-3090 host because CUDA placement, VRAM consumption, first-load time, ASR/TTS package compatibility and generation latency cannot be validated by lightweight application tests.
