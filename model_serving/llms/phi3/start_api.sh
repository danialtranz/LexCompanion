#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install -r requirements.txt >/dev/null

export PHI3_MAX_QUEUE_SIZE="${PHI3_MAX_QUEUE_SIZE:-200}"
export PHI3_MAX_CONCURRENCY="${PHI3_MAX_CONCURRENCY:-3}"
export PHI3_REQUEST_TIMEOUT_SECONDS="${PHI3_REQUEST_TIMEOUT_SECONDS:-180}"
export PHI3_ENQUEUE_TIMEOUT_SECONDS="${PHI3_ENQUEUE_TIMEOUT_SECONDS:-2}"
export PHI3_OLLAMA_TIMEOUT_SECONDS="${PHI3_OLLAMA_TIMEOUT_SECONDS:-75}"
export PHI3_DEFAULT_NUM_PREDICT="${PHI3_DEFAULT_NUM_PREDICT:-128}"
export PHI3_DEFAULT_NUM_CTX="${PHI3_DEFAULT_NUM_CTX:-2048}"
export PHI3_DEFAULT_NUM_BATCH="${PHI3_DEFAULT_NUM_BATCH:-256}"
export PHI3_DEFAULT_NUM_THREAD="${PHI3_DEFAULT_NUM_THREAD:-0}"
export PHI3_DEFAULT_NUM_GPU="${PHI3_DEFAULT_NUM_GPU:--1}"
export OLLAMA_HOST="${OLLAMA_HOST:-127.0.0.1:11434}"
export OLLAMA_MODELS="${OLLAMA_MODELS:-$SCRIPT_DIR/.ollama/models}"

uvicorn app:app --host 0.0.0.0 --port 6511 --workers 1
