import argparse
import logging
from src.etl import extract, transform
from src.nlp import apply_nlp
from src.db import init_db, save_df
from src.export import export_for_dashboard

def run_pipeline(source, out, to_db=False, db_path='data/db/reviews.db', nrows=None, log_level='INFO'):
    # Configura logging
    logging.basicConfig(level=getattr(logging, log_level.upper()), format='%(levelname)s: %(message)s')
    logging.info("Running pipeline")

    # ETL
    logging.info("[extract] lendo CSV")
    df = extract(source, nrows=nrows)
    
    logging.info("[transform] aplicando transformações")
    df = transform(df)

    # NLP
    logging.info("Applying NLP (clean_text, sentiment, keywords)...")
    df = apply_nlp(df)

    # Salva CSV processado
    logging.info(f"[save_processed] salvando CSV em {out}")
    df.to_csv(out, index=False)

    # Salva DB
    if to_db:
        logging.info(f"Initializing DB and saving to SQLite: {db_path}")
        engine = init_db(db_path)
        save_df(engine, df, table_name='reviews')
        logging.info(f"Saved {len(df)} rows to DB")

    logging.info("Pipeline finished. Processed rows: %d", len(df))
    return df

def main():
    parser = argparse.ArgumentParser(description="Run ETL + NLP pipeline")
    parser.add_argument('--source', required=True, help="Path to input CSV")
    parser.add_argument('--out', required=True, help="Path to output CSV")
    parser.add_argument('--to-db', action='store_true', help="Save results to SQLite")
    parser.add_argument('--db', default='data/db/reviews.db', help="SQLite DB path")
    parser.add_argument('--nrows', type=int, help="Number of rows to process (for testing)")
    parser.add_argument('--log-level', default='INFO', help="Logging level (DEBUG, INFO, WARNING, ERROR)")

    args = parser.parse_args()
    run_pipeline(args.source, args.out, to_db=args.to_db, db_path=args.db, nrows=args.nrows, log_level=args.log_level)

if __name__ == '__main__':
    main()
