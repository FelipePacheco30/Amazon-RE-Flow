#!/usr/bin/env bash
set -euo pipefail

# configura a porta padrão (pode ser sobrescrita por env)
PORT="${PORT:-8000}"

# caminhos (ajuste se seu projeto usa paths diferentes)
DB_PATH="${AMZ_DB_PATH:-/data/db/reviews.db}"
RAW_CSV="${AMZ_RAW_CSV:-data/raw/reviews_sample.csv}"
WORKERS="${GUNICORN_WORKERS:-2}"

echo "Starting container"
echo "PORT=${PORT}"
echo "DB_PATH=${DB_PATH}"
echo "RAW_CSV=${RAW_CSV}"

# se DB não existir e houver CSV bruto, tenta rodar pipeline para criar DB
if [ ! -f "${DB_PATH}" ]; then
  if [ -f "${RAW_CSV}" ]; then
    echo "DB not found at ${DB_PATH}"
    echo "Attempting to run pipeline to create DB from ${RAW_CSV}"
    python -m src.main --source "${RAW_CSV}" --out "${DB_PATH}" --to_db true || {
      echo "Pipeline failed — continuing without DB (app may error)"
    }
  else
    echo "DB not found and raw CSV missing (${RAW_CSV}). Starting without DB."
  fi
fi

# start gunicorn (module wsgi: app is expected to be available)
exec gunicorn -w "${WORKERS}" -b 0.0.0.0:"${PORT}" --access-logfile - --error-logfile - src.app:app
