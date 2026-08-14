# Models

The fixed model stack is defined in `backend/interviews/services/real_models.py` and `turn_detection.py`. Device and precision changes are code changes, not candidate settings.

| Purpose | Model/source | Device | Runtime precision |
| --- | --- | --- | --- |
| Interviewer + job metadata + final evaluator | `Qwen/Qwen3.6-27B` | GPU 0 + GPU 1 | BitsAndBytes NF4 4-bit weights, BF16 compute |
| Text-to-speech | `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice` via qwentts.cpp | GPU 0 | BF16 GGUF |
| Content safety | `Qwen/Qwen3Guard-Gen-4B` | GPU 0 | INT8 weights, FP16 activations |
| Speech recognition | `Qwen/Qwen3-ASR-1.7B-hf` | GPU 1 | BF16 |
| Misuse monitoring | `Qwen/Qwen3.5-4B` | GPU 1 | INT8 weights, FP16 activations |
| Turn completion | `pipecat-ai/smart-turn-v3` / `smart-turn-v3.2-gpu.onnx` | GPU 1 | FP32 ONNX |
| Voice activity detection | Silero VAD 6.2.1 | CPU | FP32 JIT |

Qwen3.6 is the only general-purpose language model. The same resident instance handles candidate interviewing, job-title metadata and post-interview evaluation. It is loaded with `load_in_4bit=True`, NF4 quantization, nested/double quantization and BF16 compute.

## Resident placement

```text
GPU 0
  Qwen3.6-27B NF4 shard
  Qwen3-TTS-1.7B BF16
  Qwen3Guard-Gen-4B INT8

GPU 1
  Qwen3.6-27B NF4 shard
  Qwen3-ASR-1.7B BF16
  Qwen3.5-4B misuse INT8
  Smart Turn v3.2 FP32

CPU
  Silero VAD
```

The shared Qwen3.6 loader uses a balanced Transformers/Accelerate device map with a 10 GiB placement cap on each GPU. This cap is for Qwen3.6 placement only; it deliberately leaves room for the permanently resident auxiliary models and runtime activations. CPU or disk weight offload is not part of the intended deployment.

`RealModelSuite.load_models()` owns all model instances. Do not create additional checkpoint copies in consumers, views or helper modules.

## Attention backend

All Transformers models explicitly request PyTorch SDPA. The project does not require the external Dao-AILab `flash-attn` package. PyTorch may still select fused Flash-style SDPA kernels internally where the installed PyTorch build and GPU support them.

## Evaluation

Evaluation no longer unloads the realtime stack or launches a second inference engine. The resident Qwen3.6 instance evaluates criteria in microbatches of two, performs the final reasoning pass, then uses the same constrained decoder used elsewhere in the project to return exactly `PROGRESS` or `NOT_PROGRESS`.

Inference ownership remains serialized: one interview or one final evaluation can generate at a time. Residency and execution are separate concerns; all models stay in VRAM even while idle.

## Speech model contracts

- Browser audio is normalized to mono 16 kHz float32 PCM before VAD, Smart Turn or ASR.
- Smart Turn evaluates up to the last 8 seconds of the current candidate turn.
- Qwen3-ASR receives the full accepted accumulated turn.
- Qwen3-TTS runs through the pinned qwentts.cpp C ABI so the main Python environment can stay on Transformers 5.
