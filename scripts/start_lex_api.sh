#!/usr/bin/env bash
# Chạy Lex Companion API (port 5999) từ root repo.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -d ".venv" ]]; then
  echo "Chưa có .venv. Chạy: uv venv && uv sync"
  exit 1
fi

export PYTHONPATH="$ROOT"
exec "$ROOT/.venv/bin/python" -m api.lex_companion_server
