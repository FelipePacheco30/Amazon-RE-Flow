# src/nlp.py
import re
from collections import Counter
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.sentiment import SentimentIntensityAnalyzer

# downloads (serão ignorados se já existentes)
nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)
nltk.download('vader_lexicon', quiet=True)

STOPWORDS = set(stopwords.words('english'))
sia = SentimentIntensityAnalyzer()

def clean_text(text):
    text = str(text).lower()
    text = re.sub(r'http\S+','', text)
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def get_sentiment(text):
    if not text:
        return 'neutral'
    score = sia.polarity_scores(text)['compound']
    if score >= 0.05:
        return 'positive'
    if score <= -0.05:
        return 'negative'
    return 'neutral'

def top_keywords(text, n=5):
    tokens = [t for t in word_tokenize(text) if t.isalpha() and t not in STOPWORDS]
    counts = Counter(tokens)
    return ','.join([w for w,_ in counts.most_common(n)])
