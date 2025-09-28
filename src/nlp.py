# src/nlp.py
import pandas as pd
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import nltk

nltk.download('vader_lexicon')
nltk.download('punkt')
STOPWORDS = set(stopwords.words('english'))

def clean_text(text):
    if pd.isna(text):
        return ""
    return (
        text.lower()
        .replace('\n', ' ')
        .replace('\r', ' ')
    )

def sentiment(text):
    sia = SentimentIntensityAnalyzer()
    score = sia.polarity_scores(text)['compound']
    if score >= 0.05:
        return "positive"
    elif score <= -0.05:
        return "negative"
    else:
        return "neutral"

def top_keywords(text, n=5):
    tokens = [t for t in word_tokenize(text) if t.isalpha() and t not in STOPWORDS]
    freq = pd.Series(tokens).value_counts()
    return ','.join(freq.head(n).index.tolist())

def apply_nlp(df):
    df['clean_text'] = df['review_text'].apply(clean_text)
    df['sentiment'] = df['clean_text'].apply(sentiment)
    df['keywords'] = df['clean_text'].apply(lambda x: top_keywords(x, n=5))
    return df
