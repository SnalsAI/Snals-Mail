"""
Endpoint pubblici per il modulo Prenotazioni

Accessibili SENZA autenticazione.
Gli utenti esterni usano questi endpoint per:
- Vedere servizi e slot disponibili
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
    BookingSede, BookingServizio, BookingTipoAppuntamento,
    BookingSlot, BookingContatto, BookingPrenotazione,
    StatoSlot, StatoPrenotazione
)
from app.schemas.booking import (
    SedeResponse, ServizioResponse, ServizioDetailResponse,
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

@router.get("/servizi", response_model=List[ServizioResponse])
async def lista_servizi_attive(
    db: Session = Depends(get_db)
):
    """
    Lista servizi attive e nel periodo di validità.

    Restituisce solo le servizi:
    - attive
    - con data_inizio <= oggi <= data_fine
    """
    oggi = date.today()
    servizi = db.query(BookingServizio).filter(
        BookingServizio.attivo == True,
        BookingServizio.data_inizio <= oggi,
        BookingServizio.data_fine >= oggi
    ).order_by(BookingServizio.data_fine).all()

    return servizi


@router.get("/servizi/{slug}", response_model=ServizioDetailResponse)
async def dettaglio_servizio(
    slug: str,
    db: Session = Depends(get_db)
):
    """
    Dettaglio servizio con tipi appuntamento associati.
    """
    servizio = db.query(BookingServizio).filter(
        BookingServizio.slug == slug,
        BookingServizio.attivo == True
    ).first()

    if not servizio:
        raise HTTPException(status_code=404, detail="Servizio non trovata")

    return servizio


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
    servizio_id: Optional[int] = Query(None, description="Filtra per servizio"),
    db: Session = Depends(get_db)
):
    """
    Lista tipi appuntamento disponibili.

    Se specificato servizio_id, restituisce solo i tipi associati a quella servizio.
    """
    query = db.query(BookingTipoAppuntamento).filter(
        BookingTipoAppuntamento.attivo == True
    )

    if servizio_id:
        servizio = db.query(BookingServizio).get(servizio_id)
        if servizio:
            tipo_ids = [t.id for t in servizio.tipi_appuntamento]
            query = query.filter(BookingTipoAppuntamento.id.in_(tipo_ids))

    return query.order_by(BookingTipoAppuntamento.ordine).all()


# ============================================================================
# SLOT DISPONIBILI
# ============================================================================

@router.get("/slots/disponibili", response_model=SlotDisponibiliResponse)
async def lista_slot_disponibili(
    sede_id: Optional[int] = Query(None),
    tipo_appuntamento_id: Optional[int] = Query(None),
    servizio_id: Optional[int] = Query(None),
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

    if servizio_id:
        # Filtra per tipi appuntamento della servizio
        servizio = db.query(BookingServizio).get(servizio_id)
        if servizio:
            tipo_ids = [t.id for t in servizio.tipi_appuntamento]
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
        contatto_data = data.contatto.model_dump(exclude={'email'})
        contatto = BookingContatto(
            **contatto_data,
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
        servizio_id=data.servizio_id,
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

    # Invia email di conferma
    try:
        from app.services.booking.email_service import invia_email_conferma_prenotazione
        invia_email_conferma_prenotazione(
            destinatario=contatto.email,
            nome=contatto.nome,
            cognome=contatto.cognome,
            data_ora=slot.data_ora_inizio,
            sede_nome=slot.sede.nome if slot.sede else "Da definire",
            sede_indirizzo=slot.sede.indirizzo if slot.sede else None,
            tipo_appuntamento=slot.tipo_appuntamento.nome if slot.tipo_appuntamento else "Appuntamento",
            token=prenotazione.token_pubblico,
            istruzioni=slot.tipo_appuntamento.istruzioni if slot.tipo_appuntamento else None
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Errore invio email conferma: {e}")

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


# ============================================================================
# SCUOLE (per selezione nel form di prenotazione)
# ============================================================================

from app.models.booking import Scuola
from pydantic import BaseModel

class ScuolaResponse(BaseModel):
    id: int
    nome: str
    codice_meccanografico: Optional[str] = None
    tipo: Optional[str] = None
    ordine: Optional[str] = None
    comune: str
    provincia: Optional[str] = None
    indirizzo: Optional[str] = None

    class Config:
        from_attributes = True


@router.get("/scuole/comuni", response_model=List[str])
async def lista_comuni(
    provincia: Optional[str] = Query(None, description="Filtra per provincia (sigla, es. RM)"),
    db: Session = Depends(get_db)
):
    """
    Lista comuni con scuole.

    Restituisce la lista unica dei comuni dove ci sono scuole.
    Opzionalmente filtrabile per provincia.
    """
    query = db.query(Scuola.comune).filter(Scuola.attivo == True)

    if provincia:
        query = query.filter(Scuola.provincia == provincia.upper())

    comuni = query.distinct().order_by(Scuola.comune).all()
    return [c[0] for c in comuni]


@router.get("/scuole/province", response_model=List[str])
async def lista_province(
    db: Session = Depends(get_db)
):
    """
    Lista province con scuole.

    Restituisce la lista unica delle sigle province dove ci sono scuole.
    """
    province = db.query(Scuola.provincia).filter(
        Scuola.attivo == True,
        Scuola.provincia != None
    ).distinct().order_by(Scuola.provincia).all()
    return [p[0] for p in province if p[0]]


@router.get("/scuole", response_model=List[ScuolaResponse])
async def lista_scuole(
    comune: Optional[str] = Query(None, description="Filtra per comune"),
    provincia: Optional[str] = Query(None, description="Filtra per provincia (sigla)"),
    search: Optional[str] = Query(None, description="Ricerca nel nome"),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db)
):
    """
    Lista scuole con filtri.

    Filtri disponibili:
    - comune: nome esatto del comune
    - provincia: sigla provincia
    - search: ricerca parziale nel nome
    """
    query = db.query(Scuola).filter(Scuola.attivo == True)

    if comune:
        query = query.filter(Scuola.comune.ilike(comune))

    if provincia:
        query = query.filter(Scuola.provincia == provincia.upper())

    if search:
        query = query.filter(Scuola.nome.ilike(f"%{search}%"))

    scuole = query.order_by(Scuola.nome).limit(limit).all()
    return scuole


@router.get("/scuole/{scuola_id}", response_model=ScuolaResponse)
async def dettaglio_scuola(
    scuola_id: int,
    db: Session = Depends(get_db)
):
    """
    Dettaglio singola scuola.
    """
    scuola = db.query(Scuola).filter(
        Scuola.id == scuola_id,
        Scuola.attivo == True
    ).first()

    if not scuola:
        raise HTTPException(status_code=404, detail="Scuola non trovata")

    return scuola
