"""
EventoCalendario model
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class EventoCalendario(Base):
    """Modello Evento Google Calendar"""
    __tablename__ = "eventi_calendario"

    id = Column(Integer, primary_key=True, index=True)
    email_id = Column(Integer, ForeignKey("emails.id"))
    google_event_id = Column(String, unique=True)
    titolo = Column(String)
    data_inizio = Column(DateTime)
    data_fine = Column(DateTime, nullable=True)
    luogo = Column(String, nullable=True)
    assegnatario_id = Column(Integer, nullable=True)  # FK to users table
    created_at = Column(DateTime, server_default=func.now())
