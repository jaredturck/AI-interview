# Deployment

`npm run dev` starts Django development `runserver`, Vite and the admin Sass watcher. It is not a production command.

## Runtime requirements

- Python 3.12+, Node/npm and ffmpeg.
- Two RTX 3090 GPUs.
- CUDA-capable PyTorch + Transformers + BitsAndBytes.
- `onnxruntime-gpu` with a working CUDA execution provider.
- qwentts.cpp built with CUDA for compute capability 8.6.
- Hugging Face cache/access for Qwen3.6, Qwen3-ASR, Qwen3Guard, Qwen3.5-4B and Smart Turn.

The project intentionally uses PyTorch SDPA and does not depend on the external `flash-attn` package. vLLM is not part of the inference stack.

## Model cache warmup

Production hosts should download large artifacts before accepting interviews:

```bash
hf download Qwen/Qwen3.6-27B
hf download Qwen/Qwen3-ASR-1.7B-hf
hf download Qwen/Qwen3Guard-Gen-4B
hf download Qwen/Qwen3.5-4B
hf download pipecat-ai/smart-turn-v3 smart-turn-v3.2-gpu.onnx
```

Qwen3.6 is quantized to NF4 by BitsAndBytes when loaded. The application uses the text-only `Qwen3_5ForCausalLM` class with `AutoTokenizer`, so the checkpoint's vision tower is not instantiated. No separate pre-quantized evaluator checkpoint is required.

## Production shape

1. Configure strong Django secrets, production hosts/origins and TLS.
2. Install Python/Node dependencies and build `frontend/dist/` plus the admin CSS.
3. Run migrations.
4. Serve Django with one model-owning ASGI process per dual-GPU worker.
5. Serve the SPA separately with fallback to `index.html`.
6. Proxy `/api`, `/admin` and WebSocket `/ws` correctly.
7. Warm the complete resident model stack before accepting interviews when predictable first-turn latency matters.

All models remain resident after startup. Final evaluation uses the same Qwen3.6 instance as live interviewing, so there is no evaluator process or model swap. Do not scale ASGI workers on one GPU host as if inference state were stateless; each process would allocate another complete model suite.
