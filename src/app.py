# src/app.py
import os
import threading
import sqlite3
from typing import Dict, Any
import pandas as pd

from flask import Flask, current_app, request, jsonify, send_file, render_template
from flask_cors import CORS

# Importa sua pipeline existente e export
from src.main import run_pipeline
from src.export import export_for_dashboard

# Flask app (frontend templates / static em frontend/)
app = Flask(__name__, template_folder="../frontend/templates", static_folder="../frontend/static")
CORS(app)

# Configs via env vars (padrões locais) — carregadas no app.config para uso uniforme
app.config['DB_PATH'] = os.getenv("AMZ_DB_PATH", "data/db/reviews.db")
app.config['RAW_CSV'] = os.getenv("AMZ_RAW_CSV", "data/raw/reviews.csv")
app.config['EXPORT_CSV'] = os.getenv("AMZ_EXPORT_CSV", "data/export/reviews_for_dashboard.csv")


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/api/run", methods=["POST"])
def api_run():
    """
    Inicia o pipeline em background.
    JSON body opcional: {"nrows": 100, "out": "path/out.csv", "to_db": true, "db": "path/to/db"}
    Por segurança: se nrows for enviado e for baixo, pode sobrescrever DB — o cliente deve evitar enviar nrows para runs full.
    """
    body = request.get_json(silent=True) or {}
    nrows = body.get("nrows")
    out = body.get("out", "data/processed/reviews_from_api.csv")
    to_db = bool(body.get("to_db", True))
    db = body.get("db", current_app.config['DB_PATH'])

    def _job():
        try:
            run_pipeline(source=current_app.config['RAW_CSV'], out=out, to_db=to_db, db_path=db, nrows=nrows, log_level="INFO")
        except Exception as e:
            app.logger.exception("Pipeline failed: %s", e)

    thread = threading.Thread(target=_job, daemon=True)
    thread.start()
    return jsonify({"status": "started"})


@app.route("/api/stats")
def api_stats():
    db = request.args.get("db", current_app.config['DB_PATH'])
    if not os.path.exists(db):
        return jsonify({"error": "db_not_found", "path": db}), 404

    conn = _connect_db(db)
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


def _connect_db(db_path=None):
    """
    Conecta ao SQLite. Se db_path não for informado, usa current_app.config['DB_PATH'].
    Retorna conexão com row_factory = sqlite3.Row (permite dict-like rows).
    """
    if db_path is None:
        try:
            db_path = current_app.config.get('DB_PATH', 'data/db/reviews.db')
        except RuntimeError:
            # current_app não disponível (chamada fora do contexto) -> fallback
            db_path = 'data/db/reviews.db'

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/api/reviews')
def api_reviews():
    """
    GET /api/reviews?limit=50&offset=0
    - limit: quantas linhas retornar (int, padrão 50, máximo 5000)
    - offset: deslocamento (int, padrão 0)
    Retorna JSON com formato compatível: { total?: Number, rows: [ ... ] }
    (mantive compatibilidade anterior: também funciona se você ainda quiser retornar só um array)
    """
    # valida params
    try:
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
    except (TypeError, ValueError):
        return jsonify({"error": "limit and offset must be integers"}), 400

    # clamps de segurança
    limit = max(1, min(limit, 5000))
    offset = max(0, offset)

    db_path = request.args.get('db', current_app.config['DB_PATH'])
    if not os.path.exists(db_path):
        return jsonify({"error": "db_not_found", "path": db_path}), 500

    query = """
        SELECT
            review_id,
            product_id,
            review_date,
            rating,
            sentiment,
            keywords,
            review_text
        FROM reviews
        ORDER BY review_date DESC
        LIMIT ? OFFSET ?
    """

    conn = _connect_db(db_path)
    try:
        cur = conn.execute(query, (limit, offset))
        rows = [dict(r) for r in cur.fetchall()]
        # também busco o total absoluto para permitir paginação no frontend
        total_cur = conn.execute("SELECT COUNT(*) as cnt FROM reviews")
        total = total_cur.fetchone()["cnt"]
    finally:
        conn.close()

    return jsonify({"total": int(total), "rows": rows})


@app.route("/api/export")
def api_export():
    """
    Gera/atualiza CSV de export a partir do DB e retorna o caminho.
    """
    db = request.args.get("db", current_app.config['DB_PATH'])
    out = request.args.get("out", current_app.config['EXPORT_CSV'])

    # Garante diretório
    out_dir = os.path.dirname(out) or "."
    os.makedirs(out_dir, exist_ok=True)

    try:
        path, rows = export_for_dashboard(db_path=db, out_path=out)
        rel_path = os.path.relpath(path, start=os.getcwd())
        return jsonify({"path": rel_path, "rows": rows})
    except Exception as e:
        app.logger.exception("Export failed: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route("/download/export")
def download_export():
    """
    Download direto do CSV de export.
    Tenta múltiplos candidatos para localizar o CSV (working dir, app.root_path, etc).
    """
    cfg_path = os.getenv("AMZ_EXPORT_CSV", current_app.config['EXPORT_CSV'])

    candidates = []
    if os.path.isabs(cfg_path):
        candidates.append(cfg_path)
    else:
        candidates.append(os.path.abspath(cfg_path))
        candidates.append(os.path.abspath(os.path.join(app.root_path, cfg_path)))
        candidates.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", cfg_path)))

    # Dedup
    seen = set()
    candidates = [p for p in candidates if not (p in seen or seen.add(p))]

    for p in candidates:
        if os.path.exists(p):
            return send_file(p, as_attachment=True, download_name=os.path.basename(p))

    return jsonify({
        "error": "file_not_found",
        "requested": cfg_path,
        "checked_paths": candidates
    }), 404


@app.route("/api/db-info")
def api_db_info():
    """
    Rota de debug: retorna o DB em uso e contagem de linhas (útil localmente).
    """
    db_path = current_app.config.get('DB_PATH', 'data/db/reviews.db')
    candidates = {
        "app_config_db_path": db_path,
        "cwd_abs_path": os.path.abspath(db_path),
        "app_root_relative": os.path.abspath(os.path.join(app.root_path, db_path)),
    }
    exists = os.path.exists(db_path)
    rows = None
    if exists:
        try:
            conn = _connect_db(db_path)
            cur = conn.execute("SELECT COUNT(*) as cnt FROM reviews")
            rows = cur.fetchone()["cnt"]
            conn.close()
        except Exception as e:
            rows = f"error: {str(e)}"
    return jsonify({"candidates": candidates, "exists": exists, "rows": rows})


# Serve frontend
@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    # Porta 8000 por compatibilidade com o que testamos antes
    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=True)
