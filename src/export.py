# src/export.py
"""
Export utilities: consulta o DB e gera CSV pronto para Google Sheets / Looker Studio.
Uso:
    from src.export import export_for_dashboard
    export_for_dashboard('data/db/reviews.db', 'data/export/reviews_for_dashboard.csv')
"""

import os
import sqlite3
import pandas as pd
from typing import Tuple

def export_for_dashboard(db_path: str = 'data/db/reviews.db',
                         out_path: str = 'data/export/reviews_for_dashboard.csv') -> Tuple[str, int]:
    """
    Exporta dados da tabela 'reviews' do SQLite para CSV pronto para Google Sheets / Looker Studio.

    - Faz verificação de existência da tabela.
    - Seleciona colunas relevantes apenas se existirem (evita KeyError).
    - Formata review_date como string ISO.

    Retorna (out_path, number_of_rows).
    """
    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)

    # Conecta ao sqlite
    conn = sqlite3.connect(db_path)
    try:
        # Checa se tabela existe
        tbls = pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table' AND name='reviews';", conn)
        if tbls.empty:
            raise RuntimeError(f"Tabela 'reviews' não encontrada no DB: {db_path}")

        # Ler tudo da tabela reviews
        df = pd.read_sql_query("SELECT * FROM reviews", conn)
    finally:
        conn.close()

    # Colunas preferenciais para export (ordem desejada)
    preferred = [
        "review_id", "product_id", "review_date", "rating", "sentiment", "keywords",
        "review_len", "review_word_count", "reviews_username", "reviews_title",
        "brand", "categories"
    ]

    # Seleciona apenas colunas que realmente existem no DataFrame, preservando a ordem preferida
    cols = [c for c in preferred if c in df.columns]
    # Se nenhuma coluna preferida existir (caso raro), exporta todas
    if not cols:
        cols = df.columns.tolist()

    df_export = df[cols].copy()

    # Formatar data para ISO (Google Sheets lê bem)
    if "review_date" in df_export.columns:
        df_export["review_date"] = pd.to_datetime(df_export["review_date"], errors="coerce").dt.strftime('%Y-%m-%d %H:%M:%S')

    # Salvar CSV final
    df_export.to_csv(out_path, index=False)
    return out_path, len(df_export)
