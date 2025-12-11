"""
Endpoint per Staff/Operatori del modulo Prenotazioni

Questi endpoint saranno protetti quando l'auth verrà attivata.
Lo staff può:
- Gestire le proprie disponibilità
- Vedere il proprio calendario prenotazioni
- Marcare prenotazioni come completate o no-show
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import Optional, List
from datetime import datetime, date, timedelta

from app.database import get_db
from app.models.booking import (
    BookingStaff, BookingDisponibilita, BookingSlot, BookingPrenotazione,
    BookingSede, StatoSlot, StatoPrenotazione
)
from app.schemas.booking import (
    DisponibilitaCreate, DisponibilitaBulkCreate, DisponibilitaUpdate,
    DisponibilitaResponse, DisponibilitaDetailResponse,
    SlotResponse, SlotDetailResponse,
    PrenotazioneDetailResponse, PrenotazioneListResponse,
    SuccessResponse
)
from .deps import require_staff_auth, get_current_staff

router = APIRouter()


# ============================================================================
# DISPONIBILITA
# ============================================================================

@router.get("/disponibilita", response_model=List[DisponibilitaDetailResponse])
async def lista_mie_disponibilita(
    staff_id: Optional[int] = Query(None, description="ID staff (temporaneo finché auth disabilitata)"),
    data_da: Optional[date] = Query(None),
    data_a: Optional[date] = Query(None),
    auth: bool = Depends(require_staff_auth),
    db: Session = Depends(get_db)
):
    """
    Lista disponibilità dello staff.

    Quando auth attiva, staff_id viene da token.
    Per ora va passato come query param.
    """
    if not staff_id:
        raise HTTPException(
            status_code=400,
            detail="staff_id richiesto (auth non attiva)"
        )

    query = db.query(BookingDisponibilita).filter(
        BookingDisponibilita.staff_id == staff_id,
        BookingDisponibilita.attivo == True
    )

    if data_da:
        query = query.filter(BookingDisponibilita.data >= data_da)
    if data_a:
        query = query.filter(BookingDisponibilita.data <= data_a)

    disponibilita = query.order_by(BookingDisponibilita.data).all()
    return disponibilita


@router.post("/disponibilita", response_model=DisponibilitaResponse)
async def crea_disponibilita(
    data: DisponibilitaCreate,
    auth: bool = Depends(require_staff_auth),
    db: Session = Depends(get_db)
):
    """
    Crea una nuova disponibilità.

    Verifica che staff e sede esistano.
    """
    # Verifica staff
    staff = db.query(BookingStaff).filter(
        BookingStaff.id == data.staff_id,
        BookingStaff.attivo == True
    ).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff non trovato")

    # Verifica sede
    sede = db.query(BookingSede).filter(
        BookingSede.id == data.sede_id,
        BookingSede.attivo == True
    ).first()
    if not sede:
        raise HTTPException(status_code=404, detail="Sede non trovata")

    # Verifica ora_fine > ora_inizio
    if data.ora_fine <= data.ora_inizio:
        raise HTTPException(
            status_code=400,
            detail="ora_fine deve essere successiva a ora_inizio"
        )

    # Verifica sovrapposizioni
    sovrapposizione = db.query(BookingDisponibilita).filter(
        BookingDisponibilita.staff_id == data.staff_id,
        BookingDisponibilita.data == data.data,
        BookingDisponibilita.attivo == True,
        or_(
            and_(
                BookingDisponibilita.ora_inizio <= data.ora_inizio,
                BookingDisponibilita.ora_fine > data.ora_inizio
            ),
            and_(
                BookingDisponibilita.ora_inizio < data.ora_fine,
                BookingDisponibilita.ora_fine >= data.ora_fine
            ),
            and_(
                BookingDisponibilita.ora_inizio >= data.ora_inizio,
                BookingDisponibilita.ora_fine <= data.ora_fine
            )
        )
    ).first()

    if sovrapposizione:
        raise HTTPException(
            status_code=400,
            detail=f"Sovrapposizione con disponibilità esistente ({sovrapposizione.ora_inizio}-{sovrapposizione.ora_fine})"
        )

    # Crea disponibilità
    disponibilita = BookingDisponibilita(**data.model_dump())
    db.add(disponibilita)
    db.commit()
    db.refresh(disponibilita)

    return disponibilita


@router.post("/disponibilita/bulk", response_model=List[DisponibilitaResponse])
async def crea_disponibilita_bulk(
    data: DisponibilitaBulkCreate,
    auth: bool = Depends(require_staff_auth),
    db: Session = Depends(get_db)
):
    """
    Crea disponibilità per più giorni contemporaneamente.

    Utile per impostare orari settimanali.
    """
    # Verifica staff e sede
    staff = db.query(BookingStaff).get(data.staff_id)
    if not staff or not staff.attivo:
        raise HTTPException(status_code=404, detail="Staff non trovato")

    sede = db.query(BookingSede).get(data.sede_id)
    if not sede or not sede.attivo:
        raise HTTPException(status_code=404, detail="Sede non trovata")

    # Verifica orari
    if data.ora_fine <= data.ora_inizio:
        raise HTTPException(
            status_code=400,
            detail="ora_fine deve essere successiva a ora_inizio"
        )

    created = []
    for giorno in data.date_list:
        # Salta se già esiste
        existing = db.query(BookingDisponibilita).filter(
            BookingDisponibilita.staff_id == data.staff_id,
            BookingDisponibilita.data == giorno,
            BookingDisponibilita.ora_inizio == data.ora_inizio,
            BookingDisponibilita.attivo == True
        ).first()

        if existing:
            continue

        disponibilita = BookingDisponibilita(
            staff_id=data.staff_id,
            sede_id=data.sede_id,
            data=giorno,
            ora_inizio=data.ora_inizio,
            ora_fine=data.ora_fine,
            note=data.note
        )
        db.add(disponibilita)
        created.append(disponibilita)

    db.commit()
    for d in created:
        db.refresh(d)

    return created


@router.put("/disponibilita/{id}", response_model=DisponibilitaResponse)
async def aggiorna_disponibilita(
    id: int,
    data: DisponibilitaUpdate,
    auth: bool = Depends(require_staff_auth),
    db: Session = Depends(get_db)
):
    """Aggiorna una disponibilità esistente."""
    disponibilita = db.query(BookingDisponibilita).get(id)
    if not disponibilita:
        raise HTTPException(status_code=404, detail="Disponibilità non trovata")

    # Aggiorna campi
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(disponibilita, field, value)

    disponibilita.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(disponibilita)

    return disponibilita


@router.delete("/disponibilita/{id}", response_model=SuccessResponse)
async def elimina_disponibilita(
    id: int,
    auth: bool = Depends(require_staff_auth),
    db: Session = Depends(get_db)
):
    """
    Disattiva una disponibilità.

    Non elimina fisicamente per preservare storico slot generati.
    """
    disponibilita = db.query(BookingDisponibilita).get(id)
    if not disponibilita:
        raise HTTPException(status_code=404, detail="Disponibilità non trovata")

    disponibilita.attivo = False
    disponibilita.updated_at = datetime.utcnow()
    db.commit()

    return SuccessResponse(message="Disponibilità eliminata")


# ============================================================================
# CALENDARIO PRENOTAZIONI
# ============================================================================

@router.get("/calendario", response_model=List[SlotDetailResponse])
async def mio_calendario(
    staff_id: Optional[int] = Query(None, description="ID staff (temporaneo)"),
    data_da: Optional[date] = Query(None),
    data_a: Optional[date] = Query(None),
    auth: bool = Depends(require_staff_auth),
    db: Session = Depends(get_db)
):
    """
    Calendario slot dello staff (prenotati e liberi).

    Restituisce tutti gli slot assegnati allo staff nel periodo.
    """
    if not staff_id:
        raise HTTPException(
            status_code=400,
            detail="staff_id richiesto (auth non attiva)"
        )

    # Default: questa settimana
    if not data_da:
        data_da = date.today()
    if not data_a:
        data_a = data_da + timedelta(days=7)

    slots = db.query(BookingSlot).filter(
        BookingSlot.staff_id == staff_id,
        BookingSlot.data_ora_inizio >= datetime.combine(data_da, datetime.min.time()),
        BookingSlot.data_ora_inizio <= datetime.combine(data_a, datetime.max.time())
    ).order_by(BookingSlot.data_ora_inizio).all()

    return slots


@router.get("/prenotazioni", response_model=PrenotazioneListResponse)
async def mie_prenotazioni(
    staff_id: Optional[int] = Query(None, description="ID staff (temporaneo)"),
    data_da: Optional[date] = Query(None),
    data_a: Optional[date] = Query(None),
    stato: Optional[StatoPrenotazione] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    auth: bool = Depends(require_staff_auth),
    db: Session = Depends(get_db)
):
    """
    Lista prenotazioni per lo staff.

    Solo prenotazioni per slot assegnati allo staff.
    """
    if not staff_id:
        raise HTTPException(
            status_code=400,
            detail="staff_id richiesto (auth non attiva)"
        )

    # Query base: prenotazioni per slot dello staff
    query = db.query(BookingPrenotazione).join(BookingSlot).filter(
        BookingSlot.staff_id == staff_id
    )

    # Filtri
    if data_da:
        query = query.filter(BookingSlot.data_ora_inizio >= datetime.combine(data_da, datetime.min.time()))
    if data_a:
        query = query.filter(BookingSlot.data_ora_inizio <= datetime.combine(data_a, datetime.max.time()))
    if stato:
        query = query.filter(BookingPrenotazione.stato == stato)

    # Totale
    total = query.count()

    # Paginazione
    offset = (page - 1) * per_page
    prenotazioni = query.order_by(BookingSlot.data_ora_inizio).offset(offset).limit(per_page).all()

    return PrenotazioneListResponse(
        items=prenotazioni,
        total=total,
        page=page,
        per_page=per_page
    )


# ============================================================================
# GESTIONE PRENOTAZIONI
# ============================================================================

@router.put("/prenotazioni/{id}/completata", response_model=SuccessResponse)
async def marca_completata(
    id: int,
    esito: Optional[str] = Query(None, description="Note sull'esito"),
    auth: bool = Depends(require_staff_auth),
    db: Session = Depends(get_db)
):
    """
    Marca una prenotazione come completata.

    Da usare dopo che l'appuntamento è avvenuto.
    """
    prenotazione = db.query(BookingPrenotazione).get(id)
    if not prenotazione:
        raise HTTPException(status_code=404, detail="Prenotazione non trovata")

    if prenotazione.stato != StatoPrenotazione.CONFERMATA:
        raise HTTPException(
            status_code=400,
            detail="Solo prenotazioni confermate possono essere marcate come completate"
        )

    prenotazione.stato = StatoPrenotazione.COMPLETATA
    prenotazione.completato_at = datetime.utcnow()
    prenotazione.esito = esito
    prenotazione.updated_at = datetime.utcnow()

    # Log audit
    from app.models.booking import BookingAuditLog, AzioneAudit, TipoUtenteAudit
    audit = BookingAuditLog(
        prenotazione_id=prenotazione.id,
        azione=AzioneAudit.COMPLETED,
        utente_tipo=TipoUtenteAudit.STAFF,
        descrizione=f"Appuntamento completato. Esito: {esito or 'non specificato'}"
    )
    db.add(audit)

    db.commit()

    return SuccessResponse(message="Prenotazione marcata come completata")


@router.put("/prenotazioni/{id}/no-show", response_model=SuccessResponse)
async def marca_no_show(
    id: int,
    note: Optional[str] = Query(None),
    auth: bool = Depends(require_staff_auth),
    db: Session = Depends(get_db)
):
    """
    Marca una prenotazione come no-show.

    L'utente non si è presentato all'appuntamento.
    """
    prenotazione = db.query(BookingPrenotazione).get(id)
    if not prenotazione:
        raise HTTPException(status_code=404, detail="Prenotazione non trovata")

    if prenotazione.stato != StatoPrenotazione.CONFERMATA:
        raise HTTPException(
            status_code=400,
            detail="Solo prenotazioni confermate possono essere marcate come no-show"
        )

    # Verifica che l'appuntamento sia passato
    if prenotazione.slot.data_ora_inizio > datetime.now():
        raise HTTPException(
            status_code=400,
            detail="L'appuntamento non è ancora passato"
        )

    prenotazione.stato = StatoPrenotazione.NO_SHOW
    prenotazione.note_admin = note
    prenotazione.updated_at = datetime.utcnow()

    # Log audit
    from app.models.booking import BookingAuditLog, AzioneAudit, TipoUtenteAudit
    audit = BookingAuditLog(
        prenotazione_id=prenotazione.id,
        azione=AzioneAudit.NO_SHOW,
        utente_tipo=TipoUtenteAudit.STAFF,
        descrizione=f"Utente non presentato. Note: {note or 'nessuna'}"
    )
    db.add(audit)

    db.commit()

    return SuccessResponse(message="Prenotazione marcata come no-show")


@router.put("/prenotazioni/{id}/annulla", response_model=SuccessResponse)
async def annulla_prenotazione_staff(
    id: int,
    motivo: Optional[str] = Query(None),
    auth: bool = Depends(require_staff_auth),
    db: Session = Depends(get_db)
):
    """
    Annulla una prenotazione (da staff).

    Libera lo slot per altre prenotazioni.
    """
    prenotazione = db.query(BookingPrenotazione).get(id)
    if not prenotazione:
        raise HTTPException(status_code=404, detail="Prenotazione non trovata")

    if prenotazione.stato != StatoPrenotazione.CONFERMATA:
        raise HTTPException(
            status_code=400,
            detail="Prenotazione già annullata o completata"
        )

    # Annulla
    prenotazione.stato = StatoPrenotazione.ANNULLATA_UFFICIO
    prenotazione.annullato_da = "staff"
    prenotazione.annullato_at = datetime.utcnow()
    prenotazione.motivo_annullamento = motivo
    prenotazione.updated_at = datetime.utcnow()

    # Libera slot
    prenotazione.slot.stato = StatoSlot.LIBERO
    prenotazione.slot.updated_at = datetime.utcnow()

    # Log audit
    from app.models.booking import BookingAuditLog, AzioneAudit, TipoUtenteAudit
    audit = BookingAuditLog(
        prenotazione_id=prenotazione.id,
        azione=AzioneAudit.CANCELLED,
        utente_tipo=TipoUtenteAudit.STAFF,
        descrizione=f"Annullata dallo staff. Motivo: {motivo or 'non specificato'}"
    )
    db.add(audit)

    db.commit()

    # TODO: Invia notifica all'utente

    return SuccessResponse(message="Prenotazione annullata")
