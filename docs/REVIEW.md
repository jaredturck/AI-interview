# Architecture review

The current V2 product boundary is stable:

```text
Candidate React SPA -> Django JSON + Channels -> local realtime model suite
Staff Django Admin  -> Django ORM
Completed interview -> Qwen3.6 evaluation -> binary stage-one outcome
```

## Invariants

- Jobs are immutable recruitment snapshots once created.
- Candidate resources are owned through authenticated `JobApplication.user`.
- One dual-GPU worker handles one live interview or one evaluation at a time.
- Safety, misuse and final recruitment evaluation remain separate decisions.
- Confirmed text is persisted; raw microphone audio is not.
- Model/device choices are fixed code-level architecture, not candidate settings.
- Current voice turn-taking is documented in `VOICE_PIPELINE.md`.

## Review before major changes

Trace the full browser -> WebSocket -> model -> persistence path, confirm GPU lifecycle impact, update protocol/types/tests together, then update the authoritative docs. Follow `STYLE_GUIDE.md` for code/change discipline.
