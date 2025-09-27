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

def export_for_dashboard(db_path='data/db/reviews.db', out_path='data/export/reviews_for_dashboard.csv'):
    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        query = """
        SELECT
          review_id,
          product_id,
          review_date,
          rating,
          sentiment,
          keywords,
          review_len,
          review_word_count,
          reviews_username,
          reviews_title,
          brand,
          categories
        FROM reviews
        """
        df = pd.read_sql_query(query, conn)
    finally:
        conn.close()

    # formatar data para ISO (Google Sheets)
    if 'review_date' in df.columns:
        df['review_date'] = pd.to_datetime(df['review_date'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')

    df.to_csv(out_path, index=False)
    return out_path, len(df)
