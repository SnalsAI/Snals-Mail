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
    # Azioni di risposta
    BOZZA_RISPOSTA = "BOZZA_RISPOSTA"
    INVIA_RISPOSTA_AUTOMATICA = "invia_risposta_automatica"

    # Azioni di gestione
    BOZZA_APPUNTAMENTO = "BOZZA_APPUNTAMENTO"
    BOZZA_TESSERAMENTO = "BOZZA_TESSERAMENTO"
    CREA_TASK = "crea_task"

    # Azioni di calendario
    EVENTO_CALENDARIO = "EVENTO_CALENDARIO"

    # Azioni di comunicazione
    INOLTRA = "INOLTRA"
    INOLTRA_EMAIL = "inoltra_email"
    INOLTRA_DELEGATI_ZONA = "INOLTRA_DELEGATI_ZONA"
    NOTIFICA = "NOTIFICA"
    INVIA_NOTIFICA = "invia_notifica"

    # Azioni di archiviazione e organizzazione
    ARCHIVIA = "archivia"
    SEGNA_IMPORTANTE = "segna_importante"
    PUBBLICA_SU_SITO = "pubblica_su_sito"

    # Azioni di elaborazione
    SINTESI = "SINTESI"
    INDICIZZA_RAG = "INDICIZZA_RAG"
    PARSE_INTERPELLO = "PARSE_INTERPELLO"

    # Azioni di moderazione
    ELIMINA = "elimina"
    SPAM = "SPAM"


class StatoAzione(enum.Enum):
    """Stato esecuzione azione"""
    IN_CODA = "IN_CODA"
    IN_ESECUZIONE = "IN_ESECUZIONE"
    COMPLETATA = "COMPLETATA"
    FALLITA = "FALLITA"
    ANNULLATA = "ANNULLATA"


class Azione(Base):
    """Azione eseguita su email"""
    
    __tablename__ = "azioni"
    
    id = Column(Integer, primary_key=True, index=True)
    email_id = Column(Integer, ForeignKey("emails.id"), nullable=False)
    
    # Tipo azione
    tipo = Column(Enum(TipoAzione, values_callable=lambda x: [e.value for e in x]), nullable=False)
    stato = Column(Enum(StatoAzione, values_callable=lambda x: [e.value for e in x]), default=StatoAzione.IN_CODA, index=True)
    
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
