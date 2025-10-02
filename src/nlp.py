# src/nlp.py
import re
import warnings
from collections import Counter
from typing import List

import pandas as pd

# Try to import NLTK pieces but be robust if resources are missing in container
try:
    import nltk
    from nltk.tokenize import word_tokenize
    from nltk.corpus import stopwords
    from nltk.sentiment import SentimentIntensityAnalyzer

    _NLTK_AVAILABLE = True
except Exception:
    # NLTK not installed or import failed
    nltk = None
    word_tokenize = None
    stopwords = None
    SentimentIntensityAnalyzer = None
    _NLTK_AVAILABLE = False

# Try to initialize resources (but do NOT call nltk.download at import-time)
_SIA = None
if SentimentIntensityAnalyzer is not None:
    try:
        _SIA = SentimentIntensityAnalyzer()
    except Exception as e:
        warnings.warn("VADER available but failed to initialize: %s" % e)
        _SIA = None
else:
    _SIA = None

# Stopwords fallback (simple english set) if NLTK stopwords not available
try:
    if stopwords is not None:
        STOPWORDS = set(w.lower() for w in stopwords.words("english"))
    else:
        raise RuntimeError("nltk.corpus.stopwords not available")
except Exception:
    # minimal fallback list (keeps common English stopwords)
    STOPWORDS = {
        "the", "and", "is", "in", "it", "of", "to", "a", "i", "this", "that",
        "was", "for", "with", "as", "on", "but", "are", "they", "be", "have",
        "not", "you", "he", "she", "we", "my", "so", "if", "or", "at", "by",
        "an", "from", "its", "me", "do", "did", "has"
    }

# Patterns used to detect neutral short phrases
_NEUTRAL_PHRASE_PATTERNS = [
    r"^\s*(it is okay|it's okay|it is ok|it's ok)\.?\s*$",
    r"^\s*(okay|ok|fine)\.?\s*$",
]
_NEUTRAL_PHRASE_RE = re.compile("|".join(_NEUTRAL_PHRASE_PATTERNS), flags=re.IGNORECASE)

# Small positive / negative token lists for fallback sentiment if VADER missing
_POSITIVE_WORDS = {
    "good", "great", "excellent", "love", "loved", "nice", "awesome", "amazing",
    "happy", "best", "perfect", "recommend", "recommended", "easy", "works",
}
_NEGATIVE_WORDS = {
    "bad", "poor", "disappoint", "disappointed", "terrible", "hate", "hated",
    "awful", "worst", "problem", "issue", "doesn't", "doesnt", "broke", "broken",
}

_token_pattern = re.compile(r"[a-zA-Z]+")  # fallback tokenizer


def clean_text(text: str) -> str:
    """Remove HTML, non-letters and collapse whitespace; return lowercase."""
    if not text:
        return ""
    # strip html-like tags
    s = re.sub(r"<.*?>", " ", str(text))
    # keep letters and spaces
    s = re.sub(r"[^a-zA-Z\s]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip().lower()


def tokenize_and_remove_stopwords(text: str) -> List[str]:
    """Tokenize text and remove stopwords. Uses nltk.word_tokenize when available,
    otherwise a simple regex-based tokenizer."""
    if not text:
        return []
    txt = str(text)
    tokens = []
    if word_tokenize is not None:
        try:
            # NLTK tokenizer may raise if punkt not present; catch and fallback
            toks = word_tokenize(txt)
            tokens = [t.lower() for t in toks if t.isalpha()]
        except Exception:
            tokens = _token_pattern.findall(txt.lower())
    else:
        tokens = _token_pattern.findall(txt.lower())

    # remove stopwords
    tokens = [t for t in tokens if t and t not in STOPWORDS]
    return tokens


def sentiment_vader(text: str) -> str:
    """
    Return 'positive' | 'negative' | 'neutral'.
    Prefer VADER when available. If not, use a simple lexicon/count heuristic.
    """
    if not text or not str(text).strip():
        return "neutral"

    text_str = str(text).strip()

    # explicit neutral short phrases
    if _NEUTRAL_PHRASE_RE.match(text_str):
        return "neutral"

    # Try VADER if initialized
    if _SIA is not None:
        try:
            scores = _SIA.polarity_scores(text_str)
            compound = scores.get("compound", 0.0)
            if compound >= 0.05:
                # small heuristic: if contains moderating tokens and compound small -> neutral
                lower = text_str.lower()
                moderate_tokens = {"okay", "ok", "fine", "alright"}
                if any(re.search(rf"\b{re.escape(t)}\b", lower) for t in moderate_tokens) and compound < 0.2:
                    return "neutral"
                return "positive"
            if compound <= -0.05:
                return "negative"
            return "neutral"
        except Exception:
            # fallback to lexicon method below
            pass

    # Fallback simple heuristic: count positive vs negative tokens
    tokens = tokenize_and_remove_stopwords(clean_text(text_str))
    if not tokens:
        return "neutral"

    pos = sum(1 for t in tokens if t in _POSITIVE_WORDS)
    neg = sum(1 for t in tokens if t in _NEGATIVE_WORDS)

    # If counts are equal and low, call neutral
    if pos == neg:
        # small bias using presence of strong words
        if pos + neg == 0:
            return "neutral"
        # if both present but pos significantly greater -> positive
    if pos > neg and pos - neg >= 1:
        return "positive"
    if neg > pos and neg - pos >= 1:
        return "negative"
    return "neutral"


def top_keywords(text: str, n: int = 5) -> str:
    """Return the top-n keywords from text as a comma-separated string."""
    cleaned = clean_text(text)
    tokens = tokenize_and_remove_stopwords(cleaned)
    if not tokens:
        return ""
    counts = Counter(tokens)
    most_common = [word for word, _ in counts.most_common(n)]
    return ",".join(most_common)


def apply_nlp(df: pd.DataFrame, text_column: str = "review_text") -> pd.DataFrame:
    """Apply NLP transformations to a DataFrame: clean_text, sentiment, keywords."""
    df = df.copy()
    if text_column not in df.columns:
        df[text_column] = ""

    # ensure we operate on strings for robustness
    df["clean_text"] = df[text_column].astype(str).apply(clean_text)
    df["sentiment"] = df[text_column].astype(str).apply(sentiment_vader)
    df["keywords"] = df[text_column].astype(str).apply(lambda t: top_keywords(t, n=5))
    return df


# If module imported as script, don't attempt downloads; just print status
if __name__ == "__main__":
    print("NLTK available:", _NLTK_AVAILABLE)
    print("VADER initialized:", _SIA is not None)
    print("Sample stopwords count:", len(STOPWORDS))
