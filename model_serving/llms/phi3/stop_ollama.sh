#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/.ollama/ollama.pid"

if [ ! -f "$PID_FILE" ]; then
  echo "No PID file found. Ollama local may not be running."
  exit 0
fi

PID="$(cat "$PID_FILE")"
if kill -0 "$PID" >/dev/null 2>&1; then
  kill "$PID"
  echo "Stopped local Ollama server PID $PID"
else
  echo "Process $PID is not running."
fi

rm -f "$PID_FILE"
