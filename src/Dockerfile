# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# evitar prompts interativos
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# copiar apenas requirements primeiro (cache)
COPY requirements-flask.txt /app/requirements-flask.txt
RUN apt-get update && apt-get install -y build-essential && \
    pip install --no-cache-dir -r requirements-flask.txt && \
    apt-get remove -y build-essential && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

# copiar o resto do projeto
COPY . /app

# baixar pacotes NLTK necessários na build (para evitar downloads em runtime)
RUN python - <<'PY'\nimport nltk\nnltk.download('punkt')\nnltk.download('stopwords')\nnltk.download('vader_lexicon')\nPY

EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "src.app:app", "--workers", "2", "--threads", "4"]
