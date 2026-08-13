# Testing

The project defaults to mock-model mode so application behaviour can be tested without GPU model weights.

Run the complete local test command from the project root:

```bash
npm test
```

This performs:

1. `python backend/manage.py check`
2. `python -m pytest backend`
3. `vite build`

The Python tests cover normal interview turns, content-safety redirection, accumulated misuse termination, the multi-criterion evaluator, HTTP session/token behaviour and a Channels WebSocket flow.

Real-model verification must additionally be performed on the target dual-3090 machine because model loading, CUDA placement, latency and memory use cannot be validated by mock tests.
