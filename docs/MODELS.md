# Models

The model stack is fixed in `backend/interviews/services/real_models.py` and `turn_detection.py`. Device/precision changes are code changes, not runtime candidate settings.

| Purpose | Model/source | Device | Runtime precision |
| --- | --- | --- | --- |
| Interviewer + job metadata | `Qwen/Qwen3.5-9B` | GPU 0 | INT8 weights, FP16 activations |
| Text-to-speech | `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice` via qwentts.cpp | GPU 0 | BF16 GGUF |
| Speech recognition | `Qwen/Qwen3-ASR-1.7B-hf` | GPU 1 | BF16 |
| Turn completion | `pipecat-ai/smart-turn-v3` / `smart-turn-v3.2-gpu.onnx` | GPU 1 | FP32 ONNX |
| Voice activity detection | Silero VAD 6.2.1 | CPU | FP32 JIT |
| Content safety | `Qwen/Qwen3Guard-Gen-4B` | GPU 1 | INT8 weights, FP16 activations |
| Misuse monitoring | `Qwen/Qwen3.5-4B` | GPU 1 | INT8 weights, FP16 activations |
| Final evaluator | `Qwen/Qwen3.6-27B` | GPU 0 + GPU 1 | INT8 weights, FP16 activations |

Smart Turn is GPU-resident for its unquantized model/accuracy path. Silero stays on CPU because its tiny VAD workload is already sub-millisecond-class and avoids unnecessary GPU scheduling for continuous speech filtering.

## Live load order

```text
GPU 0: Qwen3-TTS -> Qwen3.5-9B interviewer
GPU 1: Qwen3-ASR -> Smart Turn -> Qwen3Guard -> Qwen3.5-4B misuse
CPU:   Silero VAD (owned by TurnDetector)
```

`RealModelSuite.load_live()` owns all live model instances. Do not create additional model copies in consumers, views or helper modules.

## Evaluation handoff

`load_evaluator()` releases the live stack before loading Qwen3.6-27B across both GPUs. `finish_evaluation()` restores the live stack. ONNX Smart Turn is released with the rest of the live suite.

## Speech model contracts

- Browser audio is normalized to mono 16 kHz float32 PCM before VAD, Smart Turn or ASR.
- Smart Turn evaluates up to the last 8 seconds of the **current** candidate turn.
- Qwen3-ASR receives the full accepted accumulated turn.
- Qwen3-TTS runs through the pinned qwentts.cpp C ABI so the main Python environment can stay on Transformers 5.
