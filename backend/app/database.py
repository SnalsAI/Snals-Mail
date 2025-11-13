"""
Database configuration
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Database URL (da configurare in .env)
SQLALCHEMY_DATABASE_URL = "postgresql://snals_user:password@localhost/snals_email_agent"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency per FastAPI"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
