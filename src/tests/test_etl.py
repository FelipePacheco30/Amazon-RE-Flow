# tests/test_etl.py
import pandas as pd
from src.etl import extract, transform

def test_extract_transform_small_sample(tmp_path):
    # cria um CSV minimal para teste
    csv = tmp_path / "sample.csv"
    df = pd.DataFrame({
        'reviews.text': ['good', 'bad', None],
        'reviews.rating': [5, 1, 3],
        'reviews.date': ['2020-01-01', '2020-02-01', '2020-03-01']
    })
    df.to_csv(csv, index=False)
    df_raw = extract(str(csv))
    df_clean = transform(df_raw)
    assert 'review_text' in df_clean.columns
    assert df_clean['review_text'].notna().all()
