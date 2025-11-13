"""
Model per email ricevute
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, JSON, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.database import Base


class AccountType(enum.Enum):
    """Tipo account email"""
    NORMALE = "normale"
    PEC = "pec"


class EmailCategory(enum.Enum):
    """Categorie email"""
    INFO_GENERICHE = "info_generiche"
    RICHIESTA_APPUNTAMENTO = "richiesta_appuntamento"
    RICHIESTA_TESSERAMENTO = "richiesta_tesseramento"
    CONVOCAZIONE_SCUOLA = "convocazione_scuola"
    COMUNICAZIONE_UST_USR = "comunicazione_ust_usr"
    COMUNICAZIONE_SCUOLA = "comunicazione_scuola"
    COMUNICAZIONE_SNALS_CENTRALE = "comunicazione_snals_centrale"
    VARIE = "varie"


class EmailStatus(enum.Enum):
    """Stato elaborazione email"""
    RICEVUTA = "ricevuta"
    IN_ELABORAZIONE = "in_elaborazione"
    CATEGORIZZATA = "categorizzata"
    INTERPRETATA = "interpretata"
    AZIONE_ESEGUITA = "azione_eseguita"
    ERRORE = "errore"
    COMPLETATA = "completata"


class Email(Base):
    """Email ricevuta"""
    
    __tablename__ = "emails"
    
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(String(255), unique=True, nullable=False, index=True)
    
    # Account origine
    account_type = Column(Enum(AccountType), nullable=False)
    
    # Metadati base
    mittente = Column(String(255), nullable=False, index=True)
    destinatario = Column(String(255), nullable=False)
    oggetto = Column(String(500))
    corpo = Column(Text)
    
    # Timestamp
    data_ricezione = Column(DateTime, nullable=False, index=True)
    data_elaborazione = Column(DateTime)
    
    # Allegati
    allegati_path = Column(JSON)
    allegati_nomi = Column(JSON)
    
    # Categorizzazione
    categoria = Column(Enum(EmailCategory), index=True)
    categoria_confidence = Column(Float)
    
    # Stato
    stato = Column(Enum(EmailStatus), default=EmailStatus.RICEVUTA, index=True)
    
    # Flag speciali
    richiede_revisione = Column(Boolean, default=False)
    revisionata = Column(Boolean, default=False)
    priorita = Column(Integer, default=0)
    
    # Relazioni
    interpretazione = relationship("Interpretazione", back_populates="email", uselist=False)
    azioni = relationship("Azione", back_populates="email")
    
    # Metadati
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Email {self.id}: {self.oggetto[:50] if self.oggetto else 'No subject'}>"
