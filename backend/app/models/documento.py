"""
Model per documenti da embeddare per RAG.

FASE 9: RAG System
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Enum as SQLEnum, JSON
from sqlalchemy.sql import func
from datetime import datetime
from enum import Enum

from app.database import Base


class TipoDocumento(str, Enum):
    """Tipo di documento."""
    SNALS_CENTRALE = "snals_centrale"
    USR_USP = "usr_usp"
    NORMATIVA = "normativa"
    CIRCOLARE = "circolare"
    CONTRATTO = "contratto"
    FAQ = "faq"
    ALTRO = "altro"


class StatoDocumento(str, Enum):
    """Stato del documento."""
    CARICATO = "caricato"
    PROCESSATO = "processato"
    EMBEDDATO = "embeddato"
    ERRORE = "errore"


class Documento(Base):
    """
    Documenti da usare per RAG.

    Supporta documenti da SNALS centrale, USR/USP, normative, ecc.
    """
    __tablename__ = "documenti"

    id = Column(Integer, primary_key=True, index=True)

    # Info documento
    titolo = Column(String(500), nullable=False)
    descrizione = Column(Text, nullable=True)
    tipo = Column(SQLEnum(TipoDocumento), nullable=False, index=True)

    # Sorgente
    url_sorgente = Column(String(1000), nullable=True)
    file_path = Column(String(1000), nullable=True)  # Path nel filesystem

    # Contenuto
    contenuto_originale = Column(Text, nullable=True)  # Testo estratto
    metadata = Column(JSON, nullable=True)  # Metadata aggiuntivi

    # Embedding
    embedding_abilitato = Column(Boolean, default=True, index=True)
    stato = Column(SQLEnum(StatoDocumento), default=StatoDocumento.CARICATO, index=True)
    vector_store_id = Column(String(255), nullable=True)  # ID nel vector store
    num_chunks = Column(Integer, default=0)  # Numero di chunk creati

    # Priorità per RAG
    priorita = Column(Integer, default=10)  # Più alto = più importante
    attivo = Column(Boolean, default=True, index=True)  # Usare nel RAG?

    # Versioning
    versione = Column(String(50), nullable=True)
    data_documento = Column(DateTime, nullable=True)  # Data del documento originale

    # Audit
    caricato_at = Column(DateTime, default=datetime.now, nullable=False)
    processato_at = Column(DateTime, nullable=True)
    embeddato_at = Column(DateTime, nullable=True)
    ultimo_accesso = Column(DateTime, nullable=True)
    num_utilizzi = Column(Integer, default=0)  # Quante volte usato nel RAG

    # Errori
    errore_messaggio = Column(Text, nullable=True)

    def __repr__(self):
        return f"<Documento {self.id}: {self.titolo} ({self.tipo.value})>"
