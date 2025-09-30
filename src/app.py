# src/app.py
import os
import threading
import sqlite3
import re
from flask import current_app, request, jsonify, Blueprint
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


def _connect_db(db_path=None):
    """
    Conecta ao SQLite. Se db_path não for informado, tenta pegar current_app.config['DB_PATH']
    ou usa o padrão 'data/db/reviews.db'.
    Retorna conexão com row_factory = sqlite3.Row (permite dict-like rows).
    """
    if db_path is None:
        # tenta obter do config do Flask
        try:
            db_path = current_app.config.get('DB_PATH', 'data/db/reviews.db')
        except RuntimeError:
            # se current_app não estiver disponível (chamada fora do app context),
            # usar padrão relativo ao projeto.
            db_path = 'data/db/reviews.db'

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

# --- rota para listar reviews com limit/offset seguros ---
@app.route('/api/reviews')
def api_reviews():
    """
    GET /api/reviews?limit=50&offset=0
    - limit: quantas linhas retornar (int, padrão 50, máximo 5000)
    - offset: deslocamento (int, padrão 0)
    Retorna JSON array de objetos.
    """
    # valida params
    try:
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
    except (TypeError, ValueError):
        return jsonify({"error": "limit and offset must be integers"}), 400

    # clamps de segurança
    if limit < 1:
        limit = 1
    if limit > 5000:
        limit = 5000
    if offset < 0:
        offset = 0

    # pegar db_path de config do app quando disponível
    db_path = current_app.config.get('DB_PATH', 'data/db/reviews.db') if hasattr(current_app, 'config') else 'data/db/reviews.db'
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
    finally:
        conn.close()

    # Para compatibilidade com o frontend que aceita { total, rows } ou array,
    # retornamos um object com total + rows.
    return jsonify({"total": len(rows), "rows": rows})


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


# ---------------------------
# NEW: Products mapping API
# ---------------------------

def _choose_product_name_column(conn):
    """
    Verifica colunas da tabela 'reviews' e decide qual coluna usar como
    'product name'. Retorna nome da coluna preferida ou None.
    Preferências: 'name', 'product_name', 'product_title', 'title', 'reviews_title'
    """
    prefs = ['name', 'product_name', 'product_title', 'title', 'reviews_title']
    cols = [r[1] for r in conn.execute("PRAGMA table_info(reviews)").fetchall()]
    for p in prefs:
        if p in cols:
            return p
    # se não encontrou, tenta detectar colunas que contenham 'title' ou 'name'
    for c in cols:
        if 'title' in c or 'name' in c:
            return c
    return None

def simplify_product_name(name: str) -> str:
    """
    Heurística para reduzir o nome do produto:
    - remove conteúdo entre parênteses
    - corta em '-', ',' e toma a primeira parte
    - remove tokens que contenham dígitos (ex: '6', '16GB') ao montar resultado
    - limita a ~3 tokens relevantes
    Ex.: "Kindle E-reader 6\" Wifi (8th Generation, 2016)" -> "Kindle E-reader"
    """
    if not name:
        return ""
    s = str(name)
    # remove parenthesis content
    s = re.sub(r'\(.*?\)', '', s)
    # replace multiple whitespace
    s = re.sub(r'\s+', ' ', s).strip()
    # split on comma or hyphen, choose first segment
    seg = re.split(r'[,–\-]', s)[0].strip()
    # split into tokens and drop tokens that contain digits (or are short punctuation)
    tokens = [t for t in re.split(r'[\s/]+', seg) if t and not re.search(r'\d', t)]
    # if no tokens (e.g. everything numeric), fallback to first words from original seg
    if not tokens:
        tokens = [w for w in seg.split() if w]
    # limit tokens to first 3 (but also handle brand at start)
    out_tokens = []
    for t in tokens:
        # keep tokens like "Amazon" even if brand; but overall limit to 3
        out_tokens.append(t)
        if len(out_tokens) >= 3:
            break
    friendly = " ".join(out_tokens).strip()
    # final cleanup
    friendly = re.sub(r'["\']', '', friendly)
    return friendly


@app.route("/api/products")
def api_products():
    """
    Retorna um JSON mapping { product_id: friendly_name, ... }
    - tenta usar uma coluna de 'nome do produto' na tabela reviews (se existir)
    - caso não exista, tenta extrair a partir de CSV processado (data/processed/*)
    - sempre retorna strings amigáveis reduzidas
    """
    db = request.args.get("db", DB_PATH)
    if not os.path.exists(db):
        return jsonify({}), 404

    conn = _connect_db(db)
    try:
        col = _choose_product_name_column(conn)
        mapping = {}
        if col:
            # seleciona product_id + coluna escolhida (pega um valor representativo)
            q = f"SELECT product_id, {col} FROM reviews WHERE product_id IS NOT NULL"
            cur = conn.execute(q)
            for row in cur.fetchall():
                pid = row['product_id']
                raw = row[col] or ''
                # use simplified
                mapping[pid] = simplify_product_name(raw) or pid
        else:
            # fallback: pega distinct product_ids only
            cur = conn.execute("SELECT DISTINCT product_id FROM reviews")
            for row in cur.fetchall():
                pid = row['product_id']
                mapping[pid] = pid
    finally:
        conn.close()

    return jsonify(mapping)


# Serve frontend
@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    # Porta 8000 por compatibilidade com o que testamos antes
    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=True)
