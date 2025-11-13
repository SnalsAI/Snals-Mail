"""
Interpretazione model
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class Interpretazione(Base):
    """Modello Interpretazione LLM"""
    __tablename__ = "interpretazioni"

    id = Column(Integer, primary_key=True, index=True)
    email_id = Column(Integer, ForeignKey("emails.id"), unique=True)
    categoria = Column(String)
    interpretazione_json = Column(JSON)
    confidence = Column(Float)
    created_at = Column(DateTime, server_default=func.now())
