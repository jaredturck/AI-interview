# Deployment

`npm run dev` is for local development only.

For production:

1. create `config/runtime.toml` with production Django settings and `mode = "real"`;
2. run `npm run build`;
3. run `python backend/manage.py migrate` when schema migrations are pending;
4. serve Django through a production ASGI process behind TLS;
5. serve `frontend/dist/` through the chosen web server/CDN and route `/api` and `/ws` to Django;
6. ensure ffmpeg, CUDA, PyTorch and the required model weights are available on the GPU host.

The current runtime coordinates one dual-GPU worker. During a live interview it owns the realtime suite; during post-interview evaluation it owns Qwen3.6-27B across both GPUs.
