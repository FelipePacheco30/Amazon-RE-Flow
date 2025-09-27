# src/main.py
import argparse
from src.etl import extract, transform, save_processed
# tentar importar nlp (se existir)
try:
    from src.nlp import clean_text, get_sentiment, top_keywords
    NLP_AVAILABLE = True
except Exception:
    NLP_AVAILABLE = False

from src.db import init_db, save_df

def run_pipeline(source, out, to_db=False, nrows=None):
    print("Running pipeline:")
    df_raw = extract(source, nrows=nrows)
    df = transform(df_raw)

    if NLP_AVAILABLE and 'review_text' in df.columns:
        print("Applying NLP (clean_text, sentiment, keywords)...")
        df['clean_text'] = df['review_text'].apply(clean_text)
        df['sentiment'] = df['clean_text'].apply(get_sentiment)
        df['keywords'] = df['clean_text'].apply(lambda x: top_keywords(x, n=5))
    else:
        print("NLP not available or review_text missing; skipping NLP step.")

    save_processed(df, out)

    if to_db:
        print("Initializing DB and saving to SQLite...")
        init_db()
        rows = save_df(df)
        print(f"Saved {rows} rows to DB.")
    print("Pipeline finished. Processed rows:", len(df))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run full pipeline: ETL (+ NLP) + optional DB save")
    parser.add_argument("--source", required=True, help="path to raw csv (ex: data/raw/reviews.csv)")
    parser.add_argument("--out", default="data/processed/reviews_clean.csv", help="output processed csv")
    parser.add_argument("--to-db", action="store_true", help="save results to SQLite DB")
    parser.add_argument("--nrows", type=int, default=None, help="number of rows to read (dev)")
    args = parser.parse_args()
    run_pipeline(args.source, args.out, to_db=args.to_db, nrows=args.nrows)
