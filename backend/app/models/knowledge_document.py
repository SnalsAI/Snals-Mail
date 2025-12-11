"""
Model per documenti Knowledge Base caricati manualmente.

Permette di gestire normativa, FAQ, circolari e altri documenti
che arricchiscono il RAG per risposte più accurate.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, Date, Enum
from datetime import datetime
import enum

from app.database import Base
from app.models.email import EmailCategory


class TipoDocumento(enum.Enum):
    """Tipo di documento knowledge base"""
    NORMATIVA = "normativa"  # Leggi, decreti, DM, DPCM
    CIRCOLARE = "circolare"  # Circolari ministeriali, USR
    FAQ = "faq"  # Domande frequenti e risposte
    MODELLO = "modello"  # Template risposte standard
    CONTRATTO = "contratto"  # CCNL, contratti integrativi
    PRASSI = "prassi"  # Procedure interne, best practices
    GUIDA = "guida"  # Guide operative, manuali
    INTERPELLO_TIPO = "interpello_tipo"  # Tipologia interpelli ricorrenti
    ALTRO = "altro"  # Altri documenti


class KnowledgeDocument(Base):
    """Documento knowledge base caricato manualmente"""

    __tablename__ = "knowledge_documents"

    id = Column(Integer, primary_key=True, index=True)

    # Informazioni base
    titolo = Column(String(500), nullable=False, index=True)
    descrizione = Column(Text)  # Descrizione estesa
    file_path = Column(String(1000), nullable=False)  # Path file su disco
    file_name = Column(String(500), nullable=False)  # Nome file originale
    file_size = Column(Integer)  # Dimensione in bytes
    file_type = Column(String(50))  # MIME type (application/pdf, etc)

    # Categorizzazione
    tipo_documento = Column(Enum(TipoDocumento), nullable=False, index=True)
    categoria_email = Column(String(100), nullable=True, index=True)  # A quale categoria si riferisce (evita conflitti enum)

    # Metadati ricercabili
    tags = Column(JSON, default=list)  # ["GPS", "graduatorie", "2024/2025", "supplenze"]
    ente_emittente = Column(String(200), index=True)  # "Ministero Istruzione", "SNALS Nazionale", "USR Puglia"
    data_emissione = Column(Date, index=True)  # Data emissione documento
    numero_protocollo = Column(String(100))  # Numero protocollo ufficiale
    anno_riferimento = Column(String(20))  # "2024/2025", "2025" per anno scolastico/normativa

    # Contenuto
    testo_estratto = Column(Text)  # Testo estratto dal documento
    testo_length = Column(Integer)  # Lunghezza testo

    # RAG Integration
    indexed_in_rag = Column(Boolean, default=False, index=True)  # Se indicizzato in ChromaDB
    rag_document_ids = Column(JSON, default=list)  # Lista IDs documenti in ChromaDB
    rag_indexed_at = Column(DateTime)  # Quando è stato indicizzato

    # Metadata gestione
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    caricato_da = Column(String(100))  # Username operatore che ha caricato
    note_interne = Column(Text)  # Note per uso interno

    # Stato
    attivo = Column(Boolean, default=True, index=True)  # Se il documento è attivo
    verificato = Column(Boolean, default=False)  # Se verificato da supervisore

    def __repr__(self):
        return f"<KnowledgeDocument {self.id}: {self.titolo[:50]}>"

    @property
    def tags_str(self) -> str:
        """Tags come stringa separata da virgole"""
        if not self.tags:
            return ""
        return ", ".join(self.tags)

    @property
    def file_size_mb(self) -> float:
        """Dimensione file in MB"""
        if not self.file_size:
            return 0.0
        return round(self.file_size / (1024 * 1024), 2)
