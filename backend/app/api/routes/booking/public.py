"""
Endpoint pubblici per il modulo Prenotazioni

Accessibili SENZA autenticazione.
Gli utenti esterni usano questi endpoint per:
- Vedere campagne e slot disponibili
- Creare prenotazioni
- Gestire prenotazioni via token (modifica/annullamento)
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional, List
from datetime import datetime, date, timedelta

from app.database import get_db
from app.models.booking import (
    BookingSede, BookingCampagna, BookingTipoAppuntamento,
    BookingSlot, BookingContatto, BookingPrenotazione,
    StatoSlot, StatoPrenotazione
)
from app.schemas.booking import (
    SedeResponse, CampagnaResponse, CampagnaDetailResponse,
    TipoAppuntamentoResponse, SlotDetailResponse, SlotDisponibiliResponse,
    PrenotazioneCreatePublic, PrenotazionePublicResponse,
    PrenotazioneAnnullaRequest, PrenotazioneSpostaRequest,
    ContattoUpdate, SuccessResponse, ErrorResponse
)
from .deps import get_client_ip, get_user_agent

router = APIRouter()


# ============================================================================
# CAMPAGNE
# ============================================================================

@router.get("/campagne", response_model=List[CampagnaResponse])
async def lista_campagne_attive(
    db: Session = Depends(get_db)
):
    """
    Lista campagne attive e nel periodo di validità.

    Restituisce solo le campagne:
    - attive
    - con data_inizio <= oggi <= data_fine
    """
    oggi = date.today()
    campagne = db.query(BookingCampagna).filter(
        BookingCampagna.attivo == True,
        BookingCampagna.data_inizio <= oggi,
        BookingCampagna.data_fine >= oggi
    ).order_by(BookingCampagna.data_fine).all()

    return campagne


@router.get("/campagne/{slug}", response_model=CampagnaDetailResponse)
async def dettaglio_campagna(
    slug: str,
    db: Session = Depends(get_db)
):
    """
    Dettaglio campagna con tipi appuntamento associati.
    """
    campagna = db.query(BookingCampagna).filter(
        BookingCampagna.slug == slug,
        BookingCampagna.attivo == True
    ).first()

    if not campagna:
        raise HTTPException(status_code=404, detail="Campagna non trovata")

    return campagna


# ============================================================================
# SEDI
# ============================================================================

@router.get("/sedi", response_model=List[SedeResponse])
async def lista_sedi_attive(
    db: Session = Depends(get_db)
):
    """Lista sedi attive per prenotazioni."""
    sedi = db.query(BookingSede).filter(
        BookingSede.attivo == True
    ).order_by(BookingSede.nome).all()

    return sedi


# ============================================================================
# TIPI APPUNTAMENTO
# ============================================================================

@router.get("/tipi-appuntamento", response_model=List[TipoAppuntamentoResponse])
async def lista_tipi_appuntamento(
    sede_id: Optional[int] = Query(None, description="Filtra per sede"),
    campagna_id: Optional[int] = Query(None, description="Filtra per campagna"),
    db: Session = Depends(get_db)
):
    """
    Lista tipi appuntamento disponibili.

    Se specificato campagna_id, restituisce solo i tipi associati a quella campagna.
    """
    query = db.query(BookingTipoAppuntamento).filter(
        BookingTipoAppuntamento.attivo == True
    )

    if campagna_id:
        campagna = db.query(BookingCampagna).get(campagna_id)
        if campagna:
            tipo_ids = [t.id for t in campagna.tipi_appuntamento]
            query = query.filter(BookingTipoAppuntamento.id.in_(tipo_ids))

    return query.order_by(BookingTipoAppuntamento.ordine).all()


# ============================================================================
# SLOT DISPONIBILI
# ============================================================================

@router.get("/slots/disponibili", response_model=SlotDisponibiliResponse)
async def lista_slot_disponibili(
    sede_id: Optional[int] = Query(None),
    tipo_appuntamento_id: Optional[int] = Query(None),
    campagna_id: Optional[int] = Query(None),
    data_da: Optional[date] = Query(None, description="Default: oggi"),
    data_a: Optional[date] = Query(None, description="Default: +30 giorni"),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db)
):
    """
    Lista slot disponibili per prenotazione.

    Filtra per sede, tipo appuntamento, e range date.
    Restituisce solo slot LIBERI e futuri.
    """
    # Default date range
    if not data_da:
        data_da = date.today()
    if not data_a:
        data_a = data_da + timedelta(days=30)

    # Query base: slot liberi e futuri
    query = db.query(BookingSlot).filter(
        BookingSlot.stato == StatoSlot.LIBERO,
        BookingSlot.data_ora_inizio >= datetime.now(),
        BookingSlot.data_ora_inizio >= datetime.combine(data_da, datetime.min.time()),
        BookingSlot.data_ora_inizio <= datetime.combine(data_a, datetime.max.time())
    )

    # Filtri opzionali
    if sede_id:
        query = query.filter(BookingSlot.sede_id == sede_id)

    if tipo_appuntamento_id:
        query = query.filter(BookingSlot.tipo_appuntamento_id == tipo_appuntamento_id)

    if campagna_id:
        # Filtra per tipi appuntamento della campagna
        campagna = db.query(BookingCampagna).get(campagna_id)
        if campagna:
            tipo_ids = [t.id for t in campagna.tipi_appuntamento]
            query = query.filter(BookingSlot.tipo_appuntamento_id.in_(tipo_ids))

    # Ordina e limita
    slots = query.order_by(BookingSlot.data_ora_inizio).limit(limit).all()

    return SlotDisponibiliResponse(
        items=slots,
        total=len(slots)
    )


# ============================================================================
# PRENOTAZIONE
# ============================================================================

@router.post("/prenotazioni", response_model=PrenotazionePublicResponse)
async def crea_prenotazione(
    data: PrenotazioneCreatePublic,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Crea una nuova prenotazione.

    1. Verifica slot disponibile
    2. Crea o aggiorna contatto
    3. Crea prenotazione con token univoco
    4. Marca slot come prenotato
    5. (TODO) Schedula notifiche email
    """
    # 1. Verifica slot
    slot = db.query(BookingSlot).filter(
        BookingSlot.id == data.slot_id,
        BookingSlot.stato == StatoSlot.LIBERO
    ).first()

    if not slot:
        raise HTTPException(
            status_code=400,
            detail="Slot non disponibile o già prenotato"
        )

    # Verifica slot futuro
    if slot.data_ora_inizio <= datetime.now():
        raise HTTPException(
            status_code=400,
            detail="Non è possibile prenotare slot passati"
        )

    # 2. Verifica consenso privacy
    if not data.contatto.consenso_privacy:
        raise HTTPException(
            status_code=400,
            detail="È necessario accettare l'informativa privacy"
        )

    # 3. Crea o aggiorna contatto
    contatto = db.query(BookingContatto).filter(
        BookingContatto.email == data.contatto.email.lower()
    ).first()

    if contatto:
        # Aggiorna dati esistenti
        for field, value in data.contatto.model_dump(exclude_unset=True).items():
            if value is not None and field != 'email':
                setattr(contatto, field, value)
        contatto.updated_at = datetime.utcnow()
    else:
        # Crea nuovo contatto
        contatto = BookingContatto(
            **data.contatto.model_dump(),
            email=data.contatto.email.lower(),
            privacy_version="2025.1",  # TODO: da config
            data_consenso=datetime.utcnow()
        )
        db.add(contatto)
        db.flush()

    # 4. Crea prenotazione
    prenotazione = BookingPrenotazione(
        contatto_id=contatto.id,
        slot_id=slot.id,
        campagna_id=data.campagna_id,
        note_utente=data.note_utente,
        stato=StatoPrenotazione.CONFERMATA,
        data_conferma=datetime.utcnow()
    )
    db.add(prenotazione)

    # 5. Marca slot come prenotato
    slot.stato = StatoSlot.PRENOTATO
    slot.updated_at = datetime.utcnow()

    # 6. Log audit
    from app.models.booking import BookingAuditLog, AzioneAudit, TipoUtenteAudit
    audit = BookingAuditLog(
        prenotazione_id=None,  # Sarà aggiornato dopo flush
        azione=AzioneAudit.CREATED,
        utente_tipo=TipoUtenteAudit.ESTERNO,
        utente_email=contatto.email,
        descrizione=f"Prenotazione creata per {slot.data_ora_inizio.strftime('%d/%m/%Y %H:%M')}",
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request)
    )
    db.add(audit)

    db.commit()
    db.refresh(prenotazione)

    # Aggiorna audit con prenotazione_id
    audit.prenotazione_id = prenotazione.id
    db.commit()

    # TODO: Schedula notifica conferma via Celery
    # from app.tasks.booking_tasks import invia_notifica_conferma
    # invia_notifica_conferma.delay(prenotazione.id)

    # Costruisci response pubblica
    return PrenotazionePublicResponse(
        id=prenotazione.id,
        token_pubblico=prenotazione.token_pubblico,
        stato=prenotazione.stato,
        note_utente=prenotazione.note_utente,
        data_conferma=prenotazione.data_conferma,
        data_ora=slot.data_ora_inizio,
        durata_minuti=slot.durata_minuti,
        sede_nome=slot.sede.nome if slot.sede else None,
        sede_indirizzo=slot.sede.indirizzo if slot.sede else None,
        tipo_appuntamento=slot.tipo_appuntamento.nome if slot.tipo_appuntamento else None,
        istruzioni=slot.tipo_appuntamento.istruzioni if slot.tipo_appuntamento else None,
        link_modifica=f"/prenotazioni/{prenotazione.token_pubblico}",
        link_annulla=f"/prenotazioni/{prenotazione.token_pubblico}/annulla"
    )


@router.get("/prenotazioni/{token}", response_model=PrenotazionePublicResponse)
async def dettaglio_prenotazione_pubblica(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Dettaglio prenotazione via token pubblico.

    Usato dall'utente per vedere i dettagli della propria prenotazione.
    """
    prenotazione = db.query(BookingPrenotazione).filter(
        BookingPrenotazione.token_pubblico == token
    ).first()

    if not prenotazione:
        raise HTTPException(status_code=404, detail="Prenotazione non trovata")

    slot = prenotazione.slot
    return PrenotazionePublicResponse(
        id=prenotazione.id,
        token_pubblico=prenotazione.token_pubblico,
        stato=prenotazione.stato,
        note_utente=prenotazione.note_utente,
        data_conferma=prenotazione.data_conferma,
        data_ora=slot.data_ora_inizio if slot else None,
        durata_minuti=slot.durata_minuti if slot else None,
        sede_nome=slot.sede.nome if slot and slot.sede else None,
        sede_indirizzo=slot.sede.indirizzo if slot and slot.sede else None,
        tipo_appuntamento=slot.tipo_appuntamento.nome if slot and slot.tipo_appuntamento else None,
        istruzioni=slot.tipo_appuntamento.istruzioni if slot and slot.tipo_appuntamento else None,
        link_modifica=f"/prenotazioni/{prenotazione.token_pubblico}",
        link_annulla=f"/prenotazioni/{prenotazione.token_pubblico}/annulla"
    )


@router.put("/prenotazioni/{token}", response_model=PrenotazionePublicResponse)
async def aggiorna_prenotazione_pubblica(
    token: str,
    data: ContattoUpdate,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Aggiorna dati contatto di una prenotazione.

    L'utente può aggiornare i propri dati (telefono, ecc.)
    ma NON l'email (chiave identificativa).
    """
    prenotazione = db.query(BookingPrenotazione).filter(
        BookingPrenotazione.token_pubblico == token
    ).first()

    if not prenotazione:
        raise HTTPException(status_code=404, detail="Prenotazione non trovata")

    # Verifica stato modificabile
    if prenotazione.stato not in [StatoPrenotazione.CONFERMATA]:
        raise HTTPException(
            status_code=400,
            detail="Prenotazione non modificabile (già annullata o completata)"
        )

    # Verifica tempo minimo (TODO: leggere da config)
    ore_minime = 24
    if prenotazione.slot.data_ora_inizio <= datetime.now() + timedelta(hours=ore_minime):
        raise HTTPException(
            status_code=400,
            detail=f"Non è possibile modificare prenotazioni a meno di {ore_minime} ore dall'appuntamento"
        )

    # Aggiorna contatto
    contatto = prenotazione.contatto
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(contatto, field, value)
    contatto.updated_at = datetime.utcnow()

    # Log audit
    from app.models.booking import BookingAuditLog, AzioneAudit, TipoUtenteAudit
    audit = BookingAuditLog(
        prenotazione_id=prenotazione.id,
        azione=AzioneAudit.MODIFIED,
        utente_tipo=TipoUtenteAudit.ESTERNO,
        utente_email=contatto.email,
        descrizione="Dati contatto aggiornati",
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request)
    )
    db.add(audit)

    db.commit()
    db.refresh(prenotazione)

    slot = prenotazione.slot
    return PrenotazionePublicResponse(
        id=prenotazione.id,
        token_pubblico=prenotazione.token_pubblico,
        stato=prenotazione.stato,
        note_utente=prenotazione.note_utente,
        data_conferma=prenotazione.data_conferma,
        data_ora=slot.data_ora_inizio,
        durata_minuti=slot.durata_minuti,
        sede_nome=slot.sede.nome if slot.sede else None,
        sede_indirizzo=slot.sede.indirizzo if slot.sede else None,
        tipo_appuntamento=slot.tipo_appuntamento.nome if slot.tipo_appuntamento else None,
        istruzioni=slot.tipo_appuntamento.istruzioni if slot.tipo_appuntamento else None,
        link_modifica=f"/prenotazioni/{prenotazione.token_pubblico}",
        link_annulla=f"/prenotazioni/{prenotazione.token_pubblico}/annulla"
    )


@router.delete("/prenotazioni/{token}", response_model=SuccessResponse)
async def annulla_prenotazione_pubblica(
    token: str,
    data: Optional[PrenotazioneAnnullaRequest] = None,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Annulla una prenotazione.

    Libera lo slot per altre prenotazioni.
    """
    prenotazione = db.query(BookingPrenotazione).filter(
        BookingPrenotazione.token_pubblico == token
    ).first()

    if not prenotazione:
        raise HTTPException(status_code=404, detail="Prenotazione non trovata")

    # Verifica stato annullabile
    if prenotazione.stato != StatoPrenotazione.CONFERMATA:
        raise HTTPException(
            status_code=400,
            detail="Prenotazione già annullata o completata"
        )

    # Verifica tempo minimo
    ore_minime = 24  # TODO: da config
    if prenotazione.slot.data_ora_inizio <= datetime.now() + timedelta(hours=ore_minime):
        raise HTTPException(
            status_code=400,
            detail=f"Non è possibile annullare prenotazioni a meno di {ore_minime} ore dall'appuntamento. Contattare la segreteria."
        )

    # Annulla prenotazione
    prenotazione.stato = StatoPrenotazione.ANNULLATA_UTENTE
    prenotazione.annullato_da = "utente"
    prenotazione.annullato_at = datetime.utcnow()
    prenotazione.motivo_annullamento = data.motivo if data else None
    prenotazione.updated_at = datetime.utcnow()

    # Libera slot
    slot = prenotazione.slot
    slot.stato = StatoSlot.LIBERO
    slot.updated_at = datetime.utcnow()

    # Log audit
    from app.models.booking import BookingAuditLog, AzioneAudit, TipoUtenteAudit
    audit = BookingAuditLog(
        prenotazione_id=prenotazione.id,
        azione=AzioneAudit.CANCELLED,
        utente_tipo=TipoUtenteAudit.ESTERNO,
        utente_email=prenotazione.contatto.email,
        descrizione=f"Prenotazione annullata dall'utente. Motivo: {data.motivo if data else 'non specificato'}",
        ip_address=get_client_ip(request) if request else None,
        user_agent=get_user_agent(request) if request else None
    )
    db.add(audit)

    db.commit()

    # TODO: Invia notifica annullamento

    return SuccessResponse(
        success=True,
        message="Prenotazione annullata con successo"
    )


@router.post("/prenotazioni/{token}/sposta", response_model=PrenotazionePublicResponse)
async def sposta_prenotazione_pubblica(
    token: str,
    data: PrenotazioneSpostaRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Sposta una prenotazione su un altro slot.

    1. Verifica prenotazione esistente e modificabile
    2. Verifica nuovo slot disponibile
    3. Libera vecchio slot
    4. Assegna nuovo slot
    """
    prenotazione = db.query(BookingPrenotazione).filter(
        BookingPrenotazione.token_pubblico == token
    ).first()

    if not prenotazione:
        raise HTTPException(status_code=404, detail="Prenotazione non trovata")

    # Verifica stato
    if prenotazione.stato != StatoPrenotazione.CONFERMATA:
        raise HTTPException(
            status_code=400,
            detail="Solo prenotazioni confermate possono essere spostate"
        )

    # Verifica tempo minimo
    ore_minime = 24  # TODO: da config
    if prenotazione.slot.data_ora_inizio <= datetime.now() + timedelta(hours=ore_minime):
        raise HTTPException(
            status_code=400,
            detail=f"Non è possibile spostare prenotazioni a meno di {ore_minime} ore dall'appuntamento"
        )

    # Verifica nuovo slot
    nuovo_slot = db.query(BookingSlot).filter(
        BookingSlot.id == data.nuovo_slot_id,
        BookingSlot.stato == StatoSlot.LIBERO
    ).first()

    if not nuovo_slot:
        raise HTTPException(
            status_code=400,
            detail="Nuovo slot non disponibile"
        )

    if nuovo_slot.data_ora_inizio <= datetime.now():
        raise HTTPException(
            status_code=400,
            detail="Non è possibile prenotare slot passati"
        )

    # Verifica stesso tipo appuntamento
    if nuovo_slot.tipo_appuntamento_id != prenotazione.slot.tipo_appuntamento_id:
        raise HTTPException(
            status_code=400,
            detail="Il nuovo slot deve essere dello stesso tipo di appuntamento"
        )

    # Salva riferimento vecchio slot
    vecchio_slot = prenotazione.slot
    vecchio_slot_id = vecchio_slot.id

    # Libera vecchio slot
    vecchio_slot.stato = StatoSlot.LIBERO
    vecchio_slot.updated_at = datetime.utcnow()

    # Assegna nuovo slot
    prenotazione.slot_precedente_id = vecchio_slot_id
    prenotazione.slot_id = nuovo_slot.id
    prenotazione.spostato_at = datetime.utcnow()
    prenotazione.updated_at = datetime.utcnow()

    # Occupa nuovo slot
    nuovo_slot.stato = StatoSlot.PRENOTATO
    nuovo_slot.updated_at = datetime.utcnow()

    # Log audit
    from app.models.booking import BookingAuditLog, AzioneAudit, TipoUtenteAudit
    audit = BookingAuditLog(
        prenotazione_id=prenotazione.id,
        azione=AzioneAudit.RESCHEDULED,
        utente_tipo=TipoUtenteAudit.ESTERNO,
        utente_email=prenotazione.contatto.email,
        descrizione=f"Prenotazione spostata da {vecchio_slot.data_ora_inizio.strftime('%d/%m/%Y %H:%M')} a {nuovo_slot.data_ora_inizio.strftime('%d/%m/%Y %H:%M')}",
        dati_precedenti={"slot_id": vecchio_slot_id},
        dati_nuovi={"slot_id": nuovo_slot.id},
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request)
    )
    db.add(audit)

    db.commit()
    db.refresh(prenotazione)

    # TODO: Invia notifica spostamento

    return PrenotazionePublicResponse(
        id=prenotazione.id,
        token_pubblico=prenotazione.token_pubblico,
        stato=prenotazione.stato,
        note_utente=prenotazione.note_utente,
        data_conferma=prenotazione.data_conferma,
        data_ora=nuovo_slot.data_ora_inizio,
        durata_minuti=nuovo_slot.durata_minuti,
        sede_nome=nuovo_slot.sede.nome if nuovo_slot.sede else None,
        sede_indirizzo=nuovo_slot.sede.indirizzo if nuovo_slot.sede else None,
        tipo_appuntamento=nuovo_slot.tipo_appuntamento.nome if nuovo_slot.tipo_appuntamento else None,
        istruzioni=nuovo_slot.tipo_appuntamento.istruzioni if nuovo_slot.tipo_appuntamento else None,
        link_modifica=f"/prenotazioni/{prenotazione.token_pubblico}",
        link_annulla=f"/prenotazioni/{prenotazione.token_pubblico}/annulla"
    )
