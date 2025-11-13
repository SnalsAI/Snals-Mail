"""
Regola model
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON
from sqlalchemy.sql import func
from app.database import Base


class Regola(Base):
    """Modello Regola"""
    __tablename__ = "regole"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, unique=True, index=True)
    descrizione = Column(Text, nullable=True)
    attivo = Column(Boolean, default=True)
    priorita = Column(Integer, default=10, index=True)
    condizioni = Column(JSON)  # Struttura condizioni con operatori logici
    azioni = Column(JSON)  # Lista azioni da eseguire
    volte_applicata = Column(Integer, default=0)
    ultima_applicazione = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
