"""
Robust NLP utilities for the pipeline.

This module avoids forcing nltk.download() at import time (which can fail
in container/cloud environments) and provides safe fallbacks if NLTK data
is not available.

Exports:
- clean_text(text)
- tokenize_and_remove_stopwords(text)
- sentiment_vader(text)  -> returns 'positive'|'negative'|'neutral'
- top_keywords(text, n=5)
- apply_nlp(df, text_column='review_text')
"""
from __future__ import annotations

import re
import warnings
from collections import Counter
from typing import List

import pandas as pd

# Try importing nltk components; if unavailable, fall back to lightweight alternatives
try:
    import nltk  # type: ignore
    from nltk.tokenize import word_tokenize  # type: ignore
    from nltk.corpus import stopwords  # type: ignore
    from nltk.sentiment import SentimentIntensityAnalyzer  # type: ignore

    _NLTK_AVAILABLE = True
except Exception:
    _NLTK_AVAILABLE = False
    # Provide placeholders to keep type checkers happy
    word_tokenize = None  # type: ignore
    stopwords = None  # type: ignore
    SentimentIntensityAnalyzer = None  # type: ignore

# Prepare stopwords set (safe fallback)
if _NLTK_AVAILABLE:
    try:
        _stopset = set(w.lower() for w in stopwords.words("english"))
    except Exception:
        # If stopwords not present, don't attempt to download automatically.
        # Use a small built-in fallback list.
        warnings.warn("NLTK stopwords not available — using small built-in stoplist")
        _stopset = {
            "the",
            "and",
            "is",
            "in",
            "it",
            "of",
            "to",
            "a",
            "i",
            "this",
            "that",
            "for",
            "on",
            "with",
        }
else:
    _stopset = {
        "the",
        "and",
        "is",
        "in",
        "it",
        "of",
        "to",
        "a",
        "i",
        "this",
        "that",
        "for",
        "on",
        "with",
    }

STOPWORDS = set(w.lower() for w in _stopset)

# Initialize sentiment analyzer if available. Do NOT call nltk.download() here
# to avoid concurrency / permission issues in cloud environments.
_sia = None
if _NLTK_AVAILABLE and SentimentIntensityAnalyzer is not None:
    try:
        _sia = SentimentIntensityAnalyzer()
    except Exception as e:
        warnings.warn(f"VADER unavailable; falling back to simple sentiment: {e}")
        _sia = None

# Simple fallback lexicons (used when VADER unavailable)
_POSITIVE_LEX = {
    "good",
    "great",
    "love",
    "excellent",
    "awesome",
    "perfect",
    "best",
    "nice",
    "happy",
    "recommended",
    "recommend",
    "amazing",
}
_NEGATIVE_LEX = {
    "bad",
    "terrible",
    "awful",
    "poor",
    "disappointed",
    "hate",
    "problem",
    "broken",
    "worse",
    "worst",
    "disappointing",
}

# Recognize short explicit neutral phrases
_NEUTRAL_PHRASE_PATTERNS = [
    r"^\s*(it is okay|it's okay|it is ok|it's ok)\.?\s*$",
    r"^\s*(okay|ok|fine)\.?\s*$",
]
_NEUTRAL_PHRA_RE = re.compile("|".join(_NEUTRAL_PHRASE_PATTERNS), flags=re.IGNORECASE)


def clean_text(text: str) -> str:
    """
    Remove HTML-like tags, non-letter characters, collapse whitespace and lowercase.
    """
    if not text:
        return ""
    s = str(text)
    s = re.sub(r"<.*?>", " ", s)  # strip simple HTML tags
    s = re.sub(r"[^A-Za-z\s]", " ", s)  # keep letters and spaces
    s = re.sub(r"\s+", " ", s).strip()
    return s.lower()


def _simple_tokenize(text: str) -> List[str]:
    """Lightweight tokenizer used as fallback."""
    if not text:
        return []
    return re.findall(r"[A-Za-z]+", text)


def tokenize_and_remove_stopwords(text: str) -> List[str]:
    """
    Tokenize text and remove stopwords. Prefer NLTK tokenizer if available,
    otherwise fallback to a regex-based tokenizer.
    """
    if not text:
        return []
    if _NLTK_AVAILABLE and word_tokenize is not None:
        try:
            toks = word_tokenize(text)
            toks = [t.lower() for t in toks if t.isalpha()]
        except Exception:
            toks = _simple_tokenize(text)
    else:
        toks = _simple_tokenize(text)

    toks = [t for t in toks if t not in STOPWORDS]
    return toks


def sentiment_vader(text: str) -> str:
    """
    Return 'positive', 'negative' or 'neutral'.
    - If VADER is available, use its compound score with thresholds:
        compound >= 0.05  -> positive
        compound <= -0.05 -> negative
        otherwise -> neutral
      plus a small heuristic to treat mild positives containing 'ok/okay/fine' as neutral.
    - If VADER is not available, use a very simple lexicon count fallback.
    """
    if not text or not str(text).strip():
        return "neutral"

    text_str = str(text).strip()

    # explicit neutral short-phrases
    if _NEUTRAL_PHRA_RE.match(text_str):
        return "neutral"

    # use VADER if initialized
    if _sia is not None:
        try:
            scores = _sia.polarity_scores(text_str)
            compound = float(scores.get("compound", 0.0))
        except Exception:
            compound = 0.0

        # neutral window
        if -0.05 <= compound <= 0.05:
            return "neutral"

        if compound > 0.05:
            lower = text_str.lower()
            moderate_tokens = ["okay", "ok", "fine", "alright"]
            contains_moderate = any(re.search(rf"\b{re.escape(t)}\b", lower) for t in moderate_tokens)
            if contains_moderate and compound < 0.20:
                return "neutral"
            return "positive"

        if compound < -0.05:
            return "negative"

        return "neutral"

    # fallback simple lexicon approach
    txt = text_str.lower()
    pos_count = sum(1 for w in _POSITIVE_LEX if re.search(rf"\b{re.escape(w)}\b", txt))
    neg_count = sum(1 for w in _NEGATIVE_LEX if re.search(rf"\b{re.escape(w)}\b", txt))

    if pos_count == neg_count:
        return "neutral"
    return "positive" if pos_count > neg_count else "negative"


def top_keywords(text: str, n: int = 5) -> str:
    """
    Return the top-n keywords as a comma-separated string.
    Uses tokenize_and_remove_stopwords + simple frequency count.
    """
    if not text:
        return ""
    cleaned = clean_text(text)
    toks = tokenize_and_remove_stopwords(cleaned)
    if not toks:
        return ""
    counts = Counter(toks)
    most = [w for w, _ in counts.most_common(n)]
    return ",".join(most)


def apply_nlp(df: pd.DataFrame, text_column: str = "review_text") -> pd.DataFrame:
    """
    Apply NLP transforms to a pandas DataFrame:
      - adds 'clean_text'
      - adds 'sentiment' (positive/neutral/negative)
      - adds 'keywords' (comma-separated top tokens)
    Returns a copy of the dataframe with the new columns.
    """
    df = df.copy()
    if text_column not in df.columns:
        df[text_column] = ""

    # ensure we operate on strings
    src = df[text_column].fillna("").astype(str)

    df["clean_text"] = src.map(clean_text)
    df["sentiment"] = src.map(sentiment_vader)
    df["keywords"] = src.map(lambda t: top_keywords(t, n=5))
    return df
