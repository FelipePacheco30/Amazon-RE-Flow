#!/usr/bin/env bash
set -euo pipefail

# default port
PORT="${PORT:-8000}"

# Make sure Python can import the "src" package no matter where it was copied.
# If repo layout is /app/src -> add /app; if it's /src -> add / (parent dir).
PYTHONPATH="${PYTHONPATH:-}"
if [ -d "/app/src" ]; then
  PYTHONPATH="/app:${PYTHONPATH}"
fi
if [ -d "/src" ]; then
  # parent of /src is / which is already on sys.path normally, but make explicit
  PYTHONPATH="/:${PYTHONPATH}"
fi
export PYTHONPATH

# ensure NLTK data dir exists (if used)
if [ -n "${NLTK_DATA:-}" ]; then
  mkdir -p "$NLTK_DATA"
  chown -R "$(id -u):$(id -g)" "$NLTK_DATA" || true
fi

echo "Starting container"
echo "PORT=$PORT"
echo "PYTHONPATH=$PYTHONPATH"

# If DB missing attempt to create it non-blocking (entrypoint may call pipeline)
# The original entrypoint logic (if any) can be placed here; keep lightweight.
# Finally start Gunicorn serving the Flask app (module 'src.app:app').
exec gunicorn --bind "0.0.0.0:${PORT}" --workers 3 --worker-class sync "src.app:app"
