# Testing

Run from the repository root:

```bash
npm test
```

It runs:

1. `python backend/manage.py check`
2. `python backend/manage.py makemigrations --check --dry-run`
3. `python -m pytest backend`
4. `tsc -b && vite build`

The backend suite injects a deterministic fake model suite. Production code has no mock-model mode.

Coverage includes authentication, open-job listing, job application, duplicate prevention, candidate ownership, account/application payloads, immutable Job snapshots, staff job creation, generic opening-message behaviour, live interview safety/misuse handling, criterion persistence, evaluation outcome, human review and authenticated Channels WebSockets.

Real-model CUDA placement, VRAM usage, model load times, ASR/TTS compatibility and latency must still be validated on the target dual-RTX-3090 host.
