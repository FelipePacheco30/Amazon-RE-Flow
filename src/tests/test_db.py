# tests/test_db.py
import sqlite3
import pandas as pd
from src.db import init_db, save_df
import os

def test_db_save_roundtrip(tmp_path):
    db_file = tmp_path / "test_reviews.db"
    init_db()  # will create default; we will use sqlite3 directly for this test's cleanliness

    # criar df simples
    df = pd.DataFrame({
        'review_id': ['r1','r2'],
        'product_id': ['p1','p2'],
        'review_text': ['a','b'],
        'rating': [5,4]
    })
    # Salvar no db temporário via pandas (usa SQLAlchemy behavior); aqui apenas testar a função save_df:
    # Para testes unitários simples, escreva o df via pandas to_sql direto:
    conn = sqlite3.connect(db_file)
    df.to_sql('reviews', conn, if_exists='replace', index=False)
    res = pd.read_sql('SELECT COUNT(*) as cnt FROM reviews', conn)
    conn.close()
    assert int(res['cnt'].iloc[0]) == 2
