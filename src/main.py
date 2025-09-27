# (resumo do main: preserve o resto do arquivo se já existir)
# Salve este arquivo como src/main.py (substituir conteúdo anterior)
import argparse
import os
from src.etl import extract, transform, save_processed

try:
    from src.nlp import clean_text, get_sentiment, top_keywords
    NLP_AVAILABLE = True
except Exception:
    NLP_AVAILABLE = False

def run_pipeline(source, out, db_path=None, to_db=False, nrows=None):
    if db_path:
        os.environ['DATABASE_URL'] = f"sqlite:///{os.path.abspath(db_path)}"
    if to_db:
        from src.db import init_db, save_df

    df_raw = extract(source, nrows=nrows)
    df = transform(df_raw)

    if NLP_AVAILABLE and 'review_text' in df.columns:
        df['clean_text'] = df['review_text'].apply(clean_text)
        df['sentiment'] = df['clean_text'].apply(get_sentiment)
        df['keywords'] = df['clean_text'].apply(lambda x: top_keywords(x, n=5))

    save_processed(df, out)

    if to_db:
        init_db()
        rows = save_df(df)
        print(f"Saved {rows} rows to DB.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True)
    parser.add_argument('--out', default='data/processed/reviews_clean.csv')
    parser.add_argument('--to-db', action='store_true')
    parser.add_argument('--db', default=None, help='path to sqlite db file')
    parser.add_argument('--nrows', type=int, default=None)
    args = parser.parse_args()
    run_pipeline(args.source, args.out, db_path=args.db, to_db=args.to_db, nrows=args.nrows)
