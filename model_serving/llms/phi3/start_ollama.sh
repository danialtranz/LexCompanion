#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

RUNTIME_DIR="$SCRIPT_DIR/.ollama-runtime"
BIN_DIR="$RUNTIME_DIR/bin"
OLLAMA_BIN="$BIN_DIR/ollama"
MODELS_DIR="$SCRIPT_DIR/.ollama/models"
LOG_FILE="$SCRIPT_DIR/.ollama/ollama.log"
PID_FILE="$SCRIPT_DIR/.ollama/ollama.pid"

mkdir -p "$BIN_DIR" "$MODELS_DIR" "$(dirname "$LOG_FILE")"

if [ ! -x "$OLLAMA_BIN" ]; then
  ARCH="$(uname -m)"
  case "$ARCH" in
    x86_64)
      PKG_BASENAME="ollama-linux-amd64"
      ;;
    aarch64|arm64)
      PKG_BASENAME="ollama-linux-arm64"
      ;;
    *) echo "Unsupported architecture: $ARCH"; exit 1 ;;
  esac

  TMP_ZST="$RUNTIME_DIR/ollama.tar.zst"
  echo "[setup] Downloading local Ollama runtime..."

  if curl -fsSL "https://github.com/ollama/ollama/releases/latest/download/${PKG_BASENAME}.tar.zst" -o "$TMP_ZST"; then
    if command -v zstd >/dev/null 2>&1; then
      tar --zstd -xf "$TMP_ZST" -C "$RUNTIME_DIR"
      rm -f "$TMP_ZST"
    elif python3 - <<'PY'
import importlib.util, sys
sys.exit(0 if importlib.util.find_spec("zstandard") else 1)
PY
    then
      python3 - "$TMP_ZST" "$RUNTIME_DIR" <<'PY'
import io
import pathlib
import tarfile
import zstandard as zstd
import sys

src = pathlib.Path(sys.argv[1])
dst = pathlib.Path(sys.argv[2])

with src.open("rb") as fh:
    dctx = zstd.ZstdDecompressor()
    with dctx.stream_reader(fh) as reader:
        data = reader.read()
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:") as tf:
            tf.extractall(dst)
PY
      rm -f "$TMP_ZST"
    else
      echo "Missing zstd support. Install once in venv:"
      echo "  source .venv/bin/activate && pip install zstandard"
      echo "Or install system package: sudo apt-get install -y zstd"
      exit 1
    fi
  else
    echo "Failed to download local Ollama runtime (.tar.zst)."
    exit 1
  fi

  if [ ! -x "$OLLAMA_BIN" ] && [ -x "$RUNTIME_DIR/ollama" ]; then
    mkdir -p "$BIN_DIR"
    cp "$RUNTIME_DIR/ollama" "$OLLAMA_BIN"
    chmod +x "$OLLAMA_BIN"
  fi

  if [ ! -x "$OLLAMA_BIN" ]; then
    echo "Ollama binary not found after extraction."
    exit 1
  fi
fi

if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" >/dev/null 2>&1; then
  echo "Ollama local server already running with PID $(cat "$PID_FILE")"
else
  echo "[1/2] Starting local Ollama server..."
  export OLLAMA_MODELS="$MODELS_DIR"
  export OLLAMA_HOST="${OLLAMA_HOST:-127.0.0.1:11434}"
  export OLLAMA_MAX_LOADED_MODELS="${OLLAMA_MAX_LOADED_MODELS:-1}"
  export OLLAMA_NUM_PARALLEL="${OLLAMA_NUM_PARALLEL:-2}"
  export OLLAMA_KEEP_ALIVE="${OLLAMA_KEEP_ALIVE:-15m}"
  export OLLAMA_FLASH_ATTENTION="${OLLAMA_FLASH_ATTENTION:-1}"
  nohup "$OLLAMA_BIN" serve >"$LOG_FILE" 2>&1 &
  echo $! >"$PID_FILE"
fi

sleep 2

echo "[2/2] Pulling model qwen3:8b into project storage..."
export OLLAMA_MODELS="$MODELS_DIR"
export OLLAMA_HOST="${OLLAMA_HOST:-127.0.0.1:11434}"
"$OLLAMA_BIN" pull qwen3:8b

echo "Ollama local is ready."
echo " - Binary: $OLLAMA_BIN"
echo " - Models: $MODELS_DIR"
echo " - Host:   ${OLLAMA_HOST}"
echo " - Log:    $LOG_FILE"
