# scripts/check_dbs.py
import os
import sqlite3

root = os.path.abspath(".")
candidates = []

# procura arquivos reviews.db em todo o repo
for dirpath, dirs, files in os.walk(root):
    for f in files:
        if f.lower() == "reviews.db":
            candidates.append(os.path.join(dirpath, f))

if not candidates:
    print("Nenhum arquivo reviews.db encontrado sob", root)
else:
    print("Arquivos encontrados:", len(candidates))
    for p in sorted(candidates):
        try:
            conn = sqlite3.connect(p)
            cur = conn.execute("SELECT COUNT(*) FROM reviews")
            cnt = cur.fetchone()[0]
            conn.close()
        except Exception as e:
            cnt = f"erro: {e}"
        print(f"{p} -> {cnt} rows")
