#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/backend"
"$ROOT/.venv/bin/python" manage.py recover_interviews
exec "$ROOT/.venv/bin/daphne" -b 127.0.0.1 -p 8000 ai_interviewer.asgi:application
