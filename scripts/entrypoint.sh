#!/usr/bin/env bash
set -euo pipefail

# default DB path (use env AMZ_DB_PATH to override)
DB_PATH="${AMZ_DB_PATH:-/app/data/db/reviews.db}"
RAW_CSV="${AMZ_RAW_CSV:-/app/data/raw/reviews_sample.csv}"
OUT_CSV="/app/data/processed/reviews_from_api.csv"

# If DB missing, try to generate it by running pipeline (if available)
if [ ! -f "$DB_PATH" ]; then
  echo "DB not found at $DB_PATH"
  # prefer to run pipeline if script exists; adapt arguments as your pipeline expects
  if python -c "import src.main" >/dev/null 2>&1; then
    echo "Attempting to run pipeline to create DB from $RAW_CSV"
    # Adjust flags if your pipeline CLI is different
    python -m src.main --source "$RAW_CSV" --out "$OUT_CSV" --to-db --db "$DB_PATH" || {
      echo "Pipeline failed — continuing without DB (app may error)"
    }
  else
    echo "Pipeline entrypoint not found — cannot create DB automatically"
  fi
else
  echo "DB exists at $DB_PATH — skipping seed"
fi

# Start Gunicorn (or use flask run for simpler)
exec gunicorn -w 4 -b 0.0.0.0:${PORT:-8000} src.app:app
