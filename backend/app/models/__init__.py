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

# Modulo Prenotazioni (NUOVO - completamente separato dal calendario esistente)
from app.models.booking import (
    # Enums
    StatoSlot,
    StatoPrenotazione,
    TipoNotifica,
    StatoNotifica,
    AzioneAudit,
    TipoUtenteAudit,
    # Models
    BookingSede,
    BookingStaff,
    BookingTipoAppuntamento,
    BookingStaffCompetenza,
    BookingCampagna,
    BookingCampagnaTipoAppuntamento,
    BookingDisponibilita,
    BookingSlot,
    BookingContatto,
    BookingPrenotazione,
    BookingNotifica,
    BookingAuditLog,
    BookingConfig,
    # Config defaults
    DEFAULT_BOOKING_CONFIG,
)

__all__ = [
    # Email
    "Email",
    "AccountType",
    "EmailCategory",
    "EmailStatus",
    "Interpretazione",
    "Azione",
    "TipoAzione",
    "StatoAzione",
    # Calendario esistente
    "EventoCalendario",
    # Regole e sistema
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
    # === MODULO PRENOTAZIONI (NUOVO) ===
    # Enums
    "StatoSlot",
    "StatoPrenotazione",
    "TipoNotifica",
    "StatoNotifica",
    "AzioneAudit",
    "TipoUtenteAudit",
    # Models
    "BookingSede",
    "BookingStaff",
    "BookingTipoAppuntamento",
    "BookingStaffCompetenza",
    "BookingCampagna",
    "BookingCampagnaTipoAppuntamento",
    "BookingDisponibilita",
    "BookingSlot",
    "BookingContatto",
    "BookingPrenotazione",
    "BookingNotifica",
    "BookingAuditLog",
    "BookingConfig",
    "DEFAULT_BOOKING_CONFIG",
]
