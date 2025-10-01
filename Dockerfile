# Use an explicit base image
FROM python:3.11-slim

# keep logs unbuffered (helpful for cloud logs)
ENV PYTHONUNBUFFERED=1 \
    PORT=8000 \
    AMZ_DB_PATH=/app/data/db/reviews.db \
    AMZ_RAW_CSV=/app/data/raw/reviews_sample.csv

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

# ensure directories exist (will be writable at runtime)
RUN mkdir -p /app/data/db /app/data/processed /app/data/raw

# copy entrypoint script and make executable
COPY docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

# entrypoint will create DB if missing and then start gunicorn
CMD ["/app/entrypoint.sh"]
