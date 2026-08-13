# Deployment

`npm run dev` starts Django's development server and Vite. It is not a production deployment command.

For production:

1. configure a strong `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=false`, production allowed hosts and trusted CSRF origins;
2. run `npm install` and `npm run build`;
3. run `python backend/manage.py migrate`;
4. serve Django with a production ASGI server behind TLS;
5. serve `frontend/dist/` from the web server/CDN with SPA fallback to `index.html` for candidate routes;
6. proxy `/api` and `/admin` to Django and `/ws` to Django/ASGI with WebSocket upgrade support;
7. keep ffmpeg, CUDA, PyTorch and required Qwen weights available on the GPU host.

The inference runtime is intentionally single-worker. Do not scale the Django/ASGI process count on one GPU host as though model state were stateless; each independent process would create its own model runtime.

The React language selector writes Django's `django_language` cookie so custom API/admin-compatible translation selection can use the same preference. Django admin also has its own language selector.

Rate-limit login/signup and other abuse-prone public endpoints at the reverse proxy or another agreed production boundary.
