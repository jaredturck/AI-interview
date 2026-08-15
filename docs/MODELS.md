# Models

The fixed model stack is defined in `backend/interviews/services/real_models.py` and `turn_detection.py`. Device and precision changes are code changes, not candidate settings.

| Purpose | Model/source | Device | Runtime precision |
| --- | --- | --- | --- |
| Interviewer + final evaluator | `Qwen/Qwen3.5-9B` | GPU 0 | BitsAndBytes INT8 weights, FP16 compute |
| Text-to-speech | `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice` via qwentts.cpp | GPU 0 | BF16 GGUF |
| Content safety | `Qwen/Qwen3Guard-Gen-4B` | GPU 1 | INT8 weights, FP16 activations |
| Speech recognition | `Qwen/Qwen3-ASR-1.7B-hf` | GPU 1 | BF16 |
| Misuse monitoring | `Qwen/Qwen3.5-4B` | GPU 1 | INT8 weights, FP16 activations |
| Turn completion | `pipecat-ai/smart-turn-v3` / `smart-turn-v3.2-gpu.onnx` | GPU 1 | FP32 ONNX |
| Voice activity detection | Silero VAD 6.2.1 | CPU | FP32 JIT |

Qwen3.5-9B is the only general-purpose language model. The same resident instance handles candidate interviewing, job-title metadata and post-interview evaluation. It is loaded through the text-only `Qwen3_5ForCausalLM` class with `AutoTokenizer`, so the vision tower is not instantiated. The text weights use `load_in_8bit=True` with FP16 compute.

## Resident placement

```text
GPU 0
  Qwen3.5-9B INT8
  Qwen3-TTS-1.7B BF16

GPU 1
  Qwen3-ASR-1.7B BF16
  Qwen3Guard-Gen-4B INT8
  Qwen3.5-4B misuse INT8
  Smart Turn v3.2 FP32

CPU
  Silero VAD
```

Qwen3.5-9B uses a root device map pinned to GPU 0, so every Qwen3.5-9B layer and matrix multiplication stays on one RTX 3090 instead of moving hidden states between cards. Qwen3-TTS remains on GPU 0 because TTS runs after interviewer generation and is idle during final evaluation. The remaining realtime models stay on GPU 1. CPU or disk weight offload is not part of the deployment.

`RealModelSuite.load_models()` owns all model instances. Do not create additional checkpoint copies in consumers, views or helper modules.

## Attention backend

Qwen3.5-9B keeps `attn_implementation='sdpa'` for its 8 full-attention layers. Its 24 Gated DeltaNet layers use the optimized Flash Linear Attention (`fla`) delta-rule kernels and `causal-conv1d` kernels when both packages are available; startup prints the selected DeltaNet backend so fallback execution is visible. The external Dao-AILab `flash-attn` package is still not used.

## Evaluation

Evaluation no longer unloads the realtime stack or launches a second inference engine. The resident Qwen3.5-9B instance evaluates criteria in microbatches of two, performs the final reasoning pass, then uses the same constrained decoder used elsewhere in the project to return exactly `PROGRESS` or `NOT_PROGRESS`.

Inference ownership remains serialized: one interview or one final evaluation can generate at a time. Residency and execution are separate concerns; all models stay in VRAM even while idle.

## Speech model contracts

- Browser audio is normalized to mono 16 kHz float32 PCM before VAD, Smart Turn or ASR.
- Smart Turn evaluates up to the last 8 seconds of the current candidate turn.
- Qwen3-ASR receives the full accepted accumulated turn.
- Qwen3-TTS runs through the pinned qwentts.cpp C ABI so the main Python environment can stay on Transformers 5.
