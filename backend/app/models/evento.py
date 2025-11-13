"""
Model per eventi calendario
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class EventoCalendario(Base):
    """Evento calendario interno"""
    
    __tablename__ = "eventi_calendario"
    
    id = Column(Integer, primary_key=True, index=True)
    email_id = Column(Integer, ForeignKey("emails.id"))
    
    # Dettagli evento
    titolo = Column(String(500), nullable=False)
    descrizione = Column(Text)
    
    # Timing
    data_inizio = Column(DateTime, nullable=False, index=True)
    data_fine = Column(DateTime)
    all_day = Column(Boolean, default=False)
    
    # Luogo
    luogo = Column(String(500))
    link_videocall = Column(String(500))
    
    # Contesto SNALS
    scuola = Column(String(255), index=True)
    tipo_convocazione = Column(String(100))
    
    # Assegnazione
    assegnatario_id = Column(Integer, ForeignKey("utenti.id"))
    
    # Sync Google
    google_calendar_id = Column(String(255))
    google_event_id = Column(String(255))
    sincronizzato = Column(Boolean, default=False)
    
    # Allegati
    allegati = Column(JSON)
    
    # Metadati
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relazioni
    email = relationship("Email")
    assegnatario = relationship("Utente", foreign_keys=[assegnatario_id])
    
    def __repr__(self):
        return f"<EventoCalendario {self.id}: {self.titolo}>"
