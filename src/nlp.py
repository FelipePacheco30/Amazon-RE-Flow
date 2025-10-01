import re
import pandas as pd
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.sentiment import SentimentIntensityAnalyzer
from collections import Counter

import nltk
nltk.download("punkt", quiet=True)
nltk.download("stopwords", quiet=True)
nltk.download("vader_lexicon", quiet=True)

STOPWORDS = set(w.lower() for w in stopwords.words("english"))
sia = SentimentIntensityAnalyzer()

_NEUTRAL_PHRASE_PATTERNS = [
    r'^\s*(it is okay|it\'s okay|it is ok|it\'s ok)\.?\s*$',
    r'^\s*(okay|ok|fine)\.?\s*$'
]
_NEUTRAL_PHRASE_RE = re.compile("|".join(_NEUTRAL_PHRASE_PATTERNS), flags=re.IGNORECASE)

def clean_text(text: str) -> str:
    """Limpa HTML, remove números e pontuação, converte para lowercase."""
    if not text:
        return ""
    text = re.sub(r"<.*?>", " ", text)         
    text = re.sub(r"[^a-zA-Z\s]", " ", text)     
    text = re.sub(r"\s+", " ", text)             
    return text.strip().lower()

def tokenize_and_remove_stopwords(text: str) -> list:
    """Tokeniza e remove stopwords; retorna lista de tokens em minúsculas."""
    if not text:
        return []
    tokens = word_tokenize(text)
    tokens = [t.lower() for t in tokens if t.isalpha()] 
    tokens = [t for t in tokens if t not in STOPWORDS]
    return tokens

def sentiment_vader(text: str) -> str:
    """
    Classifica sentimento como 'positive', 'negative' ou 'neutral'.

    Lógica:
    - Primeiro, detecta frases curtas/moderadas explicitamente (ex.: "It is okay.") e retorna 'neutral'.
    - Caso contrário, usa VADER compound score com limiares:
        compound >= 0.05  -> positive
        compound <= -0.05 -> negative
        entre -0.05 e 0.05 -> neutral
    - Heurística adicional (opcional): se contém tokens moderados e score fraco, pode retornar neutral.
    """
    if not text or not str(text).strip():
        return "neutral"

    text_str = str(text).strip()

    if _NEUTRAL_PHRASE_RE.match(text_str):
        return "neutral"

    scores = sia.polarity_scores(text_str)
    compound = scores.get("compound", 0.0)

    if -0.05 <= compound <= 0.05:
        return "neutral"

    lower = text_str.lower()
    moderate_tokens = ["okay", "ok", "fine", "alright"]
    contains_moderate = any(re.search(rf"\b{re.escape(t)}\b", lower) for t in moderate_tokens)

    if compound > 0.05:
        if contains_moderate and compound < 0.20:
            return "neutral"
        return "positive"

    if compound < -0.05:
        return "negative"

    return "neutral"

def top_keywords(text: str, n: int = 5) -> str:
    """Retorna as n palavras mais frequentes, separadas por vírgula."""
    cleaned = clean_text(text)
    tokens = tokenize_and_remove_stopwords(cleaned)
    if not tokens:
        return ""
    counts = Counter(tokens)
    most_common = [word for word, _ in counts.most_common(n)]
    return ",".join(most_common)

def apply_nlp(df: pd.DataFrame, text_column: str = "review_text") -> pd.DataFrame:
    """Aplica NLP: clean_text, sentiment e top keywords no DataFrame."""
    df = df.copy()
    if text_column not in df.columns:
        df[text_column] = ""
    df["clean_text"] = df[text_column].astype(str).apply(clean_text)
    df["sentiment"] = df[text_column].astype(str).apply(sentiment_vader)
    df["keywords"] = df[text_column].astype(str).apply(lambda t: top_keywords(t, n=5))
    return df
