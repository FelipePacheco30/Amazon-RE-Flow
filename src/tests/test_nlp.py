# src/tests/test_nlp.py
import pytest
import pandas as pd
from src.nlp import clean_text, tokenize_and_remove_stopwords, sentiment_vader, top_keywords, apply_nlp

def test_clean_text():
    text = "<p>Hello World! 123</p>"
    cleaned = clean_text(text)
    assert cleaned == "hello world"

def test_tokenize_and_remove_stopwords():
    text = "This is a simple test sentence."
    tokens = tokenize_and_remove_stopwords(text)
    # "this", "is", "a" são stopwords
    assert "simple" in tokens
    assert "test" in tokens
    assert "sentence" in tokens
    assert "this" not in tokens

def test_sentiment_vader():
    assert sentiment_vader("I love this product!") == "positive"
    assert sentiment_vader("This is terrible.") == "negative"
    assert sentiment_vader("It is okay.") == "neutral"
    assert sentiment_vader("") == "neutral"

def test_top_keywords():
    text = "apple banana apple orange banana apple"
    keywords = top_keywords(text, n=2)
    # as duas palavras mais frequentes devem ser "apple" e "banana"
    assert keywords == "apple,banana"

def test_apply_nlp():
    df = pd.DataFrame({
        "review_text": [
            "I love this product!",
            "This is terrible.",
            "<p>Neutral review.</p>"
        ]
    })
    df_nlp = apply_nlp(df)
    assert "clean_text" in df_nlp.columns
    assert "sentiment" in df_nlp.columns
    assert "keywords" in df_nlp.columns
    assert df_nlp.loc[0, "sentiment"] == "positive"
    assert df_nlp.loc[1, "sentiment"] == "negative"
    assert df_nlp.loc[2, "sentiment"] == "neutral"
