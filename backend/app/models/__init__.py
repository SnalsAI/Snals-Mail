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
from app.models.system_settings import SystemSettings
from app.models.delegato import Delegato, Zona
from app.models.interpello import Interpello, StatoInterpello
from app.models.knowledge_document import KnowledgeDocument, TipoDocumento
from app.models.llm_queue import RichiestaLLM, StatoRichiestaLLM

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
    "SystemSettings",
    "Delegato",
    "Zona",
    "Interpello",
    "StatoInterpello",
    "KnowledgeDocument",
    "TipoDocumento",
    "RichiestaLLM",
    "StatoRichiestaLLM",
]
