# src/db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, String, Float, Integer

Base = declarative_base()

class Review(Base):
    __tablename__ = 'reviews'
    review_id = Column(String, primary_key=True)
    product_id = Column(String)
    review_text = Column(String)
    rating = Column(Float)
    review_date = Column(String)
    reviews_username = Column(String)
    reviews_title = Column(String)
    reviews_numhelpful = Column(Integer)
    reviews_dorecommend = Column(String)
    brand = Column(String)
    name = Column(String)
    categories = Column(String)
    primarycategories = Column(String)
    review_len = Column(Integer)
    review_word_count = Column(Integer)
    clean_text = Column(String)
    sentiment = Column(String)
    keywords = Column(String)

def init_db(db_path='data/db/reviews.db'):
    """Inicializa banco SQLite e retorna engine"""
    engine = create_engine(f'sqlite:///{db_path}', echo=False)
    Base.metadata.create_all(engine)
    return engine

def save_df(engine, df, table_name='reviews'):
    """Salva DataFrame em tabela SQL usando SQLAlchemy engine"""
    df.to_sql(table_name, engine, if_exists='replace', index=False)
