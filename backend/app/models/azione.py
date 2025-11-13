"""
Model per azioni eseguite
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.database import Base


class TipoAzione(enum.Enum):
    """Tipi di azione automatica"""
    BOZZA_RISPOSTA = "bozza_risposta"
    BOZZA_APPUNTAMENTO = "bozza_appuntamento"
    BOZZA_TESSERAMENTO = "bozza_tesseramento"
    EVENTO_CALENDARIO = "evento_calendario"
    UPLOAD_DRIVE = "upload_drive"
    SINTESI = "sintesi"
    INOLTRA = "inoltra"
    NOTIFICA = "notifica"


class StatoAzione(enum.Enum):
    """Stato esecuzione azione"""
    IN_CODA = "in_coda"
    IN_ESECUZIONE = "in_esecuzione"
    COMPLETATA = "completata"
    FALLITA = "fallita"
    ANNULLATA = "annullata"


class Azione(Base):
    """Azione eseguita su email"""
    
    __tablename__ = "azioni"
    
    id = Column(Integer, primary_key=True, index=True)
    email_id = Column(Integer, ForeignKey("emails.id"), nullable=False)
    
    # Tipo azione
    tipo = Column(Enum(TipoAzione), nullable=False)
    stato = Column(Enum(StatoAzione), default=StatoAzione.IN_CODA, index=True)
    
    # Dettagli
    dettagli = Column(JSON)
    risultato = Column(JSON)
    errore = Column(Text)
    
    # Timestamp
    timestamp_inizio = Column(DateTime, default=datetime.utcnow)
    timestamp_fine = Column(DateTime)
    
    # Relazioni
    email = relationship("Email", back_populates="azioni")
    
    def __repr__(self):
        return f"<Azione {self.id}: {self.tipo.value}>"
