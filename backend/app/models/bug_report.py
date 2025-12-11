"""
Modello per Bug Reports - Sistema di segnalazione bug dall'interfaccia utente
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Enum
from datetime import datetime
import enum

from app.database import Base


class BugStatus(str, enum.Enum):
    """Stato del bug report"""
    APERTO = "aperto"
    IN_ANALISI = "in_analisi"
    IN_CORSO = "in_corso"
    RISOLTO = "risolto"
    CHIUSO = "chiuso"
    NON_RIPRODUCIBILE = "non_riproducibile"


class BugPriority(str, enum.Enum):
    """Priorità del bug"""
    BASSA = "bassa"
    MEDIA = "media"
    ALTA = "alta"
    CRITICA = "critica"


class BugReport(Base):
    """
    Bug report segnalato dall'utente tramite UI.

    Contiene:
    - Descrizione del problema dall'utente
    - Dati di contesto raccolti automaticamente (pagina, browser, timestamp)
    - Stato e priorità per gestione
    - Note tecniche per la risoluzione
    """

    __tablename__ = "bug_reports"

    id = Column(Integer, primary_key=True, index=True)

    # Descrizione utente
    descrizione = Column(Text, nullable=False)

    # Contesto automatico
    pagina = Column(String(500))  # URL/route della pagina
    componente = Column(String(200))  # Componente React se identificabile
    browser = Column(String(200))  # User agent
    viewport = Column(String(50))  # Dimensioni schermo

    # Dati tecnici opzionali
    console_errors = Column(JSON)  # Errori console JS catturati
    network_errors = Column(JSON)  # Errori di rete recenti
    local_storage_snapshot = Column(JSON)  # Stato localStorage rilevante

    # Contesto email/azione se applicabile
    email_id = Column(Integer, nullable=True)
    azione_id = Column(Integer, nullable=True)

    # Gestione bug - usiamo String per evitare problemi con enum PostgreSQL
    stato = Column(String(30), default='aperto')
    priorita = Column(String(20), default='media')

    # Note per sviluppatore/AI
    note_tecniche = Column(Text)  # Note sulla causa/soluzione
    file_coinvolti = Column(JSON)  # Lista file da modificare
    soluzione_proposta = Column(Text)  # Descrizione della fix

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<BugReport {self.id}: {self.descrizione[:50]}... ({self.stato})>"

    def to_dict(self):
        return {
            "id": self.id,
            "descrizione": self.descrizione,
            "pagina": self.pagina,
            "componente": self.componente,
            "browser": self.browser,
            "viewport": self.viewport,
            "console_errors": self.console_errors,
            "network_errors": self.network_errors,
            "email_id": self.email_id,
            "azione_id": self.azione_id,
            "stato": self.stato,
            "priorita": self.priorita,
            "note_tecniche": self.note_tecniche,
            "file_coinvolti": self.file_coinvolti,
            "soluzione_proposta": self.soluzione_proposta,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }
