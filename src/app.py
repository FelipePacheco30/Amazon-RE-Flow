# src/app.py
import os
import threading
import sqlite3
from typing import Dict, Any

from flask import Flask, current_app, request, jsonify, send_file, render_template
from flask_cors import CORS

import pandas as pd

# Importa sua pipeline existente e export
from src.main import run_pipeline
from src.export import export_for_dashboard

# --- App Flask --------------------------------------------------------------
app = Flask(
    __name__,
    template_folder="../frontend/templates",
    static_folder="../frontend/static"
)
CORS(app)

# Configs via env vars (padrões locais) - armazenadas em app.config para fácil acesso
# Use absolute paths so different working directories don't break things
app.config['DB_PATH'] = os.path.abspath(os.getenv("AMZ_DB_PATH", "data/db/reviews.db"))
app.config['RAW_CSV'] = os.path.abspath(os.getenv("AMZ_RAW_CSV", "data/raw/reviews.csv"))
app.config['EXPORT_CSV'] = os.path.abspath(os.getenv("AMZ_EXPORT_CSV", "data/export/reviews_for_dashboard.csv"))

# convenience top-level variables for old codepaths (optional)
DB_PATH = app.config['DB_PATH']
RAW_CSV = app.config['RAW_CSV']
EXPORT_CSV = app.config['EXPORT_CSV']


# --- Health -----------------------------------------------------------------
@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


# --- Run pipeline (background) ----------------------------------------------
@app.route("/api/run", methods=["POST"])
def api_run():
    """
    Inicia o pipeline em background.
    JSON body opcional: {"nrows": 100, "out": "path/out.csv", "to_db": true, "db": "path/to.db"}
    """
    body = request.get_json(silent=True) or {}
    nrows = body.get("nrows")
    out = body.get("out", "data/processed/reviews_from_api.csv")
    to_db = bool(body.get("to_db", True))
    db = body.get("db", app.config['DB_PATH'])
    raw_csv = body.get("raw", app.config['RAW_CSV'])

    def _job():
        try:
            # usa a função run_pipeline que já existe no projeto
            run_pipeline(source=raw_csv, out=out, to_db=to_db, db_path=db, nrows=nrows, log_level="INFO")
        except Exception as e:
            app.logger.exception("Pipeline background job failed: %s", e)

    thread = threading.Thread(target=_job, daemon=True)
    thread.start()
    return jsonify({"status": "started"}), 202


# --- Stats ------------------------------------------------------------------
@app.route("/api/stats")
def api_stats():
    db = request.args.get("db", app.config['DB_PATH'])
    if not os.path.exists(db):
        return jsonify({"error": "db_not_found", "path": db}), 404

    conn = sqlite3.connect(db)
    try:
        df = pd.read_sql_query("SELECT rating, sentiment, product_id FROM reviews", conn)
    finally:
        conn.close()

    if df.empty:
        return jsonify({"total": 0, "avg_rating": None, "pct_pos": 0, "pct_neu": 0, "pct_neg": 0, "top_products": {}})

    total = int(len(df))
    avg_rating = float(df["rating"].mean()) if "rating" in df.columns else None
    pct_pos = float((df["sentiment"] == "positive").mean() * 100) if "sentiment" in df.columns else 0.0
    pct_neu = float((df["sentiment"] == "neutral").mean() * 100) if "sentiment" in df.columns else 0.0
    pct_neg = float((df["sentiment"] == "negative").mean() * 100) if "sentiment" in df.columns else 0.0
    top_products = df["product_id"].value_counts().head(10).to_dict() if "product_id" in df.columns else {}

    return jsonify({
        "total": total,
        "avg_rating": avg_rating,
        "pct_pos": pct_pos,
        "pct_neu": pct_neu,
        "pct_neg": pct_neg,
        "top_products": top_products
    })


# --- DB helper --------------------------------------------------------------
def _connect_db(db_path: str = None) -> sqlite3.Connection:
    """
    Conecta ao SQLite com row_factory sqlite3.Row.
    Usa db_path se fornecido, senão usa app.config['DB_PATH'].
    """
    if db_path is None:
        try:
            db_path = current_app.config.get('DB_PATH', 'data/db/reviews.db')
        except RuntimeError:
            # current_app não disponível -> usar padrão
            db_path = 'data/db/reviews.db'

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


# --- Reviews endpoint (paginação) ------------------------------------------
@app.route('/api/reviews')
def api_reviews():
    """
    GET /api/reviews?limit=50&offset=0
    Retorna JSON: { "total": <int>, "rows": [ {...}, ... ] }
    """
    # parse and validate query params
    try:
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
    except (TypeError, ValueError):
        return jsonify({"error": "limit and offset must be integers"}), 400

    # safety clamps
    if limit < 1:
        limit = 1
    if limit > 5000:
        limit = 5000
    if offset < 0:
        offset = 0

    db_path = request.args.get("db", app.config['DB_PATH'])
    if not os.path.exists(db_path):
        return jsonify({"error": "db_not_found", "path": db_path}), 404

    # total count
    total_q = "SELECT COUNT(*) AS cnt FROM reviews"
    select_q = """
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
        cur = conn.execute(total_q)
        total = int(cur.fetchone()["cnt"] or 0)

        cur = conn.execute(select_q, (limit, offset))
        rows = [dict(r) for r in cur.fetchall()]
    except Exception as e:
        app.logger.exception("Error querying reviews: %s", e)
        return jsonify({"error": "db_query_failed", "detail": str(e)}), 500
    finally:
        conn.close()

    return jsonify({"total": total, "rows": rows})


# --- Export endpoint -------------------------------------------------------
@app.route("/api/export")
def api_export():
    """
    Gera/atualiza CSV de export a partir do DB e retorna o caminho + rows gerados.
    Query params: db (opcional), out (opcional)
    """
    db = request.args.get("db", app.config['DB_PATH'])
    out = request.args.get("out", app.config['EXPORT_CSV'])

    # garante diretório de saída
    out_dir = os.path.dirname(out) or "."
    os.makedirs(out_dir, exist_ok=True)

    try:
        path, rows = export_for_dashboard(db_path=db, out_path=out)
        rel_path = os.path.relpath(path, start=os.getcwd())
        return jsonify({"path": rel_path, "rows": rows})
    except Exception as e:
        app.logger.exception("Export failed: %s", e)
        return jsonify({"error": str(e)}), 500


# --- Download CSV de export (procura em varios candidatos) ------------------
@app.route("/download/export")
def download_export():
    """
    Serve o arquivo CSV de export como attachment. Procura em múltiplos locais para facilitar debug.
    """
    cfg_path = os.getenv("AMZ_EXPORT_CSV", app.config['EXPORT_CSV'])

    candidates = []
    if os.path.isabs(cfg_path):
        candidates.append(cfg_path)
    else:
        # relativo à working dir atual (provavelmente repo root)
        candidates.append(os.path.abspath(cfg_path))
        # relativo ao app.root_path (onde Flask foi carregado)
        candidates.append(os.path.abspath(os.path.join(app.root_path, cfg_path)))
        # relativo ao diretório do módulo src (compatibilidade)
        candidates.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", cfg_path)))

    # dedup e keep order
    seen = set()
    candidates = [p for p in candidates if not (p in seen or seen.add(p))]

    found = None
    for p in candidates:
        if os.path.exists(p):
            found = p
            break

    if not found:
        return jsonify({
            "error": "file_not_found",
            "requested": cfg_path,
            "checked_paths": candidates
        }), 404

    return send_file(found, as_attachment=True, download_name=os.path.basename(found))


# --- Serve frontend --------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


# --- Run server (desenvolvimento) ------------------------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    debug = os.getenv("FLASK_DEBUG", "1") not in ["0", "false", "False"]
    app.run(host="0.0.0.0", port=port, debug=debug)
