# src/etl.py
import ast
import pandas as pd
import os

# ---------- Helpers ----------
def extract_first_asin(val):
    """Tenta extrair um ASIN único a partir de formatos comuns."""
    if pd.isna(val):
        return None
    s = str(val).strip()
    try:
        parsed = ast.literal_eval(s)
        if isinstance(parsed, (list, tuple)) and parsed:
            return str(parsed[0]).strip()
    except Exception:
        pass
    for sep in [',','|',';',' ']:
        if sep in s:
            cand = s.split(sep)[0]
            return cand.strip(" []'\"")
    return s.strip(" []'\"")

def normalize_colnames(cols):
    """Normaliza lista de colunas para snake_case simples."""
    out = []
    for c in cols:
        if c is None:
            out.append(c)
            continue
        n = str(c).strip().lower().replace(' ', '_').replace('.', '_').replace('-', '_')
        out.append(n)
    return out

# ---------- ETL functions ----------
def extract(path, usecols=None, nrows=None):
    """
    Lê CSV e retorna um DataFrame.
    - path: caminho para o CSV (relativo ao root do projeto).
    - usecols: lista de colunas a ler (opcional).
    - nrows: int (opcional) para desenvolvimento rápido.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")
    df = pd.read_csv(path, low_memory=False, usecols=usecols, nrows=nrows)
    # Normaliza nomes das colunas imediatamente
    df.columns = normalize_colnames(df.columns)
    print(f"[extract] lido {len(df)} linhas e {len(df.columns)} colunas de {path}")
    return df

def transform(df):
    """
    Recebe DataFrame cru (com col names normalizados) e devolve DataFrame limpo.
    - normaliza nomes padrão
    - mapeia colunas relevantes
    - extrai product_id (ASIN), converte rating, datas, cria features simples,
      remove reviews sem texto e duplicatas.
    """
    df = df.copy()

    # 1) Mapeamento de colunas para o schema que usaremos
    mapping_candidates = {
        'reviews_id': 'review_id',
        'review_id': 'review_id',
        'id': 'review_id',
        'asins': 'product_id',
        'product_id': 'product_id',
        'reviews_text': 'review_text',
        'review_text': 'review_text',
        'reviews_rating': 'rating',
        'rating': 'rating',
        'reviews_date': 'review_date',
        'review_date': 'review_date',
        'reviews_dateadded': 'review_date',
        'reviews_title': 'reviews_title',
        'reviews_username': 'reviews_username',
        'reviews_numhelpful': 'reviews_numhelpful',
        'reviews_dorecommend': 'reviews_dorecommend',
        'brand': 'brand',
        'name': 'name',
        'categories': 'categories',
        'primarycategories': 'primarycategories'
    }
    # constrói mapping só com chaves existentes
    mapping = {k: v for k, v in mapping_candidates.items() if k in df.columns}
    if mapping:
        df = df.rename(columns=mapping)

    # 2) Resolver possíveis colunas duplicadas por coalescing:
    # (se houver 'review_id' duplicada etc., pega o primeiro não-nulo)
    # já deve ter sido tratado, mas deixamos um passo seguro:
    cols = df.columns.tolist()
    dup_names = [name for name in set(cols) if cols.count(name) > 1]
    for dup in dup_names:
        df_dup = df.loc[:, [c for c in df.columns if c == dup]]
        combined = df_dup.bfill(axis=1).iloc[:, 0]
        # drop original (todas ocorrências) e re-inserir a combinada
        df = df.loc[:, ~pd.Index(df.columns).isin([dup])]
        df[dup] = combined

    # 3) Aplicar transformações nos campos importantes
    # product_id (ASIN)
    if 'product_id' in df.columns:
        df['product_id'] = df['product_id'].apply(extract_first_asin)

    # review_text: garantir string
    if 'review_text' in df.columns:
        df['review_text'] = df['review_text'].astype(str)

    # rating -> numérico
    if 'rating' in df.columns:
        df['rating'] = pd.to_numeric(df['rating'], errors='coerce')

    # review_date -> datetime (UTC)
    if 'review_date' in df.columns:
        df['review_date'] = pd.to_datetime(df['review_date'], errors='coerce', utc=True)

    # features simples do texto
    if 'review_text' in df.columns:
        df['review_len'] = df['review_text'].str.len()
        df['review_word_count'] = df['review_text'].str.split().str.len()

    # remover reviews sem texto útil
    if 'review_text' in df.columns:
        mask_valid_text = df['review_text'].notna() & (df['review_text'].str.strip() != '') & (df['review_text'].str.lower() != 'nan')
        df = df[mask_valid_text].copy()

    # remover duplicatas por review_id se existir, senão global
    if 'review_id' in df.columns:
        df = df.drop_duplicates(subset=['review_id'], keep='first')
    else:
        df = df.drop_duplicates()

    # reset index
    df = df.reset_index(drop=True)

    print(f"[transform] saída com {len(df)} linhas e {len(df.columns)} colunas")
    return df

def save_processed(df, out_path='../data/processed/reviews_clean.csv'):
    """Salva DataFrame processado para CSV (cria pasta se necessário)."""
    out_dir = os.path.dirname(out_path)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"[save_processed] salvo {len(df)} linhas em {out_path}")
    return out_path

# Optional: quick CLI to run only ETL (useful while main.py still integra NLP/DB)
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="ETL: extract, transform and save processed CSV")
    parser.add_argument("--source", required=True, help="caminho para CSV raw, ex: data/raw/reviews.csv")
    parser.add_argument("--out", default="data/processed/reviews_clean.csv", help="output processed csv")
    parser.add_argument("--nrows", type=int, default=None, help="usar apenas nrows (dev)")
    args = parser.parse_args()
    df_raw = extract(args.source, nrows=args.nrows)
    df_clean = transform(df_raw)
    save_processed(df_clean, args.out)
