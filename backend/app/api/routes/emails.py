"""
API Routes per gestione Email.

FASE 6: API Complete per Frontend
"""
from typing import List, Optional
import logging
import asyncio
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, or_
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

from app.database import get_db
from app.models.email import Email, EmailCategory, EmailStatus
from app.schemas.email import EmailResponse, EmailListResponse, EmailUpdateRequest
from app.tasks.email_polling import poll_email_normal, poll_email_pec
from app.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/emails", tags=["emails"])

# Channel Redis per notifiche nuove email
EMAIL_NOTIFICATION_CHANNEL = "email_notifications"


async def email_event_generator():
    """Generatore SSE per notifiche nuove email."""
    redis_url = settings.REDIS_URL.replace("localhost", "redis")
    redis_client = await aioredis.from_url(redis_url)
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(EMAIL_NOTIFICATION_CHANNEL)

    try:
        # Invia messaggio iniziale di connessione
        yield f"data: {json.dumps({'type': 'connected'})}\n\n"

        last_heartbeat = asyncio.get_event_loop().time()
        heartbeat_interval = 30.0  # secondi

        while True:
            # Aspetta messaggi con timeout breve per poter inviare heartbeat
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)

            if message:
                data = message.get('data')
                if isinstance(data, bytes):
                    data = data.decode('utf-8')
                yield f"data: {data}\n\n"

            # Invia heartbeat ogni 30 secondi
            current_time = asyncio.get_event_loop().time()
            if current_time - last_heartbeat >= heartbeat_interval:
                yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
                last_heartbeat = current_time

    except asyncio.CancelledError:
        pass
    finally:
        await pubsub.unsubscribe(EMAIL_NOTIFICATION_CHANNEL)
        await redis_client.close()


@router.get("/stream")
async def email_stream():
    """
    SSE endpoint per ricevere notifiche in tempo reale quando arrivano nuove email.

    Il frontend può ascoltare questo endpoint per fare auto-refresh.
    """
    return StreamingResponse(
        email_event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/", response_model=EmailListResponse)
def list_emails(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    categoria: Optional[str] = None,
    stato: Optional[str] = None,
    account_type: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Lista email con filtri e paginazione.

    - **skip**: Numero email da saltare (paginazione)
    - **limit**: Numero massimo email da restituire
    - **categoria**: Filtra per categoria
    - **stato**: Filtra per stato
    - **account_type**: Filtra per tipo account (normal/pec)
    - **search**: Cerca in mittente, oggetto, corpo
    """
    query = db.query(Email).options(joinedload(Email.azioni))

    # Applica filtri
    if categoria:
        # Categoria è ora String nel database, non più Enum
        query = query.filter(Email.categoria == categoria)

    if stato:
        try:
            stato_enum = EmailStatus(stato)
            query = query.filter(Email.stato == stato_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Stato non valido: {stato}")

    if account_type:
        query = query.filter(Email.account_type == account_type)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Email.mittente.ilike(search_term),
                Email.oggetto.ilike(search_term),
                Email.corpo_testo.ilike(search_term)
            )
        )

    # Conta totale
    total = query.count()

    # Paginazione e ordine
    emails = query.order_by(desc(Email.data_ricezione)).offset(skip).limit(limit).all()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "emails": [email.to_dict() for email in emails]
    }


@router.post("/fetch")
def fetch_emails_manual():
    """
    Scarica manualmente email dagli account POP3.

    Triggera immediatamente il polling di entrambi gli account (normale e PEC)
    e ritorna il numero di email scaricate.
    """
    import logging

    logger = logging.getLogger(__name__)

    try:
        # Triggera i task di polling in modo sincrono (non tramite Celery)
        logger.info("🔄 Polling manuale email normale...")
        normal_result = poll_email_normal()

        logger.info("🔄 Polling manuale email PEC...")
        pec_result = poll_email_pec()

        # Conta email nuove
        normal_new = normal_result.get("new", 0) if isinstance(normal_result, dict) else 0
        normal_total = normal_result.get("total", 0) if isinstance(normal_result, dict) else 0
        pec_new = pec_result.get("new", 0) if isinstance(pec_result, dict) else 0
        pec_total = pec_result.get("total", 0) if isinstance(pec_result, dict) else 0

        total_new = normal_new + pec_new
        total_processed = normal_total + pec_total

        message = f"{total_new} nuove email su {total_processed} processate" if total_processed > 0 else "Nessuna nuova email"

        return {
            "message": message,
            "status": "success",
            "new_emails": total_new,
            "total_processed": total_processed,
            "normal_account": {
                "new": normal_new,
                "total": normal_total
            },
            "pec_account": {
                "new": pec_new,
                "total": pec_total
            }
        }

    except Exception as e:
        logger.error(f"Errore polling manuale: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Errore durante il polling: {str(e)}"
        )


@router.get("/proposals", response_model=EmailListResponse)
def list_subcategory_proposals(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Lista email con proposte di nuove sottocategorie.

    Restituisce tutte le email che hanno `richiede_revisione=True` e
    `sottocategoria_proposta` non vuota, ordinate per data di ricezione
    decrescente.
    """
    try:
        # Query per email con proposte
        query = db.query(Email).filter(
            Email.richiede_revisione == True,
            Email.sottocategoria_proposta.isnot(None),
            Email.revisionata == False
        ).options(
            joinedload(Email.interpretazione),
            joinedload(Email.azioni)
        )

        # Conta totale
        total = query.count()

        # Paginazione
        emails = query.order_by(desc(Email.data_ricezione)).offset(skip).limit(limit).all()

        # Converti a dict
        emails_dict = [email.to_dict() for email in emails]

        return {
            "emails": emails_dict,
            "total": total,
            "skip": skip,
            "limit": limit
        }

    except Exception as e:
        logger.error(f"Errore recupero proposte: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Errore durante il recupero delle proposte: {str(e)}"
        )


@router.get("/{email_id}")
def get_email(email_id: int, db: Session = Depends(get_db)):
    """Recupera dettagli email singola."""
    email = db.query(Email).options(joinedload(Email.azioni)).filter(Email.id == email_id).first()

    if not email:
        raise HTTPException(status_code=404, detail="Email non trovata")

    return email.to_dict()


@router.put("/{email_id}")
def update_email(
    email_id: int,
    update_data: EmailUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    Aggiorna email.

    Permette di modificare: stato, letto, categoria, sottocategoria, note
    """
    email = db.query(Email).filter(Email.id == email_id).first()

    if not email:
        raise HTTPException(status_code=404, detail="Email non trovata")

    # Applica aggiornamenti
    if update_data.stato is not None:
        email.stato = update_data.stato

    if update_data.letto is not None:
        email.letto = update_data.letto

    if update_data.categoria is not None:
        email.categoria = update_data.categoria

    if update_data.sottocategoria is not None:
        email.sottocategoria = update_data.sottocategoria

    if update_data.note is not None:
        email.note = update_data.note

    db.commit()
    db.refresh(email)

    return {"message": "Email aggiornata", "email": email}


@router.put("/{email_id}/categoria")
def update_email_categoria(
    email_id: int,
    categoria_data: dict,
    db: Session = Depends(get_db)
):
    """
    Aggiorna solo la categoria di un'email.
    """
    email = db.query(Email).filter(Email.id == email_id).first()

    if not email:
        raise HTTPException(status_code=404, detail="Email non trovata")

    try:
        categoria_value = categoria_data.get('categoria')
        if categoria_value:
            # Valida che sia una categoria valida
            EmailCategory(categoria_value)
            # Assegna la stringa direttamente (categoria ora è String, non Enum)
            email.categoria = categoria_value
        else:
            email.categoria = None

        db.commit()
        db.refresh(email)

        return {"message": "Categoria aggiornata", "email": email.to_dict()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Categoria non valida: {str(e)}")


@router.delete("/{email_id}")
def delete_email(email_id: int, db: Session = Depends(get_db)):
    """Elimina email."""
    email = db.query(Email).filter(Email.id == email_id).first()

    if not email:
        raise HTTPException(status_code=404, detail="Email non trovata")

    db.delete(email)
    db.commit()

    return {"message": "Email eliminata"}


@router.get("/{email_id}/interpretazione")
def get_email_interpretation(email_id: int, db: Session = Depends(get_db)):
    """Recupera interpretazione LLM dell'email."""
    email = db.query(Email).filter(Email.id == email_id).first()

    if not email:
        raise HTTPException(status_code=404, detail="Email non trovata")

    if not email.interpretazione:
        raise HTTPException(status_code=404, detail="Interpretazione non disponibile")

    return {
        "email_id": email_id,
        "interpretazione": email.interpretazione
    }


@router.get("/{email_id}/azioni")
def get_email_actions(email_id: int, db: Session = Depends(get_db)):
    """Lista tutte le azioni associate a questa email."""
    email = db.query(Email).filter(Email.id == email_id).first()

    if not email:
        raise HTTPException(status_code=404, detail="Email non trovata")

    return {
        "email_id": email_id,
        "azioni": email.azioni
    }


@router.post("/{email_id}/reprocess")
def reprocess_email(email_id: int, db: Session = Depends(get_db)):
    """
    Riprocessa email (ricategorizza e reinterpreta).

    Utile se il LLM ha fatto errori o se sono cambiate le regole.
    """
    from app.services.categorizer import EmailCategorizer
    from app.services.interpreter import EmailInterpreter
    from datetime import datetime

    email = db.query(Email).filter(Email.id == email_id).first()

    if not email:
        raise HTTPException(status_code=404, detail="Email non trovata")

    try:
        # Ricategorizza (con testo estratto dagli allegati)
        categorizer = EmailCategorizer()
        categoria, confidence, sottocategoria, proposta_info = categorizer.categorize(
            email.mittente,
            email.oggetto,
            email.corpo or "",
            attachment_paths=email.allegati_path or [],
            allegati_testo=email.allegati_testo or {}
        )

        # Assegna .value se è un Enum, altrimenti la stringa direttamente
        email.categoria = categoria.value if hasattr(categoria, 'value') else categoria
        email.categoria_confidence = confidence
        email.sottocategoria = sottocategoria

        # Gestione proposta sottocategoria
        if proposta_info:
            email.sottocategoria_proposta = proposta_info['proposta']
            email.motivo_proposta = proposta_info['motivo']
            email.richiede_revisione = True
        else:
            email.sottocategoria_proposta = None
            email.motivo_proposta = None

        # Reinterpreta (con testo estratto dagli allegati) - OPZIONALE
        try:
            interpreter = EmailInterpreter()
            interpretazione_data = interpreter.interpret(
                categoria,
                email.mittente,
                email.oggetto,
                email.corpo or "",
                email.allegati_nomi or [],
                datetime.now().strftime('%Y-%m-%d'),
                attachment_paths=email.allegati_path or [],
                allegati_testo=email.allegati_testo or {}
            )

            if email.interpretazione:
                email.interpretazione.dati_estratti = interpretazione_data
            else:
                from app.models.interpretazione import Interpretazione
                interp = Interpretazione(
                    email_id=email.id,
                    dati_estratti=interpretazione_data
                )
                db.add(interp)
        except Exception as e:
            # Interpretazione fallita (es. timeout) - non blocchiamo il reprocess
            logger.warning(f"Interpretazione fallita durante reprocess email {email_id}: {e}")

        db.commit()
        db.refresh(email)

        # Retriggera anche le azioni (in background)
        from app.tasks.action_tasks import create_actions_for_email
        create_actions_for_email.delay(email.id)

        return {
            "message": "Email riprocessata e azioni ritriggerate",
            "categoria": email.categoria if isinstance(email.categoria, str) else email.categoria.value,
            "confidence": email.confidence_score
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore riprocessamento: {str(e)}")


@router.post("/{email_id}/approve-subcategory")
def approve_subcategory_proposal(
    email_id: int,
    db: Session = Depends(get_db)
):
    """
    Approva la proposta di sottocategoria per un'email.

    - Imposta `sottocategoria` = `sottocategoria_proposta`
    - Pulisce i campi `sottocategoria_proposta` e `motivo_proposta`
    - Imposta `richiede_revisione=False` e `revisionata=True`
    - Aggiorna la sottocategoria predefinita nel file di configurazione
    """
    try:
        email = db.query(Email).filter(Email.id == email_id).first()

        if not email:
            raise HTTPException(status_code=404, detail="Email non trovata")

        if not email.sottocategoria_proposta:
            raise HTTPException(
                status_code=400,
                detail="Nessuna proposta di sottocategoria da approvare"
            )

        # Approva la proposta
        proposta_approvata = email.sottocategoria_proposta
        email.sottocategoria = proposta_approvata
        email.sottocategoria_proposta = None
        email.motivo_proposta = None
        email.richiede_revisione = False
        email.revisionata = True

        db.commit()
        db.refresh(email)

        # TODO: Aggiornare file configurazione categorie per aggiungere la nuova sottocategoria
        # In futuro, implementare logica per aggiungere proposta_approvata alla lista
        # delle sottocategorie predefinite per email.categoria nel file categories.json

        logger.info(f"✅ Proposta approvata per email {email_id}: {proposta_approvata}")

        return {
            "message": f"Sottocategoria '{proposta_approvata}' approvata con successo",
            "email": email.to_dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Errore approvazione proposta: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Errore durante l'approvazione: {str(e)}"
        )


@router.post("/{email_id}/reject-subcategory")
def reject_subcategory_proposal(
    email_id: int,
    db: Session = Depends(get_db)
):
    """
    Rifiuta la proposta di sottocategoria per un'email.

    - Mantiene `sottocategoria` invariata (usa quella scelta dal sistema)
    - Pulisce i campi `sottocategoria_proposta` e `motivo_proposta`
    - Imposta `richiede_revisione=False` e `revisionata=True`
    """
    try:
        email = db.query(Email).filter(Email.id == email_id).first()

        if not email:
            raise HTTPException(status_code=404, detail="Email non trovata")

        if not email.sottocategoria_proposta:
            raise HTTPException(
                status_code=400,
                detail="Nessuna proposta di sottocategoria da rifiutare"
            )

        # Rifiuta la proposta (mantieni sottocategoria esistente)
        proposta_rifiutata = email.sottocategoria_proposta
        email.sottocategoria_proposta = None
        email.motivo_proposta = None
        email.richiede_revisione = False
        email.revisionata = True

        db.commit()
        db.refresh(email)

        logger.info(f"❌ Proposta rifiutata per email {email_id}: {proposta_rifiutata}")

        return {
            "message": f"Proposta rifiutata. Mantenuta sottocategoria '{email.sottocategoria}'",
            "email": email.to_dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Errore rifiuto proposta: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Errore durante il rifiuto: {str(e)}"
        )


@router.get("/{email_id}/attachment/{filename:path}")
def get_attachment(
    email_id: int,
    filename: str,
    db: Session = Depends(get_db)
):
    """
    Scarica un allegato di un'email.

    - **email_id**: ID email
    - **filename**: Nome file allegato
    """
    from fastapi.responses import FileResponse
    import os
    import urllib.parse

    email = db.query(Email).filter(Email.id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email non trovata")

    # Cerca il file negli allegati
    allegati_nomi = email.allegati_nomi or []
    allegati_path = email.allegati_path or []

    # Decodifica filename (potrebbe essere URL encoded)
    filename_decoded = urllib.parse.unquote(filename)

    file_path = None
    for i, nome in enumerate(allegati_nomi):
        if nome == filename_decoded and i < len(allegati_path):
            file_path = allegati_path[i]
            break

    if not file_path:
        raise HTTPException(status_code=404, detail=f"Allegato '{filename_decoded}' non trovato")

    # Verifica che il file esista
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File non trovato sul filesystem")

    # Determina content-type
    import mimetypes
    content_type, _ = mimetypes.guess_type(file_path)
    if not content_type:
        content_type = 'application/octet-stream'

    return FileResponse(
        path=file_path,
        filename=filename_decoded,
        media_type=content_type
    )
