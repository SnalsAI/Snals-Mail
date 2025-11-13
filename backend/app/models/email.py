"""
Email model
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Enum as SQLEnum
from sqlalchemy.sql import func
from app.database import Base
import enum


class EmailCategory(enum.Enum):
    """Categorie email"""
    CONVOCAZIONE_SCUOLA = "convocazione_scuola"
    CONVOCAZIONE_SNALS = "convocazione_snals"
    RICHIESTA_ASSISTENZA = "richiesta_assistenza"
    CONTENZIOSO = "contenzioso"
    INFO_GENERICHE = "info_generiche"
    CIRCOLARE = "circolare"
    SPAM = "spam"
    ALTRO = "altro"


class AccountType(enum.Enum):
    """Tipo account email"""
    NORMALE = "normale"
    PEC = "pec"


class EmailStatus(enum.Enum):
    """Stato email"""
    RICEVUTA = "ricevuta"
    IN_ELABORAZIONE = "in_elaborazione"
    ELABORATA = "elaborata"
    ERRORE = "errore"


class Email(Base):
    """Modello Email"""
    __tablename__ = "emails"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(String, unique=True, index=True)
    account_type = Column(SQLEnum(AccountType))
    mittente = Column(String, index=True)
    destinatario = Column(String)
    oggetto = Column(String)
    corpo = Column(Text)
    data_ricezione = Column(DateTime, index=True)
    categoria = Column(SQLEnum(EmailCategory), index=True)
    stato = Column(SQLEnum(EmailStatus), default=EmailStatus.RICEVUTA)
    created_at = Column(DateTime, server_default=func.now())
