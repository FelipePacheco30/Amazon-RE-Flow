# src/db.py
import os
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, Boolean, insert
from sqlalchemy.orm import declarative_base, sessionmaker

# Configuração do DB (padrão: sqlite local)
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///data/db/reviews.db')

# engine e session
engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, future=True)
Base = declarative_base()

class Review(Base):
    __tablename__ = 'reviews'
    id = Column(Integer, primary_key=True, autoincrement=True)
    review_id = Column(String, unique=True, index=True)
    product_id = Column(String, index=True)
    review_text = Column(Text)
    rating = Column(Float)
    review_date = Column(DateTime)
    sentiment = Column(String)
    keywords = Column(String)
    review_len = Column(Integer)
    review_word_count = Column(Integer)
    reviews_username = Column(String)
    reviews_title = Column(String)
    brand = Column(String)
    categories = Column(String)

def init_db():
    """
    Cria a pasta do DB (se necessário) e cria as tabelas.
    """
    # se for sqlite, garantir que a pasta exista
    if DATABASE_URL.startswith("sqlite:///"):
        db_path = DATABASE_URL.replace("sqlite:///", "")
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    return engine

def save_df(df):
    """
    Salva um DataFrame no banco (upsert via INSERT OR REPLACE para SQLite).
    Retorna quantidade de linhas processadas.
    """
    init_db()
    records = df.to_dict(orient="records")
    if not records:
        return 0
    # Usamos INSERT OR REPLACE para evitar duplicatas em review_id
    stmt = insert(Review).prefix_with("OR REPLACE")
    with engine.begin() as conn:
        conn.execute(stmt, records)
    return len(records)
