# Deployment

`npm run dev` starts Django development `runserver` and Vite. It is not a production command.

## Runtime requirements

- Python 3.12+, Node/npm and ffmpeg.
- CUDA-capable PyTorch for two RTX 3090 GPUs.
- `onnxruntime-gpu` with a working CUDA execution provider.
- qwentts.cpp built with CUDA for compute capability 8.6.
- Hugging Face access/cache for Qwen checkpoints and `pipecat-ai/smart-turn-v3`.

Smart Turn downloads `smart-turn-v3.2-gpu.onnx` through `hf_hub_download()` on first live-model load. Production hosts should prewarm the Hugging Face cache rather than depend on a first-request download.

```bash
hf download pipecat-ai/smart-turn-v3 smart-turn-v3.2-gpu.onnx
```

## Production shape

1. Configure strong Django secrets, production hosts/origins and TLS.
2. Install Python/Node dependencies and build `frontend/dist/`.
3. Run migrations.
4. Serve Django with one model-owning ASGI process per dual-GPU worker.
5. Serve the SPA separately with fallback to `index.html`.
6. Proxy `/api`, `/admin` and WebSocket `/ws` correctly.
7. Warm the live model stack before accepting interviews when predictable first-turn latency matters.

Do not scale ASGI workers on one GPU host as if inference state were stateless; each process would allocate another model suite.
