"""
API Routes per gestione Email.

FASE 6: API Complete per Frontend
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_

from app.database import get_db
from app.models.email import Email, EmailCategory, EmailStatus
from app.schemas.email import EmailResponse, EmailListResponse, EmailUpdateRequest

router = APIRouter(prefix="/emails", tags=["emails"])


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
    query = db.query(Email)

    # Applica filtri
    if categoria:
        try:
            cat_enum = EmailCategory(categoria)
            query = query.filter(Email.categoria == cat_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Categoria non valida: {categoria}")

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
        "emails": emails
    }


@router.get("/{email_id}", response_model=EmailResponse)
def get_email(email_id: int, db: Session = Depends(get_db)):
    """Recupera dettagli email singola."""
    email = db.query(Email).filter(Email.id == email_id).first()

    if not email:
        raise HTTPException(status_code=404, detail="Email non trovata")

    return email


@router.put("/{email_id}")
def update_email(
    email_id: int,
    update_data: EmailUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    Aggiorna email.

    Permette di modificare: stato, letto, categoria, note
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

    if update_data.note is not None:
        email.note = update_data.note

    db.commit()
    db.refresh(email)

    return {"message": "Email aggiornata", "email": email}


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
        # Ricategorizza
        categorizer = EmailCategorizer()
        categoria, confidence = categorizer.categorize(
            email.mittente,
            email.oggetto,
            email.corpo_testo
        )

        email.categoria = categoria
        email.confidence_score = confidence

        # Reinterpreta
        interpreter = EmailInterpreter()
        interpretazione_data = interpreter.interpret(
            categoria,
            email.mittente,
            email.oggetto,
            email.corpo_testo,
            email.allegati or [],
            datetime.now().strftime('%Y-%m-%d')
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

        db.commit()
        db.refresh(email)

        return {
            "message": "Email riprocessata",
            "categoria": email.categoria.value,
            "confidence": email.confidence_score
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore riprocessamento: {str(e)}")
