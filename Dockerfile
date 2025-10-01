# Dockerfile (single image: serve backend + static frontend)
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# system deps (imagem leve)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY src/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy app source
COPY src /app/src

# Copy frontend static assets (assuming frontend files under frontend/ or templates/static)
# Ajuste se seu frontend está em outra pasta
COPY frontend /app/frontend

# Ensure data dirs exist (runtime)
RUN mkdir -p /app/data/db /app/data/export

# Expose port
ENV PORT=8000
EXPOSE 8000

# Environment defaults (can be overridden on Render)
ENV AMZ_DB_PATH=/app/data/db/reviews.db
ENV AMZ_EXPORT_CSV=/app/data/export/reviews_for_dashboard.csv

# Start command - use Flask built-in for simplicity; in prod prefira gunicorn
CMD ["python", "-m", "src.app"]
