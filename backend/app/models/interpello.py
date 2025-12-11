"""
Model per interpelli scolastici
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey, Date
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.database import Base


class StatoInterpello(enum.Enum):
    """Stato interpello"""
    APERTO = "aperto"
    CHIUSO = "chiuso"
    SCADUTO = "scaduto"


class Interpello(Base):
    """Interpello per ricerca docenti"""

    __tablename__ = "interpelli"

    id = Column(Integer, primary_key=True, index=True)
    email_id = Column(Integer, ForeignKey('emails.id'), nullable=False, index=True)

    # Informazioni sulla posizione
    classe_concorso = Column(String(10), nullable=True, index=True)  # es. A042 (nullable per parsing parziali)
    numero_posti = Column(Integer, nullable=True)  # numero posti disponibili
    ore_settimanali = Column(Integer, nullable=True)  # ore settimanali

    # Informazioni temporali
    data_scadenza = Column(DateTime, nullable=True, index=True)  # scadenza candidature
    data_inizio_servizio = Column(Date, nullable=True)  # data presa di servizio
    data_fine_contratto = Column(Date, nullable=True)  # data fine contratto

    # Informazioni sulla sede
    provincia = Column(String(100), nullable=True, index=True)  # es. Rimini
    citta = Column(String(100), nullable=True)  # città
    istituto = Column(String(255), nullable=True)  # nome istituto
    indirizzo = Column(String(255), nullable=True)  # indirizzo sede

    # Dettagli contratto
    tipo_contratto = Column(String(100), nullable=True)  # supplenza, spezzone orario, ecc.
    orario_giorni = Column(String(255), nullable=True)  # es. "Lunedì, Martedì, Mercoledì e Venerdì"

    # Link e riferimenti
    link_candidatura = Column(String(500), nullable=True)  # URL per candidarsi
    link_titoli_accesso = Column(String(500), nullable=True)  # URL info titoli

    # Modalità di partecipazione / contatti
    email_contatto = Column(String(255), nullable=True)  # email per candidatura
    telefono_contatto = Column(String(100), nullable=True)  # telefono per info
    referente_contatto = Column(String(255), nullable=True)  # nome referente
    modalita_candidatura = Column(Text, nullable=True)  # descrizione modalità candidatura

    # Testo completo e metadati
    testo_completo = Column(Text, nullable=True)  # testo completo interpello
    metadata_estrazione = Column(JSON, nullable=True)  # metadati estrazione AI

    # Stato
    stato = Column(String(20), default="aperto", index=True)  # aperto, chiuso, scaduto
    verificato = Column(Boolean, default=False)  # se è stato verificato manualmente

    # Timestamp
    data_pubblicazione = Column(DateTime, nullable=True)  # quando è stato pubblicato
    data_creazione = Column(DateTime, default=datetime.utcnow)
    data_aggiornamento = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relazioni
    email = relationship("Email", back_populates="interpello")

    def __repr__(self):
        return f"<Interpello {self.classe_concorso} - {self.provincia or 'N/A'}>"
