# Architecture review

The current V2 product boundary is stable:

```text
Candidate React SPA -> Django JSON + Channels -> local realtime model suite
Staff Django Admin  -> Django ORM
Completed interview -> Qwen3.5-9B evaluation -> binary stage-one outcome
```

## Invariants

- Jobs become immutable recruitment snapshots once the first application exists.
- Candidate resources are owned through authenticated `JobApplication.user`.
- One dual-GPU worker handles one live interview or one evaluation at a time.
- Safety, misuse, interview stopping and final recruitment evaluation remain separate decisions.
- Interview timing is server-authoritative: semantic `CONTINUE` / `WRAP_UP` / `END` control is bounded by a forced 13-minute wrap-up and 15-minute hard stop.
- Confirmed text is persisted; raw microphone audio is not.
- Candidate and interviewer audio use bounded `audio_start` / binary-chunk / `audio_end` framing rather than one unbounded WebSocket message.
- Model/device choices are fixed code-level architecture, not candidate settings.
- Current voice turn-taking and transport are documented in `VOICE_PIPELINE.md`.

## Review before major changes

Trace the full browser -> WebSocket -> model -> persistence path, confirm GPU lifecycle impact, update protocol/types/tests together, then update the authoritative docs. Follow `STYLE_GUIDE.md` for code/change discipline.
