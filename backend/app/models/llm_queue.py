"""
Model per coda richieste LLM.
Gestisce l'elaborazione sequenziale delle chiamate LLM per evitare sovraccarico.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Enum
from datetime import datetime
import enum

from app.database import Base


class StatoRichiestaLLM(str, enum.Enum):
    """Stati possibili di una richiesta LLM"""
    IN_CODA = "in_coda"
    IN_ELABORAZIONE = "in_elaborazione"
    COMPLETATA = "completata"
    FALLITA = "fallita"


class RichiestaLLM(Base):
    """Richiesta LLM in coda"""

    __tablename__ = "richieste_llm"

    id = Column(Integer, primary_key=True, index=True)

    # Tipo e riferimento
    tipo = Column(String(100), nullable=False, index=True)  # es: "evento_calendario", "sintesi", "risposta"
    riferimento_tipo = Column(String(50))  # es: "azione", "email"
    riferimento_id = Column(Integer)  # ID dell'oggetto di riferimento

    # Richiesta
    prompt = Column(Text, nullable=False)
    model_type = Column(String(50), default="interpretation")
    format_json = Column(Integer, default=0)  # Boolean as int

    # Stato
    stato = Column(String(50), default="in_coda", index=True)
    priorita = Column(Integer, default=5, index=True)  # 1=alta, 10=bassa

    # Risultato
    risposta = Column(Text)
    risposta_parsed = Column(JSON)
    errore = Column(Text)

    # Timing
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    # Callback (opzionale - per notificare il completamento)
    callback_url = Column(String(500))

    def __repr__(self):
        return f"<RichiestaLLM {self.id}: {self.tipo} - {self.stato}>"
