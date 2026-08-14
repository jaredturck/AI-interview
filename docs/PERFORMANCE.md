# Performance

## Live placement

```text
GPU 0 (24 GB)
  Qwen3.5-9B INT8
  Qwen3-TTS-1.7B BF16

GPU 1 (24 GB)
  Qwen3-ASR-1.7B BF16
  Qwen3Guard-Gen-4B INT8
  Qwen3.5-4B INT8
  Smart Turn v3.2 FP32 (~32 MB model)

CPU
  Silero VAD
```

Smart Turn placement is an accuracy/latency choice, not a VRAM workaround. Silero remains CPU-side because its continuous VAD workload is tiny; Smart Turn only runs after pause probes.

## Voice latency path

```text
2 s browser pause probe
 -> ffmpeg decode
 -> Silero VAD
 -> Smart Turn
 -> 0.5 s completion grace OR ~6 s incomplete-turn hold
 -> Qwen3-ASR
 -> safety + misuse + interviewer
 -> Qwen3-TTS
```

The hold timer is conversational policy, not model latency. It exists only when Smart Turn considers a phrase incomplete.

## Transport

The browser sends one binary frame per pause-delimited recording segment. Multiple segments can form one candidate turn. TTS returns WAV bytes as a binary frame; transcript/control data remains JSON.

## Model lifecycle

Development `runserver` preloads the live suite. A production ASGI process may lazy-load it on first reservation. Live weights remain resident across unfinished disconnects and are replaced only for final Qwen3.6 evaluation.

## Concurrency

One dual-3090 model worker supports one live interview or one evaluation at a time. Scaling requires additional model workers or a separately designed inference service; increasing ASGI process count would duplicate model residency.
