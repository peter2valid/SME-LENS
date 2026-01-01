from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

PROD_DB_URL = os.getenv("DATABASE_URL", "sqlite:///./smelens.db")
# For SQLite, we need to disable same_thread_check
connect_args = {"check_same_thread": False} if "sqlite" in PROD_DB_URL else {}

engine = create_engine(
    PROD_DB_URL, connect_args=connect_args
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
