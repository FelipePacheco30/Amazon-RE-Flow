#!/usr/bin/env bash
set -e

DB_PATH=${AMZ_DB_PATH:-/app/data/db/reviews.db}
RAW_CSV=${AMZ_RAW_CSV:-/app/data/raw/reviews_sample.csv}
PORT=${PORT:-8000}

# ensure db directory
mkdir -p "$(dirname "$DB_PATH")"
mkdir -p /app/data/processed

# If DB missing, try to create from CSV (non-fatal)
if [ ! -f "$DB_PATH" ]; then
  if [ -f "$RAW_CSV" ]; then
    echo "DB not found at $DB_PATH — creating from $RAW_CSV"
    python -m src.main --source "$RAW_CSV" --out /app/data/processed/reviews_processed.csv --to-db --db "$DB_PATH" || echo "Pipeline failed at startup (continuing without DB)"
  else
    echo "DB not found and raw CSV missing ($RAW_CSV). Starting without DB."
  fi
else
  echo "DB found at $DB_PATH — skipping seed."
fi

# start gunicorn (increase timeout to avoid worker timeouts on slow startups)
exec gunicorn -w 2 -b 0.0.0.0:${PORT} --timeout 120 "src.app:app"
