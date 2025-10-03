# Use an explicit base image
FROM python:3.11-slim

# keep logs unbuffered (helpful for cloud logs)
ENV PYTHONUNBUFFERED=1 \
    PORT=8000 \
    AMZ_DB_PATH=data/db/reviews.db \
    AMZ_RAW_CSV=data/raw/reviews_sample.csv

WORKDIR /app

# install minimal build deps (if needed by some wheels)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# copy requirements.txt from repo root (you said it's in root)
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

# define local para os dados nltk e torna disponível em runtime
ENV NLTK_DATA=/usr/local/share/nltk_data

# cria o diretório e pré-baixa os pacotes que usamos (punkt, stopwords, vader_lexicon)
RUN mkdir -p "$NLTK_DATA" \
 && python - <<'PY'
import os, nltk
nl = os.environ.get("NLTK_DATA", "/usr/local/share/nltk_data")
os.makedirs(nl, exist_ok=True)
for pkg in ("punkt","stopwords","vader_lexicon"):
    try:
        nltk.download(pkg, download_dir=nl, quiet=True)
    except Exception as e:
        print("NLTK download failed for", pkg, ":", e)
print("NLTK bootstrap done ->", nl)
PY

# copy source and frontend
COPY src/ /src/
COPY frontend/ /frontend/

# ensure directories exist (will be writable at runtime)
RUN mkdir -p /data/db /data/processed /data/raw

# copy entrypoint script and make executable
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

# entrypoint will create DB if missing and then start gunicorn
CMD ["/entrypoint.sh"]
