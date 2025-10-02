# Procfile
web: gunicorn --chdir . -w 4 -k sync -b 0.0.0.0:$PORT --timeout 120 src.app:app
