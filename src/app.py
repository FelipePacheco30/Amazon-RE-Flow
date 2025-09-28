# src/app.py
import os
import threading
import sqlite3
from typing import Dict, Any

import pandas as pd
from flask import Flask, jsonify, request, send_file, render_template, Response
from flask_cors import CORS

# Importa sua pipeline existente e export
from src.main import run_pipeline
from src.export import export_for_dashboard

app = Flask(__name__, template_folder="../frontend/templates", static_folder="../frontend/static")
CORS(app)

# Configs via env vars (padrões locais)
DB_PATH = os.getenv("AMZ_DB_PATH", "data/db/reviews.db")
RAW_CSV = os.getenv("AMZ_RAW_CSV", "data/raw/reviews.csv")
EXPORT_CSV = os.getenv("AMZ_EXPORT_CSV", "data/export/reviews_for_dashboard.csv")


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/api/run", methods=["POST"])
def api_run():
    """
    Inicia o pipeline em background.
    JSON body opcional: {"nrows": 100, "out": "path/out.csv", "to_db": true}
    """
    body = request.get_json(silent=True) or {}
    nrows = body.get("nrows")
    out = body.get("out", "data/processed/reviews_from_api.csv")
    to_db = bool(body.get("to_db", True))
    db = body.get("db", DB_PATH)

    def _job():
        try:
            run_pipeline(source=RAW_CSV, out=out, to_db=to_db, db_path=db, nrows=nrows, log_level="INFO")
        except Exception as e:
            app.logger.exception("Pipeline failed: %s", e)

    thread = threading.Thread(target=_job, daemon=True)
    thread.start()
    return jsonify({"status": "started"})


@app.route("/api/stats")
def api_stats():
    db = request.args.get("db", DB_PATH)
    if not os.path.exists(db):
        return jsonify({"error": "db_not_found"}), 404

    conn = sqlite3.connect(db)
    try:
        df = pd.read_sql_query("SELECT rating, sentiment, product_id FROM reviews", conn)
    finally:
        conn.close()

    if df.empty:
        return jsonify({"total": 0})

    total = int(len(df))
    avg_rating = float(df["rating"].mean())
    pct_pos = float((df["sentiment"] == "positive").mean() * 100)
    pct_neu = float((df["sentiment"] == "neutral").mean() * 100)
    pct_neg = float((df["sentiment"] == "negative").mean() * 100)
    top_products = df["product_id"].value_counts().head(10).to_dict()
    return jsonify({
        "total": total,
        "avg_rating": avg_rating,
        "pct_pos": pct_pos,
        "pct_neu": pct_neu,
        "pct_neg": pct_neg,
        "top_products": top_products
    })


@app.route("/api/reviews")
def api_reviews():
    """
    Retorna reviews em JSON.
    Usa Response para garantir Content-Type application/json.
    """
    db = request.args.get("db", DB_PATH)
    limit = int(request.args.get("limit", 50))
    offset = int(request.args.get("offset", 0))

    if not os.path.exists(db):
        return jsonify({"error": "db_not_found"}), 404

    conn = sqlite3.connect(db)
    try:
        df = pd.read_sql_query(
            "SELECT review_id, product_id, review_date, rating, sentiment, keywords, review_text FROM reviews LIMIT ? OFFSET ?",
            conn,
            params=(limit, offset)
        )
    finally:
        conn.close()

    # Garante JSON e Content-Type correto
    json_str = df.to_json(orient="records", force_ascii=False)
    return Response(json_str, mimetype="application/json")


@app.route("/api/export")
def api_export():
    """
    Gera/atualiza CSV de export a partir do DB e retorna o caminho.
    """
    db = request.args.get("db", DB_PATH)
    out = request.args.get("out", EXPORT_CSV)

    # Garante diretório
    out_dir = os.path.dirname(out) or "."
    os.makedirs(out_dir, exist_ok=True)

    try:
        path, rows = export_for_dashboard(db_path=db, out_path=out)
        # Retorna caminho relativo para o frontend consumir
        rel_path = os.path.relpath(path, start=os.getcwd())
        return jsonify({"path": rel_path, "rows": rows})
    except Exception as e:
        app.logger.exception("Export failed: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route("/download/export")
def download_export():
    """
    Download direto do CSV de export.
    Procura o arquivo em:
      1) caminho absoluto informado via env var (AMZ_EXPORT_CSV)
      2) caminho relativo à working dir atual (os.getcwd())
      3) caminho relativo ao app.root_path (normalmente 'src/')
    Retorna 404 se não encontrar.
    """
    # caminho configurado (padrão relativo)
    cfg_path = os.getenv("AMZ_EXPORT_CSV", EXPORT_CSV)

    # Lista de candidatos (tenta resolver para caminhos absolutos)
    candidates = []
    # se já for absoluto, tenta diretamente
    if os.path.isabs(cfg_path):
        candidates.append(cfg_path)
    else:
        # relativo à working dir atual (provavelmente repo root)
        candidates.append(os.path.abspath(cfg_path))
        # relativo ao app.root_path (onde Flask foi carregado; evita erro de src/data/...)
        candidates.append(os.path.abspath(os.path.join(app.root_path, cfg_path)))
        # também tenta relativo a script (compatibilidade)
        candidates.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", cfg_path)))

    # Dedup e filtra
    seen = set()
    candidates = [p for p in candidates if not (p in seen or seen.add(p))]

    # Procura o primeiro que exista
    found = None
    for p in candidates:
        if os.path.exists(p):
            found = p
            break

    if not found:
        # retorna lista de caminhos verificados para debug (útil localmente)
        return jsonify({
            "error": "file_not_found",
            "requested": cfg_path,
            "checked_paths": candidates
        }), 404

    # Serve como attachment para forçar download
    return send_file(found, as_attachment=True, download_name=os.path.basename(found))

# Serve frontend
@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    # Porta 8000 por compatibilidade com o que testamos antes
    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=True)
