"""
Endpoint Admin per il modulo Prenotazioni

Questi endpoint saranno protetti quando l'auth verrà attivata.
Gli admin possono:
- Gestire sedi, staff, tipi appuntamento, campagne
- Vedere tutte le prenotazioni
- Generare slot
- Esportare dati
- Configurare il sistema
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import Optional, List
from datetime import datetime, date, timedelta
import csv
import io

from app.database import get_db
from app.models.booking import (
    BookingSede, BookingStaff, BookingTipoAppuntamento, BookingStaffCompetenza,
    BookingCampagna, BookingCampagnaTipoAppuntamento, BookingDisponibilita,
    BookingSlot, BookingContatto, BookingPrenotazione, BookingNotifica,
    BookingAuditLog, BookingConfig,
    StatoSlot, StatoPrenotazione
)
from app.schemas.booking import (
    # Sede
    SedeCreate, SedeUpdate, SedeResponse, SedeListResponse,
    # Staff
    StaffCreate, StaffUpdate, StaffResponse, StaffDetailResponse,
    # Competenza
    StaffCompetenzaCreate, StaffCompetenzaUpdate, StaffCompetenzaResponse,
    # Tipo Appuntamento
    TipoAppuntamentoCreate, TipoAppuntamentoUpdate, TipoAppuntamentoResponse,
    # Campagna
    CampagnaCreate, CampagnaUpdate, CampagnaResponse, CampagnaDetailResponse,
    # Slot
    SlotGenerateRequest, SlotResponse, SlotDetailResponse,
    # Contatto
    ContattoResponse, ContattoStoricoResponse,
    # Prenotazione
    PrenotazioneDetailResponse, PrenotazioneListResponse,
    # Altri
    AuditLogResponse, AuditLogListResponse,
    ConfigResponse, ConfigUpdate,
    StatisticheResponse, SuccessResponse
)
from .deps import require_admin_auth

router = APIRouter()


# ============================================================================
# SEDI
# ============================================================================

@router.get("/sedi", response_model=List[SedeResponse])
async def lista_sedi(
    attivo: Optional[bool] = Query(None),
    auth: bool = Depends(require_admin_auth),
    db: Session = Depends(get_db)
):
    """Lista tutte le sedi."""
    query = db.query(BookingSede)
    if attivo is not None:
        query = query.filter(BookingSede.attivo == attivo)
    return query.order_by(BookingSede.nome).all()


@router.post("/sedi", response_model=SedeResponse)
async def crea_sede(
    data: SedeCreate,
    auth: bool = Depends(require_admin_auth),
    db: Session = Depends(get_db)
):
    """Crea una nuova sede."""
    sede = BookingSede(**data.model_dump())
    db.add(sede)
    db.commit()
    db.refresh(sede)
    return sede


@router.get("/sedi/{id}", response_model=SedeResponse)
async def dettaglio_sede(
    id: int,
    auth: bool = Depends(require_admin_auth),
    db: Session = Depends(get_db)
):
    """Dettaglio sede."""
    sede = db.query(BookingSede).get(id)
    if not sede:
        raise HTTPException(status_code=404, detail="Sede non trovata")
    return sede


@router.put("/sedi/{id}", response_model=SedeResponse)
async def aggiorna_sede(
    id: int,
    data: SedeUpdate,
    auth: bool = Depends(require_admin_auth),
    db: Session = Depends(get_db)
):
    """Aggiorna una sede."""
    sede = db.query(BookingSede).get(id)
    if not sede:
        raise HTTPException(status_code=404, detail="Sede non trovata")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(sede, field, value)

    sede.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(sede)
    return sede


@router.delete("/sedi/{id}", response_model=SuccessResponse)
async def elimina_sede(
    id: int,
    auth: bool = Depends(require_admin_auth),
    db: Session = Depends(get_db)
):
    """Disattiva una sede (soft delete)."""
    sede = db.query(BookingSede).get(id)
    if not sede:
        raise HTTPException(status_code=404, detail="Sede non trovata")

    sede.attivo = False
    sede.updated_at = datetime.utcnow()
    db.commit()
    return SuccessResponse(message="Sede disattivata")


# ============================================================================
# STAFF
# ============================================================================

@router.get("/staff", response_model=List[StaffDetailResponse])
async def lista_staff(
    sede_id: Optional[int] = Query(None),
    attivo: Optional[bool] = Query(None),
    auth: bool = Depends(require_admin_auth),
    db: Session = Depends(get_db)
):
    """Lista staff con dettagli."""
    query = db.query(BookingStaff)
    if sede_id:
        query = query.filter(BookingStaff.sede_id == sede_id)
    if attivo is not None:
        query = query.filter(BookingStaff.attivo == attivo)
    return query.order_by(BookingStaff.cognome, BookingStaff.nome).all()


@router.post("/staff", response_model=StaffResponse)
async def crea_staff(
    data: StaffCreate,
    auth: bool = Depends(require_admin_auth),
    db: Session = Depends(get_db)
):
    """Crea un nuovo staff."""
    # Verifica sede
    sede = db.query(BookingSede).get(data.sede_id)
    if not sede:
        raise HTTPException(status_code=404, detail="Sede non trovata")

    staff = BookingStaff(**data.model_dump())
    db.add(staff)
    db.commit()
    db.refresh(staff)
    return staff


@router.get("/staff/{id}", response_model=StaffDetailResponse)
async def dettaglio_staff(
    id: int,
    auth: bool = Depends(require_admin_auth),
    db: Session = Depends(get_db)
):
    """Dettaglio staff con competenze."""
    staff = db.query(BookingStaff).get(id)
    if not staff:
        raise HTTPException(status_code=404, detail="Staff non trovato")
    return staff


@router.put("/staff/{id}", response_model=StaffResponse)
async def aggiorna_staff(
    id: int,
    data: StaffUpdate,
    auth: bool = Depends(require_admin_auth),
    db: Session = Depends(get_db)
):
    """Aggiorna uno staff."""
    staff = db.query(BookingStaff).get(id)
    if not staff:
        raise HTTPException(status_code=404, detail="Staff non trovato")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(staff, field, value)

    staff.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(staff)
    return staff


@router.delete("/staff/{id}", response_model=SuccessResponse)
async def elimina_staff(
    id: int,
    auth: bool = Depends(require_admin_auth),
    db: Session = Depends(get_db)
):
    """Disattiva uno staff."""
    staff = db.query(BookingStaff).get(id)
    if not staff:
        raise HTTPException(status_code=404, detail="Staff non trovato")

    staff.attivo = False
    staff.updated_at = datetime.utcnow()
    db.commit()
    return SuccessResponse(message="Staff disattivato")


# ============================================================================
# COMPETENZE STAFF
# ============================================================================

@router.post("/staff/{staff_id}/competenze", response_model=StaffCompetenzaResponse)
async def aggiungi_competenza(
    staff_id: int,
    data: StaffCompetenzaCreate,
    auth: bool = Depends(require_admin_auth),
    db: Session = Depends(get_db)
):
    """Aggiunge una competenza allo staff."""
    staff = db.query(BookingStaff).get(staff_id)
    if not staff:
        raise HTTPException(status_code=404, detail="Staff non trovato")

    tipo = db.query(BookingTipoAppuntamento).get(data.tipo_appuntamento_id)
    if not tipo:
        raise HTTPException(status_code=404, detail="Tipo appuntamento non trovato")

    # Verifica duplicato
    existing = db.query(BookingStaffCompetenza).filter(
        BookingStaffCompetenza.staff_id == staff_id,
        BookingStaffCompetenza.tipo_appuntamento_id == data.tipo_appuntamento_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Competenza già esistente")

    competenza = BookingStaffCompetenza(
        staff_id=staff_id,
        tipo_appuntamento_id=data.tipo_appuntamento_id,
        durata_minuti=data.durata_minuti
    )
    db.add(competenza)
    db.commit()
    db.refresh(competenza)
    return competenza


@router.put("/staff/competenze/{id}", response_model=StaffCompetenzaResponse)
async def aggiorna_competenza(
    id: int,
    data: StaffCompetenzaUpdate,
    auth: bool = Depends(require_admin_auth),
    db: Session = Depends(get_db)
):
    """Aggiorna una competenza (es. durata personalizzata)."""
    competenza = db.query(BookingStaffCompetenza).get(id)
    if not competenza:
        raise HTTPException(status_code=404, detail="Competenza non trovata")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(competenza, field, value)

    db.commit()
    db.refresh(competenza)
    return competenza


@router.delete("/staff/competenze/{id}", response_model=SuccessResponse)
async def elimina_competenza(
    id: int,
    auth: bool = Depends(require_admin_auth),
    db: Session = Depends(get_db)
):
    """Rimuove una competenza."""
    competenza = db.query(BookingStaffCompetenza).get(id)
    if not competenza:
        raise HTTPException(status_code=404, detail="Competenza non trovata")

    db.delete(competenza)
    db.commit()
    return SuccessResponse(message="Competenza rimossa")


# ============================================================================
# TIPI APPUNTAMENTO
# ============================================================================

@router.get("/tipi-appuntamento", response_model=List[TipoAppuntamentoResponse])
async def lista_tipi_appuntamento(
    attivo: Optional[bool] = Query(None),
    auth: bool = Depends(require_admin_auth),
    db: Session = Depends(get_db)
):
    """Lista tipi appuntamento."""
    query = db.query(BookingTipoAppuntamento)
    if attivo is not None:
        query = query.filter(BookingTipoAppuntamento.attivo == attivo)
    return query.order_by(BookingTipoAppuntamento.ordine).all()


@router.post("/tipi-appuntamento", response_model=TipoAppuntamentoResponse)
async def crea_tipo_appuntamento(
    data: TipoAppuntamentoCreate,
    auth: bool = Depends(require_admin_auth),
    db: Session = Depends(get_db)
):
    """Crea un nuovo tipo appuntamento."""
    tipo = BookingTipoAppuntamento(**data.model_dump())
    db.add(tipo)
    db.commit()
    db.refresh(tipo)
    return tipo


@router.put("/tipi-appuntamento/{id}", response_model=TipoAppuntamentoResponse)
async def aggiorna_tipo_appuntamento(
    id: int,
    data: TipoAppuntamentoUpdate,
    auth: bool = Depends(require_admin_auth),
    db: Session = Depends(get_db)
):
    """Aggiorna un tipo appuntamento."""
    tipo = db.query(BookingTipoAppuntamento).get(id)
    if not tipo:
        raise HTTPException(status_code=404, detail="Tipo non trovato")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(tipo, field, value)

    tipo.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(tipo)
    return tipo


@router.delete("/tipi-appuntamento/{id}", response_model=SuccessResponse)
async def elimina_tipo_appuntamento(
    id: int,
    auth: bool = Depends(require_admin_auth),
    db: Session = Depends(get_db)
):
    """Disattiva un tipo appuntamento."""
    tipo = db.query(BookingTipoAppuntamento).get(id)
    if not tipo:
        raise HTTPException(status_code=404, detail="Tipo non trovato")

    tipo.attivo = False
    tipo.updated_at = datetime.utcnow()
    db.commit()
    return SuccessResponse(message="Tipo appuntamento disattivato")


# ============================================================================
# CAMPAGNE
# ============================================================================

@router.get("/campagne", response_model=List[CampagnaDetailResponse])
async def lista_campagne(
    attivo: Optional[bool] = Query(None),
    auth: bool = Depends(require_admin_auth),
    db: Session = Depends(get_db)
):
    """Lista campagne con tipi appuntamento."""
    query = db.query(BookingCampagna)
    if attivo is not None:
        query = query.filter(BookingCampagna.attivo == attivo)
    return query.order_by(BookingCampagna.data_inizio.desc()).all()


@router.post("/campagne", response_model=CampagnaDetailResponse)
async def crea_campagna(
    data: CampagnaCreate,
    auth: bool = Depends(require_admin_auth),
    db: Session = Depends(get_db)
):
    """Crea una nuova campagna."""
    # Genera slug se non fornito
    if not data.slug:
        import re
        data.slug = re.sub(r'[^a-z0-9]+', '-', data.nome.lower()).strip('-')

    # Verifica slug univoco
    existing = db.query(BookingCampagna).filter(BookingCampagna.slug == data.slug).first()
    if existing:
        raise HTTPException(status_code=400, detail="Slug già esistente")

    campagna = BookingCampagna(
        nome=data.nome,
        descrizione=data.descrizione,
        data_inizio=data.data_inizio,
        data_fine=data.data_fine,
        slug=data.slug
    )
    db.add(campagna)
    db.flush()

    # Associa tipi appuntamento
    if data.tipi_appuntamento_ids:
        for tipo_id in data.tipi_appuntamento_ids:
            tipo = db.query(BookingTipoAppuntamento).get(tipo_id)
            if tipo:
                campagna.tipi_appuntamento.append(tipo)

    db.commit()
    db.refresh(campagna)
    return campagna


@router.put("/campagne/{id}", response_model=CampagnaDetailResponse)
async def aggiorna_campagna(
    id: int,
    data: CampagnaUpdate,
    auth: bool = Depends(require_admin_auth),
    db: Session = Depends(get_db)
):
    """Aggiorna una campagna."""
    campagna = db.query(BookingCampagna).get(id)
    if not campagna:
        raise HTTPException(status_code=404, detail="Campagna non trovata")

    # Aggiorna campi base
    for field, value in data.model_dump(exclude_unset=True, exclude={'tipi_appuntamento_ids'}).items():
        if value is not None:
            setattr(campagna, field, value)

    # Aggiorna associazioni tipi
    if data.tipi_appuntamento_ids is not None:
        campagna.tipi_appuntamento.clear()
        for tipo_id in data.tipi_appuntamento_ids:
            tipo = db.query(BookingTipoAppuntamento).get(tipo_id)
            if tipo:
                campagna.tipi_appuntamento.append(tipo)

    campagna.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(campagna)
    return campagna


@router.delete("/campagne/{id}", response_model=SuccessResponse)
async def elimina_campagna(
    id: int,
    auth: bool = Depends(require_admin_auth),
    db: Session = Depends(get_db)
):
    """Disattiva una campagna."""
    campagna = db.query(BookingCampagna).get(id)
    if not campagna:
        raise HTTPException(status_code=404, detail="Campagna non trovata")

    campagna.attivo = False
    campagna.updated_at = datetime.utcnow()
    db.commit()
    return SuccessResponse(message="Campagna disattivata")


# ============================================================================
# GENERAZIONE SLOT
# ============================================================================

@router.post("/slots/genera", response_model=SuccessResponse)
async def genera_slots(
    data: SlotGenerateRequest,
    auth: bool = Depends(require_admin_auth),
    db: Session = Depends(get_db)
):
    """
    Genera slot dalle disponibilità.

    Per ogni disponibilità, crea N slot in base alla durata
    di ogni tipo appuntamento gestito dallo staff.
    """
    from app.services.booking.slot_generator import SlotGeneratorService

    generator = SlotGeneratorService(db)

    if data.disponibilita_id:
        # Genera da singola disponibilità
        count = generator.genera_slots_da_disponibilita(
            data.disponibilita_id,
            data.tipi_appuntamento_ids
        )
    elif data.staff_id and data.data_inizio and data.data_fine:
        # Genera per staff in periodo
        count = generator.genera_slots_periodo(
            data.staff_id,
            data.data_inizio,
            data.data_fine,
            data.tipi_appuntamento_ids
        )
    else:
        raise HTTPException(
            status_code=400,
            detail="Specificare disponibilita_id oppure staff_id + data_inizio + data_fine"
        )

    return SuccessResponse(
        success=True,
        message=f"Generati {count} slot"
    )


# ============================================================================
# PRENOTAZIONI
# ============================================================================

@router.get("/prenotazioni", response_model=PrenotazioneListResponse)
async def lista_prenotazioni(
    sede_id: Optional[int] = Query(None),
    staff_id: Optional[int] = Query(None),
    campagna_id: Optional[int] = Query(None),
    stato: Optional[StatoPrenotazione] = Query(None),
    data_da: Optional[date] = Query(None),
    data_a: Optional[date] = Query(None),
    search: Optional[str] = Query(None, description="Cerca per nome/email contatto"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    auth: bool = Depends(require_admin_auth),
    db: Session = Depends(get_db)
):
    """Lista tutte le prenotazioni con filtri."""
    query = db.query(BookingPrenotazione).join(BookingSlot)

    # Filtri
    if sede_id:
        query = query.filter(BookingSlot.sede_id == sede_id)
    if staff_id:
        query = query.filter(BookingSlot.staff_id == staff_id)
    if campagna_id:
        query = query.filter(BookingPrenotazione.campagna_id == campagna_id)
    if stato:
        query = query.filter(BookingPrenotazione.stato == stato)
    if data_da:
        query = query.filter(BookingSlot.data_ora_inizio >= datetime.combine(data_da, datetime.min.time()))
    if data_a:
        query = query.filter(BookingSlot.data_ora_inizio <= datetime.combine(data_a, datetime.max.time()))
    if search:
        query = query.join(BookingContatto).filter(
            (BookingContatto.nome.ilike(f"%{search}%")) |
            (BookingContatto.cognome.ilike(f"%{search}%")) |
            (BookingContatto.email.ilike(f"%{search}%"))
        )

    total = query.count()
    offset = (page - 1) * per_page
    prenotazioni = query.order_by(BookingSlot.data_ora_inizio.desc()).offset(offset).limit(per_page).all()

    return PrenotazioneListResponse(
        items=prenotazioni,
        total=total,
        page=page,
        per_page=per_page
    )


@router.get("/prenotazioni/export")
async def esporta_prenotazioni(
    sede_id: Optional[int] = Query(None),
    campagna_id: Optional[int] = Query(None),
    stato: Optional[StatoPrenotazione] = Query(None),
    data_da: Optional[date] = Query(None),
    data_a: Optional[date] = Query(None),
    auth: bool = Depends(require_admin_auth),
    db: Session = Depends(get_db)
):
    """Esporta prenotazioni in CSV."""
    query = db.query(BookingPrenotazione).join(BookingSlot).join(BookingContatto)

    if sede_id:
        query = query.filter(BookingSlot.sede_id == sede_id)
    if campagna_id:
        query = query.filter(BookingPrenotazione.campagna_id == campagna_id)
    if stato:
        query = query.filter(BookingPrenotazione.stato == stato)
    if data_da:
        query = query.filter(BookingSlot.data_ora_inizio >= datetime.combine(data_da, datetime.min.time()))
    if data_a:
        query = query.filter(BookingSlot.data_ora_inizio <= datetime.combine(data_a, datetime.max.time()))

    prenotazioni = query.order_by(BookingSlot.data_ora_inizio).all()

    # Genera CSV
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        'ID', 'Data/Ora', 'Durata', 'Sede', 'Staff', 'Tipo',
        'Nome', 'Cognome', 'Email', 'Telefono', 'CF',
        'Ruolo Scuola', 'Contratto', 'Scuola',
        'Stato', 'Creata', 'Note'
    ])

    # Dati
    for p in prenotazioni:
        writer.writerow([
            p.id,
            p.slot.data_ora_inizio.strftime('%d/%m/%Y %H:%M') if p.slot else '',
            p.slot.durata_minuti if p.slot else '',
            p.slot.sede.nome if p.slot and p.slot.sede else '',
            p.slot.staff.nome_completo if p.slot and p.slot.staff else '',
            p.slot.tipo_appuntamento.nome if p.slot and p.slot.tipo_appuntamento else '',
            p.contatto.nome if p.contatto else '',
            p.contatto.cognome if p.contatto else '',
            p.contatto.email if p.contatto else '',
            p.contatto.telefono if p.contatto else '',
            p.contatto.codice_fiscale if p.contatto else '',
            p.contatto.ruolo_scuola if p.contatto else '',
            p.contatto.tipologia_contratto if p.contatto else '',
            p.contatto.scuola_attuale if p.contatto else '',
            p.stato.value,
            p.created_at.strftime('%d/%m/%Y %H:%M') if p.created_at else '',
            p.note_utente or ''
        ])

    output.seek(0)

    filename = f"prenotazioni_{date.today().strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ============================================================================
# CONTATTI
# ============================================================================

@router.get("/contatti", response_model=List[ContattoResponse])
async def lista_contatti(
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    auth: bool = Depends(require_admin_auth),
    db: Session = Depends(get_db)
):
    """Lista contatti."""
    query = db.query(BookingContatto)

    if search:
        query = query.filter(
            (BookingContatto.nome.ilike(f"%{search}%")) |
            (BookingContatto.cognome.ilike(f"%{search}%")) |
            (BookingContatto.email.ilike(f"%{search}%"))
        )

    offset = (page - 1) * per_page
    return query.order_by(BookingContatto.cognome).offset(offset).limit(per_page).all()


@router.get("/contatti/{id}/storico", response_model=ContattoStoricoResponse)
async def storico_contatto(
    id: int,
    auth: bool = Depends(require_admin_auth),
    db: Session = Depends(get_db)
):
    """Dettaglio contatto con storico prenotazioni."""
    contatto = db.query(BookingContatto).get(id)
    if not contatto:
        raise HTTPException(status_code=404, detail="Contatto non trovato")

    # Conta prenotazioni
    totale = db.query(func.count(BookingPrenotazione.id)).filter(
        BookingPrenotazione.contatto_id == id
    ).scalar()

    return ContattoStoricoResponse(
        **contatto.__dict__,
        nome_completo=contatto.nome_completo,
        prenotazioni=contatto.prenotazioni,
        totale_prenotazioni=totale
    )


# ============================================================================
# AUDIT LOG
# ============================================================================

@router.get("/audit-log", response_model=AuditLogListResponse)
async def lista_audit_log(
    prenotazione_id: Optional[int] = Query(None),
    azione: Optional[str] = Query(None),
    data_da: Optional[date] = Query(None),
    data_a: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    auth: bool = Depends(require_admin_auth),
    db: Session = Depends(get_db)
):
    """Lista audit log."""
    query = db.query(BookingAuditLog)

    if prenotazione_id:
        query = query.filter(BookingAuditLog.prenotazione_id == prenotazione_id)
    if azione:
        query = query.filter(BookingAuditLog.azione == azione)
    if data_da:
        query = query.filter(BookingAuditLog.created_at >= datetime.combine(data_da, datetime.min.time()))
    if data_a:
        query = query.filter(BookingAuditLog.created_at <= datetime.combine(data_a, datetime.max.time()))

    total = query.count()
    offset = (page - 1) * per_page
    logs = query.order_by(BookingAuditLog.created_at.desc()).offset(offset).limit(per_page).all()

    return AuditLogListResponse(items=logs, total=total)


# ============================================================================
# STATISTICHE
# ============================================================================

@router.get("/statistiche", response_model=StatisticheResponse)
async def statistiche(
    auth: bool = Depends(require_admin_auth),
    db: Session = Depends(get_db)
):
    """Dashboard statistiche prenotazioni."""
    oggi = date.today()
    inizio_settimana = oggi - timedelta(days=oggi.weekday())
    inizio_mese = oggi.replace(day=1)

    # Prenotazioni oggi
    prenotazioni_oggi = db.query(func.count(BookingPrenotazione.id)).join(BookingSlot).filter(
        func.date(BookingSlot.data_ora_inizio) == oggi
    ).scalar()

    # Prenotazioni settimana
    prenotazioni_settimana = db.query(func.count(BookingPrenotazione.id)).join(BookingSlot).filter(
        func.date(BookingSlot.data_ora_inizio) >= inizio_settimana,
        func.date(BookingSlot.data_ora_inizio) <= oggi
    ).scalar()

    # Prenotazioni mese
    prenotazioni_mese = db.query(func.count(BookingPrenotazione.id)).join(BookingSlot).filter(
        func.date(BookingSlot.data_ora_inizio) >= inizio_mese
    ).scalar()

    # Per stato
    per_stato = dict(db.query(
        BookingPrenotazione.stato,
        func.count(BookingPrenotazione.id)
    ).group_by(BookingPrenotazione.stato).all())

    # Per sede
    per_sede = dict(db.query(
        BookingSede.nome,
        func.count(BookingPrenotazione.id)
    ).join(BookingSlot, BookingSlot.sede_id == BookingSede.id).join(
        BookingPrenotazione, BookingPrenotazione.slot_id == BookingSlot.id
    ).group_by(BookingSede.nome).all())

    # Per tipo
    per_tipo = dict(db.query(
        BookingTipoAppuntamento.nome,
        func.count(BookingPrenotazione.id)
    ).join(BookingSlot, BookingSlot.tipo_appuntamento_id == BookingTipoAppuntamento.id).join(
        BookingPrenotazione, BookingPrenotazione.slot_id == BookingSlot.id
    ).group_by(BookingTipoAppuntamento.nome).all())

    # Slot disponibili oggi
    slot_oggi = db.query(func.count(BookingSlot.id)).filter(
        BookingSlot.stato == StatoSlot.LIBERO,
        func.date(BookingSlot.data_ora_inizio) == oggi,
        BookingSlot.data_ora_inizio > datetime.now()
    ).scalar()

    # Slot disponibili settimana
    slot_settimana = db.query(func.count(BookingSlot.id)).filter(
        BookingSlot.stato == StatoSlot.LIBERO,
        BookingSlot.data_ora_inizio >= datetime.now(),
        func.date(BookingSlot.data_ora_inizio) <= inizio_settimana + timedelta(days=6)
    ).scalar()

    return StatisticheResponse(
        prenotazioni_oggi=prenotazioni_oggi or 0,
        prenotazioni_settimana=prenotazioni_settimana or 0,
        prenotazioni_mese=prenotazioni_mese or 0,
        prenotazioni_per_stato={str(k): v for k, v in per_stato.items()},
        prenotazioni_per_sede=per_sede,
        prenotazioni_per_tipo=per_tipo,
        slot_disponibili_oggi=slot_oggi or 0,
        slot_disponibili_settimana=slot_settimana or 0
    )


# ============================================================================
# CONFIGURAZIONE
# ============================================================================

@router.get("/config", response_model=List[ConfigResponse])
async def lista_config(
    auth: bool = Depends(require_admin_auth),
    db: Session = Depends(get_db)
):
    """Lista configurazioni."""
    return db.query(BookingConfig).order_by(BookingConfig.chiave).all()


@router.put("/config/{chiave}", response_model=ConfigResponse)
async def aggiorna_config(
    chiave: str,
    data: ConfigUpdate,
    auth: bool = Depends(require_admin_auth),
    db: Session = Depends(get_db)
):
    """Aggiorna una configurazione."""
    config = db.query(BookingConfig).filter(BookingConfig.chiave == chiave).first()
    if not config:
        raise HTTPException(status_code=404, detail="Configurazione non trovata")

    config.valore = data.valore
    config.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(config)
    return config
