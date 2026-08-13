# Deployment notes

## Intended V1 topology

A single dual-RTX-3090 host runs one Django/Daphne process and owns one model worker. React should be built to static assets and served by a normal reverse proxy in production.

Do not start multiple Daphne workers against the same two GPUs: model capacity ownership is intentionally process-local in this V1.

## Configuration

Copy:

```bash
cp config/runtime.example.toml config/runtime.toml
```

Set at minimum:

- a strong Django `secret_key`;
- `debug = false`;
- real `allowed_hosts`;
- real `csrf_trusted_origins`;
- recruitment contact address;
- `models.mode = "real"` when the model environment is ready.

`config/runtime.toml` is ignored by Git and should be treated as a deployment configuration/secret file.

## Reverse proxy

Production traffic should terminate TLS at a reverse proxy and forward:

- `/api/` and `/admin/` to Daphne HTTP;
- `/ws/` as an upgraded WebSocket connection.

Apply conservative request and connection rate limits at the proxy. Keep WebSocket timeouts longer than the configured interview duration.

## Database

SQLite is included for development and a single-machine prototype. Use PostgreSQL before real multi-user production deployment and configure normal encrypted backups, retention and deletion processes for recruitment records.

## Model startup

In real mode `ai_interviewer.asgi` loads the live model suite before the ASGI application begins serving candidates. This makes startup intentionally slow but prevents the first candidate from paying the model download/load penalty.

Download model weights ahead of a production interview window and verify that the Hugging Face cache has sufficient disk space.

## GPU lifecycle

The evaluator intentionally takes exclusive control of both GPUs after an interview. During that period the API reports that the worker is busy and the frontend waits for capacity.

This is a quality-first design. Add additional complete GPU workers for concurrency rather than reducing evaluator precision or placing multiple independent runtimes on the same GPUs.
