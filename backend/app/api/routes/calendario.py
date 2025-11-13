"""
API Routes per gestione Calendario.

FASE 6: API Complete per Frontend
"""
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models.evento import EventoCalendario
from app.integrations.google_calendar_client import GoogleCalendarClient

router = APIRouter(prefix="/calendario", tags=["calendario"])


class EventoCreate(BaseModel):
    """Schema creazione evento."""
    titolo: str
    data_inizio: str
    data_fine: Optional[str] = None
    luogo: Optional[str] = None
    descrizione: Optional[str] = None
    partecipanti: Optional[List[str]] = None
    email_id: Optional[int] = None


class EventoUpdate(BaseModel):
    """Schema aggiornamento evento."""
    titolo: Optional[str] = None
    data_inizio: Optional[str] = None
    data_fine: Optional[str] = None
    luogo: Optional[str] = None
    descrizione: Optional[str] = None
    partecipanti: Optional[List[str]] = None


@router.get("/")
def list_eventi(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    data_da: Optional[str] = None,
    data_a: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Lista eventi calendario.

    - **skip**: Numero eventi da saltare
    - **limit**: Numero massimo eventi da restituire
    - **data_da**: Filtra da data (YYYY-MM-DD)
    - **data_a**: Filtra fino a data (YYYY-MM-DD)
    """
    query = db.query(EventoCalendario)

    # Filtri data
    if data_da:
        try:
            data_da_dt = datetime.fromisoformat(data_da)
            query = query.filter(EventoCalendario.data_inizio >= data_da_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato data_da non valido")

    if data_a:
        try:
            data_a_dt = datetime.fromisoformat(data_a)
            query = query.filter(EventoCalendario.data_inizio <= data_a_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato data_a non valido")

    total = query.count()
    eventi = query.order_by(EventoCalendario.data_inizio).offset(skip).limit(limit).all()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "eventi": eventi
    }


@router.get("/{evento_id}")
def get_evento(evento_id: int, db: Session = Depends(get_db)):
    """Recupera dettagli evento singolo."""
    evento = db.query(EventoCalendario).filter(EventoCalendario.id == evento_id).first()

    if not evento:
        raise HTTPException(status_code=404, detail="Evento non trovato")

    return evento


@router.post("/")
def create_evento(evento_data: EventoCreate, db: Session = Depends(get_db)):
    """
    Crea nuovo evento locale e opzionalmente su Google Calendar.

    Esempio body:
    ```json
    {
      "titolo": "Riunione RSU",
      "data_inizio": "2025-01-15T10:00:00",
      "data_fine": "2025-01-15T12:00:00",
      "luogo": "Sede SNALS",
      "descrizione": "Discussione contrattazione",
      "partecipanti": ["utente@example.com"],
      "email_id": 123
    }
    ```
    """
    # Crea evento locale
    evento = EventoCalendario(
        titolo=evento_data.titolo,
        data_inizio=datetime.fromisoformat(evento_data.data_inizio),
        data_fine=datetime.fromisoformat(evento_data.data_fine) if evento_data.data_fine else None,
        luogo=evento_data.luogo,
        descrizione=evento_data.descrizione,
        partecipanti=evento_data.partecipanti,
        email_id=evento_data.email_id,
        sincronizzato_google=False
    )

    db.add(evento)
    db.commit()
    db.refresh(evento)

    # Prova a sincronizzare con Google Calendar
    try:
        gcal_client = GoogleCalendarClient()

        if gcal_client.authenticate():
            gcal_event = gcal_client.create_event(
                summary=evento.titolo,
                start_datetime=evento.data_inizio.isoformat(),
                end_datetime=evento.data_fine.isoformat() if evento.data_fine else None,
                location=evento.luogo,
                description=evento.descrizione,
                attendees=evento.partecipanti
            )

            if gcal_event:
                evento.google_event_id = gcal_event['id']
                evento.sincronizzato_google = True
                db.commit()

    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.warning(f"Impossibile sincronizzare con Google Calendar: {e}")

    return {"message": "Evento creato", "evento": evento}


@router.put("/{evento_id}")
def update_evento(
    evento_id: int,
    evento_data: EventoUpdate,
    db: Session = Depends(get_db)
):
    """Aggiorna evento esistente."""
    evento = db.query(EventoCalendario).filter(EventoCalendario.id == evento_id).first()

    if not evento:
        raise HTTPException(status_code=404, detail="Evento non trovato")

    # Applica aggiornamenti
    if evento_data.titolo is not None:
        evento.titolo = evento_data.titolo

    if evento_data.data_inizio is not None:
        evento.data_inizio = datetime.fromisoformat(evento_data.data_inizio)

    if evento_data.data_fine is not None:
        evento.data_fine = datetime.fromisoformat(evento_data.data_fine)

    if evento_data.luogo is not None:
        evento.luogo = evento_data.luogo

    if evento_data.descrizione is not None:
        evento.descrizione = evento_data.descrizione

    if evento_data.partecipanti is not None:
        evento.partecipanti = evento_data.partecipanti

    db.commit()
    db.refresh(evento)

    # Aggiorna su Google Calendar se sincronizzato
    if evento.sincronizzato_google and evento.google_event_id:
        try:
            gcal_client = GoogleCalendarClient()
            if gcal_client.authenticate():
                updates = {}
                if evento_data.titolo:
                    updates['summary'] = evento.titolo
                if evento_data.luogo:
                    updates['location'] = evento.luogo
                if evento_data.descrizione:
                    updates['description'] = evento.descrizione

                gcal_client.update_event(evento.google_event_id, updates)

        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.warning(f"Impossibile aggiornare Google Calendar: {e}")

    return {"message": "Evento aggiornato", "evento": evento}


@router.delete("/{evento_id}")
def delete_evento(evento_id: int, db: Session = Depends(get_db)):
    """Elimina evento."""
    evento = db.query(EventoCalendario).filter(EventoCalendario.id == evento_id).first()

    if not evento:
        raise HTTPException(status_code=404, detail="Evento non trovato")

    # Elimina da Google Calendar se sincronizzato
    if evento.sincronizzato_google and evento.google_event_id:
        try:
            gcal_client = GoogleCalendarClient()
            if gcal_client.authenticate():
                gcal_client.delete_event(evento.google_event_id)
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.warning(f"Impossibile eliminare da Google Calendar: {e}")

    db.delete(evento)
    db.commit()

    return {"message": "Evento eliminato"}


@router.post("/sync-google")
def sync_google_calendar(
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Sincronizza eventi da Google Calendar.

    Importa eventi recenti da Google Calendar al database locale.
    """
    gcal_client = GoogleCalendarClient()

    if not gcal_client.authenticate():
        raise HTTPException(status_code=503, detail="Autenticazione Google Calendar fallita")

    try:
        # Recupera eventi da Google
        time_min = datetime.now() - timedelta(days=7)
        gcal_events = gcal_client.list_events(max_results=limit, time_min=time_min)

        imported = 0

        for gcal_event in gcal_events:
            # Verifica se evento già esiste
            existing = db.query(EventoCalendario).filter(
                EventoCalendario.google_event_id == gcal_event['id']
            ).first()

            if existing:
                continue

            # Estrai date
            start = gcal_event['start'].get('dateTime', gcal_event['start'].get('date'))
            end = gcal_event['end'].get('dateTime', gcal_event['end'].get('date'))

            # Crea evento locale
            evento = EventoCalendario(
                titolo=gcal_event.get('summary', 'Senza titolo'),
                data_inizio=datetime.fromisoformat(start.replace('Z', '+00:00')),
                data_fine=datetime.fromisoformat(end.replace('Z', '+00:00')) if end else None,
                luogo=gcal_event.get('location'),
                descrizione=gcal_event.get('description'),
                partecipanti=[a['email'] for a in gcal_event.get('attendees', [])],
                google_event_id=gcal_event['id'],
                sincronizzato_google=True
            )

            db.add(evento)
            imported += 1

        db.commit()

        return {
            "message": "Sincronizzazione completata",
            "eventi_importati": imported,
            "eventi_totali_google": len(gcal_events)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore sincronizzazione: {str(e)}")


import logging
