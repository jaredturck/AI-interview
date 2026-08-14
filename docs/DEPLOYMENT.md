# Deployment

`npm run dev` starts Django development `runserver` and Vite. It is not a production command.

## Runtime requirements

- Python 3.12+, Node/npm and ffmpeg.
- Two RTX 3090 GPUs.
- CUDA-capable PyTorch and vLLM 0.21 for final evaluation.
- `onnxruntime-gpu` with a working CUDA execution provider.
- qwentts.cpp built with CUDA for compute capability 8.6.
- Hugging Face cache/access for the Qwen, Smart Turn and evaluator checkpoints.

The dependency set pins the PyTorch/torchvision pair used by vLLM 0.21. Keep those versions aligned; vLLM's compiled CUDA extensions are sensitive to PyTorch/CUDA binary compatibility.

## Model cache warmup

Production hosts should download large artifacts before accepting interviews:

```bash
hf download pipecat-ai/smart-turn-v3 smart-turn-v3.2-gpu.onnx
hf download 88plug/Qwen3.6-27B-W8A16
```

The W8A16 evaluator checkpoint is roughly 27 GB and is separate from the official `Qwen/Qwen3.6-27B` tokenizer/config cache.

## Production shape

1. Configure strong Django secrets, production hosts/origins and TLS.
2. Install Python/Node dependencies and build `frontend/dist/`.
3. Run migrations.
4. Serve Django with one model-owning ASGI process per dual-GPU worker.
5. Serve the SPA separately with fallback to `index.html`.
6. Proxy `/api`, `/admin` and WebSocket `/ws` correctly.
7. Warm the live model stack before accepting interviews when predictable first-turn latency matters.

Final evaluation starts a non-daemon spawned child process; vLLM then owns its TP=2 GPU workers. The child is joined before the live stack is restored. Do not scale ASGI workers on one GPU host as if inference state were stateless; each process would allocate another model suite.
