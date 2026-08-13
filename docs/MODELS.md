# Model runtime

## Live interview

| Role | Model | Default device | Precision |
|---|---|---|---|
| ASR | Qwen/Qwen3-ASR-1.7B | cuda:1 | BF16 |
| Interviewer | Qwen/Qwen3.5-9B | cuda:0 | INT8 |
| TTS | Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice | cuda:0 | BF16 |
| Content guard | Qwen/Qwen3Guard-Gen-4B | cuda:1 | INT8 |
| Misuse monitor | Qwen/Qwen3.5-4B | cuda:1 | INT8 |

The interviewer and misuse models run with thinking disabled. Interviewer output is intentionally short.

ASR uses automatic language detection on each completed spoken turn. The setup language is the interviewer's default language rather than a hard lock on candidate speech.

TTS is called with automatic language selection. The included adapter synthesizes the complete short interviewer reply to a WAV in memory; it does not yet expose Qwen3-TTS incremental streaming to the browser.

## Final evaluator

After the live conversation and closing audio complete, Qwen/Qwen3.6-27B loads at INT8 with `device_map="auto"` and memory limits across both GPUs.

Each evaluation question receives a separate thinking generation. The stored assessment is only the text after a Qwen thinking block; raw chain-of-thought is not persisted.

The evaluator then performs a separate synthesis reasoning pass. A final non-thinking generation uses `ChoiceLogitsProcessor` to constrain decoding to exactly one of:

- `PROGRESS`
- `NOT_PROGRESS`

Output validity therefore does not depend on parsing an unconstrained prose answer after generation.

The evaluator seed is fixed in runtime configuration to reduce unnecessary run-to-run variance while retaining thinking-mode sampling.

## Lifecycle

1. real-mode ASGI startup preloads live models;
2. one interview reserves the GPU worker;
3. the closing text/audio is generated;
4. evaluation atomically takes worker ownership;
5. live model references are released and CUDA cache is cleared;
6. evaluator loads across both GPUs;
7. criterion passes, synthesis and final choice run;
8. evaluator unloads;
9. live models reload;
10. capacity reopens.

This deliberately trades throughput for final evaluator quality.

## Dependency versions

The real-model requirements pin the Qwen integration packages used by the adapters (`qwen-asr==0.0.6`, `qwen-tts==0.1.1`) and Transformers 5.15.0. The remaining CUDA packages are constrained to compatible major versions so the target machine can select an appropriate PyTorch/CUDA wheel.

## Hardware validation still required

The real model suite must be benchmarked on the target dual-3090 workstation before production use. In particular verify:

- aggregate live-model VRAM;
- INT8 bitsandbytes compatibility with the installed NVIDIA/CUDA stack;
- 27B evaluator placement without unintended CPU offload;
- long-context evaluator memory use;
- ASR/TTS latency;
- evaluator quality against labelled candidate examples.
