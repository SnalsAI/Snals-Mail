"""
API Routes per gestione Calendario.

FASE 6: API Complete per Frontend
"""
import re
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
    stato: Optional[str] = None  # confermato, completato, annullato, rinviato
    scuola: Optional[str] = None  # codice meccanografico


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

    # Arricchisci eventi con informazioni da email associate
    from app.models.email import Email
    from app.models.interpretazione import Interpretazione

    eventi_enriched = []
    for evento in eventi:
        evento_dict = {
            "id": evento.id,
            "email_id": evento.email_id,
            "titolo": evento.titolo,
            "descrizione": evento.descrizione,
            "sintesi_motivo": evento.sintesi_motivo,  # Sintesi generata da LLM
            "data_inizio": evento.data_inizio.isoformat() if evento.data_inizio else None,
            "data_fine": evento.data_fine.isoformat() if evento.data_fine else None,
            "all_day": evento.all_day,
            "luogo": evento.luogo,
            "link_videocall": evento.link_videocall,
            "scuola": evento.scuola,
            "tipo_convocazione": evento.tipo_convocazione,
            "google_calendar_id": evento.google_calendar_id,
            "google_event_id": evento.google_event_id,
            "sincronizzato": evento.sincronizzato,
            "allegati": evento.allegati,
            "created_at": evento.created_at.isoformat() if evento.created_at else None,
            "updated_at": evento.updated_at.isoformat() if evento.updated_at else None,
        }

        # Se l'evento è associato a un'email, aggiungi informazioni aggiuntive
        if evento.email_id:
            email = db.query(Email).filter(Email.id == evento.email_id).first()
            if email:
                # Usa il riassunto/note dell'email se disponibile
                evento_dict["email_note"] = email.note

                # Aggiungi corpo testo dell'email (primi 500 caratteri)
                if email.corpo_testo:
                    evento_dict["email_corpo_testo"] = email.corpo_testo[:500] if len(email.corpo_testo) > 500 else email.corpo_testo

                # Aggiungi testo estratto dagli allegati (primi 500 caratteri per allegato)
                if email.allegati_testo and isinstance(email.allegati_testo, dict):
                    allegati_estratti = {}
                    for filename, testo in email.allegati_testo.items():
                        if testo:
                            allegati_estratti[filename] = testo[:500] if len(testo) > 500 else testo
                    if allegati_estratti:
                        evento_dict["allegati_testo"] = allegati_estratti

                # Cerca interpretazione associata per argomento e altri dati
                interpretazione = db.query(Interpretazione).filter(
                    Interpretazione.email_id == evento.email_id
                ).first()

                if interpretazione and interpretazione.interpretazione_json:
                    # Estrai dati dall'interpretazione
                    dati = interpretazione.interpretazione_json
                    if isinstance(dati, dict):
                        evento_dict["argomento"] = dati.get("argomento") or dati.get("motivo") or dati.get("oggetto_riunione")
                        evento_dict["ordine_del_giorno"] = dati.get("ordine_del_giorno")
                        evento_dict["motivazione_dettagliata"] = dati.get("motivazione") or dati.get("descrizione_dettagliata")
                        evento_dict["note_convocazione"] = dati.get("note")
                    elif isinstance(dati, str):
                        # Se è una stringa JSON, prova a parsarla
                        import json
                        try:
                            dati_parsed = json.loads(dati)
                            evento_dict["argomento"] = dati_parsed.get("argomento") or dati_parsed.get("motivo") or dati_parsed.get("oggetto_riunione")
                            evento_dict["ordine_del_giorno"] = dati_parsed.get("ordine_del_giorno")
                            evento_dict["motivazione_dettagliata"] = dati_parsed.get("motivazione") or dati_parsed.get("descrizione_dettagliata")
                            evento_dict["note_convocazione"] = dati_parsed.get("note")
                        except:
                            pass

        eventi_enriched.append(evento_dict)

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "eventi": eventi_enriched
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

    if evento_data.scuola is not None:
        evento.scuola = evento_data.scuola

    # Gestione stato con sincronizzazione Google
    stato_cambiato = False
    old_stato = evento.stato
    if evento_data.stato is not None and evento_data.stato != evento.stato:
        evento.stato = evento_data.stato
        stato_cambiato = True

    db.commit()
    db.refresh(evento)

    # Aggiorna su Google Calendar se sincronizzato
    if evento.google_event_id:
        try:
            gcal_client = GoogleCalendarClient()
            if gcal_client.authenticate():
                updates = {}

                # Gestisci titolo con prefisso stato
                titolo_base = evento.titolo or ""
                # Rimuovi prefissi esistenti
                import re
                titolo_pulito = re.sub(r'^\[(COMPLETATO|ANNULLATO|RINVIATO)\]\s*', '', titolo_base)

                if evento_data.titolo or stato_cambiato:
                    # Aggiungi prefisso in base allo stato
                    if evento.stato == 'completato':
                        updates['summary'] = f'[COMPLETATO] {titolo_pulito}'
                    elif evento.stato == 'annullato':
                        updates['summary'] = f'[ANNULLATO] {titolo_pulito}'
                    elif evento.stato == 'rinviato':
                        updates['summary'] = f'[RINVIATO] {titolo_pulito}'
                    else:
                        updates['summary'] = titolo_pulito

                if evento_data.luogo:
                    updates['location'] = evento.luogo
                if evento_data.descrizione:
                    updates['description'] = evento.descrizione

                if updates:
                    gcal_client.update_event(evento.google_event_id, updates)

        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.warning(f"Impossibile aggiornare Google Calendar: {e}")

    return {"message": "Evento aggiornato", "evento": evento}


@router.delete("/cleanup-all")
def cleanup_all_eventi(db: Session = Depends(get_db)):
    """
    Elimina TUTTI gli eventi calendario (locale e Google Calendar).

    ⚠️ ATTENZIONE: Questa operazione è irreversibile!
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        # Recupera tutti gli eventi
        eventi = db.query(EventoCalendario).all()

        if not eventi:
            return {
                "message": "Nessun evento da eliminare",
                "eventi_eliminati": 0
            }

        # Inizializza client Google Calendar
        gcal_client = GoogleCalendarClient()
        google_disponibile = gcal_client.authenticate()

        eventi_eliminati_google = 0
        eventi_eliminati_locale = 0
        errori = []

        for evento in eventi:
            # Prova a eliminare da Google Calendar se sincronizzato
            if google_disponibile and evento.sincronizzato and evento.google_event_id:
                try:
                    success = gcal_client.delete_event(evento.google_event_id)
                    if success:
                        eventi_eliminati_google += 1
                        logger.info(f"✅ Evento Google eliminato: {evento.google_event_id}")
                except Exception as e:
                    errori.append(f"Evento {evento.id}: {str(e)}")
                    logger.warning(f"⚠️ Errore eliminazione Google event {evento.google_event_id}: {e}")

            # Elimina dal database locale
            try:
                db.delete(evento)
                eventi_eliminati_locale += 1
            except Exception as e:
                errori.append(f"Evento locale {evento.id}: {str(e)}")
                logger.error(f"❌ Errore eliminazione evento locale {evento.id}: {e}")

        # Commit finale
        db.commit()

        logger.info(f"🗑️ Cleanup completato: {eventi_eliminati_locale} eventi locali, {eventi_eliminati_google} eventi Google")

        return {
            "message": "Cleanup completato",
            "eventi_eliminati_locale": eventi_eliminati_locale,
            "eventi_eliminati_google": eventi_eliminati_google,
            "errori": errori if errori else None
        }

    except Exception as e:
        logger.error(f"❌ Errore cleanup eventi: {e}")
        raise HTTPException(status_code=500, detail=f"Errore cleanup: {str(e)}")


@router.delete("/{evento_id}")
def delete_evento(evento_id: int, db: Session = Depends(get_db)):
    """Elimina evento."""
    import logging
    logger = logging.getLogger(__name__)

    evento = db.query(EventoCalendario).filter(EventoCalendario.id == evento_id).first()

    if not evento:
        raise HTTPException(status_code=404, detail="Evento non trovato")

    # Elimina da Google Calendar se sincronizzato
    if evento.sincronizzato and evento.google_event_id:
        try:
            gcal_client = GoogleCalendarClient()
            if gcal_client.authenticate():
                gcal_client.delete_event(evento.google_event_id)
        except Exception as e:
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


@router.get("/report/anomalie")
def get_anomalie_eventi(
    data_da: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Rileva anomalie negli eventi calendario.

    Anomalie rilevate:
    - stato_inconsistente: Titolo contiene [RINVIATO]/[ANNULLATO] ma stato diverso
    - evento_passato_confermato: Evento passato ancora in stato "confermato"
    - sottocategoria_errata: Evento da email non-convocazione
    - dati_incompleti: Mancano luogo o data
    """
    import re
    import logging
    from app.models.email import Email

    logger = logging.getLogger(__name__)

    # Default: controlla solo eventi futuri
    if not data_da:
        data_da_dt = datetime.now() - timedelta(days=7)  # Include anche eventi recenti
    else:
        data_da_dt = datetime.fromisoformat(data_da)

    eventi = db.query(EventoCalendario).filter(
        EventoCalendario.data_inizio >= data_da_dt
    ).all()

    anomalie = []
    now = datetime.now()

    for evento in eventi:
        titolo = evento.titolo or ""
        stato = evento.stato or "confermato"

        # 1. Stato inconsistente con titolo
        # NOTA: [POST RINVIO] indica che l'evento è stato rinviato MA ha una nuova data,
        # quindi lo stato corretto è 'confermato', non 'rinviato'
        is_post_rinvio = '[POST RINVIO]' in titolo.upper()
        if not is_post_rinvio and re.search(r'\[RINVIATO\]|\brinviato\b', titolo, re.IGNORECASE) and stato != "rinviato":
            anomalie.append({
                "tipo": "stato_inconsistente",
                "evento_id": evento.id,
                "titolo": titolo[:80],
                "dettaglio": f"Titolo indica rinvio ma stato='{stato}'",
                "azione_suggerita": "Aggiornare stato a 'rinviato'"
            })

        if re.search(r'\[ANNULLATO\]|\bannullato\b', titolo, re.IGNORECASE) and stato != "annullato":
            anomalie.append({
                "tipo": "stato_inconsistente",
                "evento_id": evento.id,
                "titolo": titolo[:80],
                "dettaglio": f"Titolo indica annullamento ma stato='{stato}'",
                "azione_suggerita": "Aggiornare stato a 'annullato'"
            })

        # 2. Evento passato ancora confermato (escludi 'completato')
        # Stati finali che non generano anomalie: completato, annullato
        if evento.data_inizio and evento.data_inizio < now and stato == "confermato":
            # Solo se passato da più di 1 giorno
            if (now - evento.data_inizio).days > 1:
                anomalie.append({
                    "tipo": "evento_passato_confermato",
                    "evento_id": evento.id,
                    "titolo": titolo[:80],
                    "dettaglio": f"Evento del {evento.data_inizio.strftime('%d/%m/%Y')} ancora confermato",
                    "azione_suggerita": "Verificare se è avvenuto o va eliminato"
                })

        # 3. Sottocategoria email non è Convocazione (o simile)
        if evento.email_id:
            email = db.query(Email).filter(Email.id == evento.email_id).first()
            if email and email.sottocategoria:
                sottocategoria = email.sottocategoria.lower()
                # Sottocategorie che possono generare eventi calendario validi
                sottocategorie_valide = [
                    'convocazione', 'rinvio',
                    'contrattazione integrativa',  # Include convocazioni tavolo contrattuale
                    'assemblea',
                    'rsu'
                ]
                if sottocategoria not in sottocategorie_valide:
                    anomalie.append({
                        "tipo": "sottocategoria_errata",
                        "evento_id": evento.id,
                        "email_id": evento.email_id,
                        "titolo": titolo[:80],
                        "dettaglio": f"Email sottocategoria '{email.sottocategoria}' non è Convocazione",
                        "azione_suggerita": "Verificare se evento è corretto"
                    })

        # 4. Dati incompleti - solo data_inizio è critica (luogo può mancare)
        if not evento.data_inizio:
            anomalie.append({
                "tipo": "dati_incompleti",
                "evento_id": evento.id,
                "titolo": titolo[:80],
                "dettaglio": "Campo mancante: data_inizio",
                "azione_suggerita": "Completare data evento"
            })

    # Raggruppa per tipo
    by_tipo = {}
    for a in anomalie:
        tipo = a["tipo"]
        if tipo not in by_tipo:
            by_tipo[tipo] = []
        by_tipo[tipo].append(a)

    return {
        "totale_anomalie": len(anomalie),
        "per_tipo": {k: len(v) for k, v in by_tipo.items()},
        "anomalie": anomalie
    }


@router.post("/report/anomalie/risolvi-auto")
def risolvi_anomalie_auto(
    db: Session = Depends(get_db)
):
    """
    Risolve automaticamente le anomalie risolvibili.

    - Eventi passati confermati → marcati come 'completato'
    - Stati inconsistenti → aggiornato lo stato in base al titolo
    - Sincronizza stato su Google Calendar
    """
    eventi = db.query(EventoCalendario).all()
    now = datetime.now()
    risolte = {"eventi_completati": 0, "stati_corretti": 0, "google_aggiornati": 0}
    eventi_da_sync = []

    for evento in eventi:
        titolo = (evento.titolo or "").upper()
        stato = evento.stato
        nuovo_stato = None

        # 1. Eventi passati confermati → completato
        if evento.data_inizio and evento.data_inizio < now and stato == "confermato":
            if (now - evento.data_inizio).days > 1:
                evento.stato = "completato"
                nuovo_stato = "completato"
                risolte["eventi_completati"] += 1

        # 2. Stato inconsistente con titolo
        if not nuovo_stato:
            is_post_rinvio = '[POST RINVIO]' in titolo
            if not is_post_rinvio:
                if re.search(r'\[RINVIATO\]|\bRINVIATO\b', titolo) and stato != "rinviato":
                    evento.stato = "rinviato"
                    nuovo_stato = "rinviato"
                    risolte["stati_corretti"] += 1
                elif re.search(r'\[ANNULLATO\]|\bANNULLATO\b', titolo) and stato != "annullato":
                    evento.stato = "annullato"
                    nuovo_stato = "annullato"
                    risolte["stati_corretti"] += 1

        # Aggiungi alla lista per sync Google
        if nuovo_stato and evento.google_event_id:
            eventi_da_sync.append((evento, nuovo_stato))

    db.commit()

    # Sincronizza su Google Calendar
    if eventi_da_sync:
        try:
            gcal_client = GoogleCalendarClient()
            if gcal_client.authenticate():
                for evento, nuovo_stato in eventi_da_sync:
                    try:
                        titolo_base = evento.titolo or ""
                        titolo_pulito = re.sub(r'^\[(COMPLETATO|ANNULLATO|RINVIATO)\]\s*', '', titolo_base)

                        if nuovo_stato == 'completato':
                            nuovo_titolo = f'[COMPLETATO] {titolo_pulito}'
                        elif nuovo_stato == 'annullato':
                            nuovo_titolo = f'[ANNULLATO] {titolo_pulito}'
                        elif nuovo_stato == 'rinviato':
                            nuovo_titolo = f'[RINVIATO] {titolo_pulito}'
                        else:
                            nuovo_titolo = titolo_pulito

                        gcal_client.update_event(evento.google_event_id, {'summary': nuovo_titolo})
                        risolte["google_aggiornati"] += 1
                    except Exception:
                        pass  # Ignora errori singoli eventi
        except Exception:
            pass  # Continua anche se Google non disponibile

    return {
        "success": True,
        "risolte": risolte,
        "totale": risolte["eventi_completati"] + risolte["stati_corretti"]
    }


@router.delete("/report/anomalie/{evento_id}")
def risolvi_anomalia_singola(
    evento_id: int,
    azione: str = "completato",
    db: Session = Depends(get_db)
):
    """
    Risolve una singola anomalia cambiando lo stato dell'evento.

    Args:
        evento_id: ID dell'evento
        azione: Nuovo stato (completato, annullato, rinviato, confermato)
    """
    evento = db.query(EventoCalendario).filter(EventoCalendario.id == evento_id).first()
    if not evento:
        raise HTTPException(status_code=404, detail="Evento non trovato")

    old_stato = evento.stato
    evento.stato = azione
    db.commit()

    return {
        "success": True,
        "evento_id": evento_id,
        "stato_precedente": old_stato,
        "nuovo_stato": azione
    }
