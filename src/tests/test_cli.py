import os
import pytest
from src.main import run_pipeline

TEST_CSV_IN = "data/raw/reviews_sample.csv"
TEST_CSV_OUT = "data/processed/reviews_test_output.csv"
TEST_DB = "data/db/reviews_test.db"

def test_run_pipeline_csv_only():
    # Testa pipeline sem salvar DB
    if os.path.exists(TEST_CSV_OUT):
        os.remove(TEST_CSV_OUT)

    df = run_pipeline(TEST_CSV_IN, TEST_CSV_OUT, to_db=False, nrows=5, log_level='DEBUG')
    assert os.path.exists(TEST_CSV_OUT)
    assert len(df) == 5

def test_run_pipeline_with_db():
    # Testa pipeline salvando DB
    if os.path.exists(TEST_CSV_OUT):
        os.remove(TEST_CSV_OUT)
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

    df = run_pipeline(TEST_CSV_IN, TEST_CSV_OUT, to_db=True, db_path=TEST_DB, nrows=5, log_level='DEBUG')
    assert os.path.exists(TEST_CSV_OUT)
    assert os.path.exists(TEST_DB)
    assert len(df) == 5
