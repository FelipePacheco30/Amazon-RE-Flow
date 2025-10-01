# Use an explicit base image (important)
FROM python:3.11-slim

# keep logs unbuffered (helpful for cloud logs)
ENV PYTHONUNBUFFERED=1 \
    PORT=8000 \
    AMZ_DB_PATH=/app/data/db/reviews.db \
    AMZ_RAW_CSV=/app/data/raw/reviews_sample.csv

# set working directory for subsequent commands
WORKDIR /app

# install minimal build deps (if needed by some wheels)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# copy requirements.txt from repo root (you said it's in root)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# copy source and frontend
COPY src/ /app/src/
COPY frontend/ /app/frontend/

# copy raw CSVs so we can optionally seed DB at build-time
COPY data/raw/ /app/data/raw/

# ensure directories exist
RUN mkdir -p /app/data/db /app/data/processed

# attempt to seed DB at build time if CSV available (non-fatal)
ARG AMZ_RAW_CSV=/app/data/raw/reviews_sample.csv
ARG AMZ_DB_PATH=/app/data/db/reviews.db
RUN if [ -f "$AMZ_RAW_CSV" ]; then \
      python -m src.main --source "$AMZ_RAW_CSV" --out /app/data/processed/reviews_processed.csv --to-db --db "$AMZ_DB_PATH" || echo "pipeline at build failed (continuing)"; \
    else \
      echo "no raw csv at $AMZ_RAW_CSV, skipping build-time seed"; \
    fi

# copy entrypoint script and make executable
COPY docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# expose port
EXPOSE 8000

# entrypoint will create DB if missing and then start gunicorn
CMD ["/app/entrypoint.sh"]
