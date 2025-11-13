"""
Model per regole personalizzate
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, JSON, DateTime
from datetime import datetime

from app.database import Base


class Regola(Base):
    """Regola personalizzata"""
    
    __tablename__ = "regole"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Info regola
    nome = Column(String(255), nullable=False)
    descrizione = Column(Text)
    
    # Stato
    attivo = Column(Boolean, default=True, index=True)
    priorita = Column(Integer, default=10, index=True)
    
    # Condizioni (JSON schema)
    condizioni = Column(JSON, nullable=False)
    
    # Azioni (JSON schema)
    azioni = Column(JSON, nullable=False)
    
    # Statistiche
    volte_applicata = Column(Integer, default=0)
    ultima_applicazione = Column(DateTime)
    
    # Metadati
    created_by = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Regola {self.id}: {self.nome}>"
