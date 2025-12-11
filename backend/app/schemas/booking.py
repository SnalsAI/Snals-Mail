"""
Pydantic schemas per il modulo Prenotazioni

Organizzati per entità:
- Sede
- Staff
- TipoAppuntamento
- Campagna
- Disponibilita
- Slot
- Contatto
- Prenotazione
"""

from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List
from datetime import datetime, date, time
from enum import Enum


# ============================================================================
# ENUMS (mirror dei modelli SQLAlchemy)
# ============================================================================

class StatoSlotEnum(str, Enum):
    LIBERO = "libero"
    PRENOTATO = "prenotato"
    BLOCCATO = "bloccato"


class StatoPrenotazioneEnum(str, Enum):
    CONFERMATA = "confermata"
    ANNULLATA_UTENTE = "annullata_utente"
    ANNULLATA_UFFICIO = "annullata_ufficio"
    NO_SHOW = "no_show"
    COMPLETATA = "completata"


class TipoNotificaEnum(str, Enum):
    CONFERMA = "conferma"
    PROMEMORIA_24H = "promemoria_24h"
    PROMEMORIA_48H = "promemoria_48h"
    PROMEMORIA_DOCUMENTI = "promemoria_documenti"
    ANNULLAMENTO = "annullamento"
    MODIFICA = "modifica"
    SPOSTAMENTO = "spostamento"


# ============================================================================
# SEDE
# ============================================================================

class SedeBase(BaseModel):
    nome: str = Field(..., min_length=1, max_length=200)
    indirizzo: Optional[str] = None
    citta: Optional[str] = None
    cap: Optional[str] = None
    provincia: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[EmailStr] = None
    note: Optional[str] = None
    latitudine: Optional[str] = None
    longitudine: Optional[str] = None


class SedeCreate(SedeBase):
    pass


class SedeUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=1, max_length=200)
    indirizzo: Optional[str] = None
    citta: Optional[str] = None
    cap: Optional[str] = None
    provincia: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[EmailStr] = None
    note: Optional[str] = None
    attivo: Optional[bool] = None


class SedeResponse(SedeBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    attivo: bool
    created_at: Optional[datetime] = None


class SedeListResponse(BaseModel):
    items: List[SedeResponse]
    total: int


# ============================================================================
# TIPO APPUNTAMENTO
# ============================================================================

class TipoAppuntamentoBase(BaseModel):
    nome: str = Field(..., min_length=1, max_length=200)
    descrizione: Optional[str] = None
    durata_default_minuti: int = Field(default=30, ge=5, le=480)
    istruzioni: Optional[str] = None
    colore: Optional[str] = Field(default="#3B82F6", pattern=r"^#[0-9A-Fa-f]{6}$")
    ordine: Optional[int] = 0


class TipoAppuntamentoCreate(TipoAppuntamentoBase):
    pass


class TipoAppuntamentoUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=1, max_length=200)
    descrizione: Optional[str] = None
    durata_default_minuti: Optional[int] = Field(None, ge=5, le=480)
    istruzioni: Optional[str] = None
    colore: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    ordine: Optional[int] = None
    attivo: Optional[bool] = None


class TipoAppuntamentoResponse(TipoAppuntamentoBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    attivo: bool
    created_at: Optional[datetime] = None


# ============================================================================
# STAFF
# ============================================================================

class StaffBase(BaseModel):
    nome: str = Field(..., min_length=1, max_length=100)
    cognome: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    telefono: Optional[str] = None
    ruolo: Optional[str] = None


class StaffCreate(StaffBase):
    sede_id: int


class StaffUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=1, max_length=100)
    cognome: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    telefono: Optional[str] = None
    ruolo: Optional[str] = None
    sede_id: Optional[int] = None
    attivo: Optional[bool] = None


class StaffResponse(StaffBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sede_id: int
    attivo: bool
    nome_completo: str
    created_at: Optional[datetime] = None


class StaffDetailResponse(StaffResponse):
    """Staff con dettagli sede e competenze"""
    sede: Optional[SedeResponse] = None
    competenze: Optional[List["StaffCompetenzaResponse"]] = None


# ============================================================================
# STAFF COMPETENZA
# ============================================================================

class StaffCompetenzaBase(BaseModel):
    tipo_appuntamento_id: int
    durata_minuti: Optional[int] = Field(None, ge=5, le=480, description="Override durata (null = usa default)")


class StaffCompetenzaCreate(StaffCompetenzaBase):
    staff_id: int


class StaffCompetenzaUpdate(BaseModel):
    durata_minuti: Optional[int] = Field(None, ge=5, le=480)
    attivo: Optional[bool] = None


class StaffCompetenzaResponse(StaffCompetenzaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    staff_id: int
    attivo: bool
    tipo_appuntamento: Optional[TipoAppuntamentoResponse] = None


# ============================================================================
# CAMPAGNA
# ============================================================================

class CampagnaBase(BaseModel):
    nome: str = Field(..., min_length=1, max_length=200)
    descrizione: Optional[str] = None
    data_inizio: date
    data_fine: date
    slug: Optional[str] = Field(None, min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")


class CampagnaCreate(CampagnaBase):
    tipi_appuntamento_ids: Optional[List[int]] = []


class CampagnaUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=1, max_length=200)
    descrizione: Optional[str] = None
    data_inizio: Optional[date] = None
    data_fine: Optional[date] = None
    slug: Optional[str] = None
    attivo: Optional[bool] = None
    tipi_appuntamento_ids: Optional[List[int]] = None


class CampagnaResponse(CampagnaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    attivo: bool
    created_at: Optional[datetime] = None


class CampagnaDetailResponse(CampagnaResponse):
    """Campagna con tipi appuntamento associati"""
    tipi_appuntamento: Optional[List[TipoAppuntamentoResponse]] = None


# ============================================================================
# DISPONIBILITA
# ============================================================================

class DisponibilitaBase(BaseModel):
    data: date
    ora_inizio: time
    ora_fine: time
    ricorrenza: Optional[str] = None
    note: Optional[str] = None


class DisponibilitaCreate(DisponibilitaBase):
    staff_id: int
    sede_id: int


class DisponibilitaBulkCreate(BaseModel):
    """Crea disponibilità per più giorni"""
    staff_id: int
    sede_id: int
    date_list: List[date]
    ora_inizio: time
    ora_fine: time
    note: Optional[str] = None


class DisponibilitaUpdate(BaseModel):
    data: Optional[date] = None
    ora_inizio: Optional[time] = None
    ora_fine: Optional[time] = None
    sede_id: Optional[int] = None
    note: Optional[str] = None
    attivo: Optional[bool] = None


class DisponibilitaResponse(DisponibilitaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    staff_id: int
    sede_id: int
    attivo: bool
    created_at: Optional[datetime] = None


class DisponibilitaDetailResponse(DisponibilitaResponse):
    staff: Optional[StaffResponse] = None
    sede: Optional[SedeResponse] = None


# ============================================================================
# SLOT
# ============================================================================

class SlotBase(BaseModel):
    data_ora_inizio: datetime
    data_ora_fine: datetime


class SlotCreate(SlotBase):
    staff_id: int
    sede_id: int
    tipo_appuntamento_id: int
    disponibilita_id: Optional[int] = None


class SlotGenerateRequest(BaseModel):
    """Request per generare slot da disponibilità"""
    disponibilita_id: Optional[int] = None
    staff_id: Optional[int] = None
    data_inizio: Optional[date] = None
    data_fine: Optional[date] = None
    tipi_appuntamento_ids: Optional[List[int]] = None


class SlotUpdate(BaseModel):
    stato: Optional[StatoSlotEnum] = None
    note: Optional[str] = None


class SlotResponse(SlotBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    staff_id: int
    sede_id: int
    tipo_appuntamento_id: int
    stato: StatoSlotEnum
    durata_minuti: int
    is_disponibile: bool
    created_at: Optional[datetime] = None


class SlotDetailResponse(SlotResponse):
    staff: Optional[StaffResponse] = None
    sede: Optional[SedeResponse] = None
    tipo_appuntamento: Optional[TipoAppuntamentoResponse] = None


class SlotDisponibiliRequest(BaseModel):
    """Filtri per ricerca slot disponibili (pubblico)"""
    sede_id: Optional[int] = None
    tipo_appuntamento_id: Optional[int] = None
    campagna_id: Optional[int] = None
    data_da: Optional[date] = None
    data_a: Optional[date] = None


class SlotDisponibiliResponse(BaseModel):
    items: List[SlotDetailResponse]
    total: int


# ============================================================================
# CONTATTO (utente esterno)
# ============================================================================

class ContattoBase(BaseModel):
    nome: str = Field(..., min_length=1, max_length=100)
    cognome: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    telefono: Optional[str] = None
    codice_fiscale: Optional[str] = Field(None, min_length=16, max_length=16)
    ruolo_scuola: Optional[str] = None
    ordine_scuola: Optional[str] = None
    tipologia_contratto: Optional[str] = None
    scuola_attuale: Optional[str] = None
    provincia: Optional[str] = None


class ContattoCreate(ContattoBase):
    consenso_privacy: bool = Field(..., description="Deve essere True")
    consenso_marketing: Optional[bool] = False


class ContattoUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=1, max_length=100)
    cognome: Optional[str] = Field(None, min_length=1, max_length=100)
    telefono: Optional[str] = None
    ruolo_scuola: Optional[str] = None
    ordine_scuola: Optional[str] = None
    tipologia_contratto: Optional[str] = None
    scuola_attuale: Optional[str] = None
    provincia: Optional[str] = None
    consenso_marketing: Optional[bool] = None


class ContattoResponse(ContattoBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome_completo: str
    consenso_privacy: bool
    consenso_marketing: bool
    privacy_version: Optional[str] = None
    created_at: Optional[datetime] = None


class ContattoStoricoResponse(ContattoResponse):
    """Contatto con storico prenotazioni"""
    prenotazioni: Optional[List["PrenotazioneResponse"]] = None
    totale_prenotazioni: int = 0


# ============================================================================
# PRENOTAZIONE
# ============================================================================

class PrenotazioneCreatePublic(BaseModel):
    """Schema per prenotazione da utente esterno"""
    slot_id: int
    campagna_id: Optional[int] = None
    note_utente: Optional[str] = None
    # Dati contatto
    contatto: ContattoCreate


class PrenotazioneCreate(BaseModel):
    """Schema per prenotazione da admin/staff"""
    slot_id: int
    contatto_id: int
    campagna_id: Optional[int] = None
    note_utente: Optional[str] = None
    note_admin: Optional[str] = None


class PrenotazioneUpdate(BaseModel):
    note_utente: Optional[str] = None
    note_admin: Optional[str] = None


class PrenotazioneAnnullaRequest(BaseModel):
    motivo: Optional[str] = None


class PrenotazioneSpostaRequest(BaseModel):
    nuovo_slot_id: int


class PrenotazioneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    contatto_id: int
    slot_id: int
    campagna_id: Optional[int] = None
    token_pubblico: str
    stato: StatoPrenotazioneEnum
    note_utente: Optional[str] = None
    data_conferma: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PrenotazioneDetailResponse(PrenotazioneResponse):
    """Prenotazione con dettagli completi"""
    contatto: Optional[ContattoResponse] = None
    slot: Optional[SlotDetailResponse] = None
    campagna: Optional[CampagnaResponse] = None
    note_admin: Optional[str] = None
    annullato_da: Optional[str] = None
    annullato_at: Optional[datetime] = None
    motivo_annullamento: Optional[str] = None


class PrenotazionePublicResponse(BaseModel):
    """Response per utente esterno (senza dati sensibili admin)"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    token_pubblico: str
    stato: StatoPrenotazioneEnum
    note_utente: Optional[str] = None
    data_conferma: Optional[datetime] = None
    # Dettagli appuntamento
    data_ora: Optional[datetime] = None
    durata_minuti: Optional[int] = None
    sede_nome: Optional[str] = None
    sede_indirizzo: Optional[str] = None
    tipo_appuntamento: Optional[str] = None
    istruzioni: Optional[str] = None
    # Link gestione
    link_modifica: Optional[str] = None
    link_annulla: Optional[str] = None


class PrenotazioneListResponse(BaseModel):
    items: List[PrenotazioneDetailResponse]
    total: int
    page: int = 1
    per_page: int = 20


# ============================================================================
# NOTIFICA
# ============================================================================

class NotificaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    prenotazione_id: int
    tipo: TipoNotificaEnum
    destinatario: str
    stato: str
    programmata_per: Optional[datetime] = None
    inviata_at: Optional[datetime] = None
    errore: Optional[str] = None
    created_at: Optional[datetime] = None


# ============================================================================
# AUDIT LOG
# ============================================================================

class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    prenotazione_id: Optional[int] = None
    azione: str
    utente_tipo: str
    utente_email: Optional[str] = None
    descrizione: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: Optional[datetime] = None


class AuditLogListResponse(BaseModel):
    items: List[AuditLogResponse]
    total: int


# ============================================================================
# CONFIG
# ============================================================================

class ConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    chiave: str
    valore: str
    tipo: str
    descrizione: Optional[str] = None


class ConfigUpdate(BaseModel):
    valore: str


# ============================================================================
# STATISTICHE
# ============================================================================

class StatisticheResponse(BaseModel):
    prenotazioni_oggi: int = 0
    prenotazioni_settimana: int = 0
    prenotazioni_mese: int = 0
    prenotazioni_per_stato: dict = {}
    prenotazioni_per_sede: dict = {}
    prenotazioni_per_tipo: dict = {}
    slot_disponibili_oggi: int = 0
    slot_disponibili_settimana: int = 0


# ============================================================================
# RESPONSE GENERICHE
# ============================================================================

class SuccessResponse(BaseModel):
    success: bool = True
    message: str


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    detail: Optional[str] = None


# Forward references per relazioni circolari
StaffDetailResponse.model_rebuild()
ContattoStoricoResponse.model_rebuild()
