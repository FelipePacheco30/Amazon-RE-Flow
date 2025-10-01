# Dockerfile - single image serving backend + static frontend
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# system deps (kept minimal)
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential \
 && rm -rf /var/lib/apt/lists/*

# copy project into image
COPY . /app

# install requirements from repo root
RUN pip install --no-cache-dir -r /app/requirements.txt

# create runtime dirs
RUN mkdir -p /app/data/db /app/data/export /disk/data/db /disk/data/export

EXPOSE 8000
ENV PORT=8000
# env defaults (override at runtime or on Render)
ENV AMZ_DB_PATH=/disk/data/db/reviews.db
ENV AMZ_EXPORT_CSV=/disk/data/export/reviews_for_dashboard.csv

# optional entrypoint (if you add one)
# COPY entrypoint.sh /app/entrypoint.sh
# RUN chmod +x /app/entrypoint.sh
# ENTRYPOINT ["/app/entrypoint.sh"]

# Use gunicorn for production-like server
CMD ["gunicorn", "src.app:app", "-b", "0.0.0.0:8000", "--workers", "2", "--threads", "4"]
