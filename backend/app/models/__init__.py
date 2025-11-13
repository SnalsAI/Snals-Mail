"""
Import tutti i models per Alembic
"""

from app.models.email import Email, AccountType, EmailCategory, EmailStatus
from app.models.interpretazione import Interpretazione
from app.models.azione import Azione, TipoAzione, StatoAzione
from app.models.evento import EventoCalendario
from app.models.regola import Regola
from app.models.utente import Utente, RuoloUtente
from app.models.log_sistema import LogSistema, LivelloLog

__all__ = [
    "Email",
    "AccountType",
    "EmailCategory",
    "EmailStatus",
    "Interpretazione",
    "Azione",
    "TipoAzione",
    "StatoAzione",
    "EventoCalendario",
    "Regola",
    "Utente",
    "RuoloUtente",
    "LogSistema",
    "LivelloLog",
]
