# Deployment

`npm run dev` uses Django's development server and Vite and is not a production deployment command.

For production:

1. set a strong `DJANGO_SECRET_KEY`;
2. set `DJANGO_DEBUG=false`;
3. set production `DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_TRUSTED_ORIGINS`;
4. run `npm run build`;
5. run `python backend/manage.py migrate` when migrations are pending;
6. serve Django with a production ASGI server behind TLS;
7. serve `frontend/dist/` from the chosen web server/CDN with SPA fallback routing and proxy `/api` and `/ws` to Django;
8. keep ffmpeg, CUDA, PyTorch and the required Qwen weights available on the GPU host.

The current inference runtime is intentionally single-worker. Run one Django/ASGI application process against one dual-3090 model worker unless the inference architecture is redesigned. Multiple independent web worker processes would each create their own model runtime and are not appropriate for this V1 deployment.

Login/signup rate limiting should be enforced at the reverse proxy or another dedicated production boundary before exposing the site publicly.
