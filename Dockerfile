FROM python:3.11-slim

# system deps
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# copy requirements from repo root
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# copy app
COPY . /app

# make data dir writable
RUN mkdir -p /app/data/db && chmod -R a+rw /app/data

ENV PORT=8000
ENV AMZ_DB_PATH=/app/data/db/reviews.db
ENV FLASK_ENV=production

# entrypoint will ensure DB exists (see scripts/entrypoint.sh)
COPY scripts/entrypoint.sh /app/scripts/entrypoint.sh
RUN chmod +x /app/scripts/entrypoint.sh

EXPOSE 8000

CMD ["/app/scripts/entrypoint.sh"]
