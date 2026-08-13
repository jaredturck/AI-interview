# Performance

## Live interview

The intended live placement is:

```text
GPU 0: Qwen3.5-9B INT8 + Qwen3-TTS-0.6B BF16
GPU 1: Qwen3-ASR-1.7B BF16 + Qwen3.5-4B INT8 + Qwen3Guard-Gen-4B INT8
```

Raw parameter storage is comfortably below the combined 48 GB VRAM budget, but actual headroom must be measured with the real packages because quantization metadata, model-specific buffers, attention/KV state and CUDA allocator behavior add overhead beyond raw weights.

A normal typed turn performs safety classification, misuse classification, interviewer generation, output safety classification and TTS. A voice turn adds ASR first. The interviewer and misuse models use no extended thinking and the interviewer response is intentionally short.

The first live interview after process startup will incur model-loading latency. Once loaded, the live stack remains resident until final evaluation needs the GPUs. Production readiness should include a controlled warm-up before accepting the first real candidate.

## Audio transport

The browser now buffers one candidate utterance locally and sends one binary frame when the candidate finishes speaking. The backend previously received 250 ms chunks but only concatenated them before ASR, which added protocol work without reducing inference latency.

TTS WAV data is returned as a binary WebSocket frame rather than base64 JSON, avoiding base64 size/CPU overhead.

## Final evaluator

Qwen3.6-27B runs INT8 across both RTX 3090 GPUs. Evaluation deliberately trades latency for decision quality:

- one reasoning call per configured criterion;
- one final reasoning call across all criterion assessments;
- one tiny constrained output call.

With the current 12-question example rubric, evaluation can be substantially slower than realtime interviewing. That is acceptable because it runs after the live conversation and the candidate-facing completion page polls for the result.

The current raw Transformers implementation does not implement cross-request prefix/KV reuse for the repeated job-description/transcript prefix. That is the largest remaining evaluator optimization opportunity, but it should be implemented only after profiling the real Qwen3.6 runtime on the target hardware.

## Concurrency

One dual-3090 host supports one live interview or one final evaluation at a time. The code deliberately rejects a second live WebSocket rather than allowing overlapping inference on the same models.

Scaling beyond one concurrent candidate requires additional GPU workers or a separately designed inference-serving architecture; it should not be achieved by simply increasing Django web worker count.
