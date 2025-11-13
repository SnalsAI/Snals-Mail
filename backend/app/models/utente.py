"""
Model per utenti sistema
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from datetime import datetime
import enum

from app.database import Base


class RuoloUtente(enum.Enum):
    """Ruoli utente"""
    ADMIN = "admin"
    OPERATORE = "operatore"
    VISUALIZZATORE = "visualizzatore"


class Utente(Base):
    """Utente sistema"""
    
    __tablename__ = "utenti"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Credenziali
    email = Column(String(255), unique=True, nullable=False, index=True)
    nome = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    
    # Ruolo
    ruolo = Column(Enum(RuoloUtente), default=RuoloUtente.OPERATORE)
    
    # Stato
    attivo = Column(Boolean, default=True)
    
    # Metadati
    created_at = Column(DateTime, default=datetime.utcnow)
    ultimo_accesso = Column(DateTime)
    
    def __repr__(self):
        return f"<Utente {self.id}: {self.nome}>"
