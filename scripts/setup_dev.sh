#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ ! -f "$ROOT/config/runtime.toml" ]]; then
    cp "$ROOT/config/runtime.example.toml" "$ROOT/config/runtime.toml"
fi

PYTHON="python"
if command -v python3.12 >/dev/null 2>&1; then
    PYTHON="python3.12"
fi

"$PYTHON" -m venv "$ROOT/.venv"
"$ROOT/.venv/bin/pip" install -r "$ROOT/backend/requirements.txt"

cd "$ROOT/backend"
"$ROOT/.venv/bin/python" manage.py migrate
"$ROOT/.venv/bin/python" manage.py seed_demo

cd "$ROOT/frontend"
npm install

echo "Development setup complete."
