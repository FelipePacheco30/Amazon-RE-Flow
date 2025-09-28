# src/main.py
import argparse
import logging
import os
from src.etl import extract, transform
from src.nlp import apply_nlp
from src.db import init_db, save_df
from src.export import export_for_dashboard

def run_pipeline(source: str,
                 out: str | None = None,
                 to_db: bool = False,
                 db_path: str = 'data/db/reviews.db',
                 nrows: int | None = None,
                 log_level: str = 'INFO') -> object:
    """
    Executa pipeline: extract -> transform -> nlp -> (save processed CSV) -> (save to db)
    Retorna o DataFrame processado.
    """
    # configurar logging
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(level=numeric_level, format='%(levelname)s: %(message)s')
    logger = logging.getLogger(__name__)
    logger.info("Running pipeline")

    # ETL
    logger.info("[extract] lendo CSV")
    df = extract(source, nrows=nrows)

    logger.info("[transform] aplicando transformações")
    df = transform(df)

    # NLP
    logger.info("Applying NLP (clean_text, sentiment, keywords)...")
    df = apply_nlp(df)

    # Salva CSV processado (opcional)
    if out:
        os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
        logger.info(f"[save_processed] salvando CSV em {out}")
        df.to_csv(out, index=False)
    else:
        logger.debug("Argumento --out não fornecido; pulando salvamento de CSV processado.")

    # Salva DB (opcional)
    if to_db:
        logger.info(f"Initializing DB and saving to SQLite: {db_path}")
        engine = init_db(db_path)
        # save_df signature: save_df(engine, df, table_name='reviews')
        save_df(engine, df, table_name='reviews')
        logger.info(f"Saved {len(df)} rows to DB")

    logger.info("Pipeline finished. Processed rows: %d", len(df))
    return df

def main():
    parser = argparse.ArgumentParser(description="Run ETL + NLP pipeline")
    parser.add_argument('--source', required=True, help='Path to input CSV')
    parser.add_argument('--out', required=False, help='Path to output CSV (optional)')
    parser.add_argument('--to-db', action='store_true', help='Save results to SQLite')
    parser.add_argument('--db', dest='db_path', default='data/db/reviews.db', help='SQLite DB path')
    parser.add_argument('--nrows', type=int, default=None, help='Number of rows to process (for testing)')
    parser.add_argument('--log-level', default='INFO', help='Logging level (DEBUG, INFO, WARNING, ERROR)')
    parser.add_argument('--export', action='store_true', help='After saving to DB, export CSV for dashboard (reads DB)')

    args = parser.parse_args()

    # run pipeline
    df = run_pipeline(source=args.source,
                      out=args.out,
                      to_db=args.to_db,
                      db_path=args.db_path,
                      nrows=args.nrows,
                      log_level=args.log_level)

    # export (opcional) -> lê do DB e gera CSV pronto
    if args.export:
        if not args.to_db:
            logging.warning("--export solicitado mas --to-db não foi passado; export irá tentar ler DB existente.")
        try:
            csv_path, rows = export_for_dashboard(db_path=args.db_path)
            logging.info(f"Exported {rows} rows to {csv_path}")
        except Exception as e:
            logging.error("Falha ao exportar para dashboard: %s", e)

if __name__ == '__main__':
    main()
