# Performance

## Live worker

```text
GPU 0: Qwen3.5-9B INT8 + Qwen3-TTS-0.6B BF16
GPU 1: Qwen3-ASR-1.7B BF16 + Qwen3.5-4B INT8 + Qwen3Guard-Gen-4B INT8
```

A normal typed turn performs input safety, misuse classification, interviewer generation, output safety and TTS. Voice adds ASR. The interviewer is non-thinking and output-capped for latency.

Django development `runserver` preloads the live stack before accepting interviews. A production worker can also load the live stack on its first interview reservation if it has not already been warmed. Once resident, the stack remains loaded until final evaluation needs both GPUs. Staff job metadata extraction reuses the same 9B model and is refused while a live interview/evaluation owns the worker.

## Transport

The browser buffers one utterance and sends one binary WebSocket frame. TTS WAV is returned as a binary frame, avoiding base64 JSON overhead.

## Final evaluator

Qwen3.6-27B runs INT8 across both GPUs. Evaluation intentionally trades latency for decision quality: one reasoning call per stored Job criterion, one final reasoning call and one constrained output call. Repeated transcript/job prefix reuse remains an optimization candidate only after profiling the real runtime.

## Concurrency

One dual-3090 host supports one live interview or one final evaluation at a time. Scaling requires additional model workers or a separately designed inference-serving architecture, not simply extra Django web processes.
