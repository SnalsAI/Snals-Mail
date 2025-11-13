"""
Model per interpretazione email
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class Interpretazione(Base):
    """Interpretazione contenuto email"""
    
    __tablename__ = "interpretazioni"
    
    id = Column(Integer, primary_key=True, index=True)
    email_id = Column(Integer, ForeignKey("emails.id"), unique=True, nullable=False)
    
    # Dati interpretazione
    categoria = Column(String(100), nullable=False)
    interpretazione_json = Column(JSON, nullable=False)
    
    # Qualità
    confidence = Column(Float)
    
    # Revisione
    richiede_revisione = Column(Boolean, default=False)
    revisionata = Column(Boolean, default=False)
    revisione_note = Column(Text)
    revisore_user_id = Column(Integer, ForeignKey("utenti.id"))
    
    # Timestamp
    timestamp_creazione = Column(DateTime, default=datetime.utcnow)
    timestamp_revisione = Column(DateTime)
    
    # Relazioni
    email = relationship("Email", back_populates="interpretazione")
    revisore = relationship("Utente", foreign_keys=[revisore_user_id])
    
    def __repr__(self):
        return f"<Interpretazione {self.id}: Email {self.email_id}>"
