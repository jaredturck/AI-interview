#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python -m compileall -q "$ROOT/backend"
python "$ROOT/scripts/static_validate.py"

if [[ -x "$ROOT/.venv/bin/python" ]]; then
    cd "$ROOT/backend"
    "$ROOT/.venv/bin/python" manage.py check
    "$ROOT/.venv/bin/pytest" -q
fi

if [[ -d "$ROOT/frontend/node_modules" ]]; then
    cd "$ROOT/frontend"
    npm run build
fi

echo "Checks complete."
