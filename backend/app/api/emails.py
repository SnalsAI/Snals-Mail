"""
API routes per gestione email
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.models.email import Email, EmailCategory, EmailStatus
from app.models.interpretazione import Interpretazione
from app.models.azione import Azione
from app.schemas.email import EmailListResponse, EmailDetailResponse, EmailStatsResponse

router = APIRouter()


@router.get("/", response_model=List[EmailListResponse])
def get_emails(
    categoria: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(50, le=100),
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Lista email con filtri"""

    query = db.query(Email)

    # Filtro categoria
    if categoria:
        try:
            cat_enum = EmailCategory[categoria.upper()]
            query = query.filter(Email.categoria == cat_enum)
        except KeyError:
            pass

    # Filtro ricerca
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (Email.mittente.ilike(search_pattern)) |
            (Email.oggetto.ilike(search_pattern)) |
            (Email.corpo.ilike(search_pattern))
        )

    # Ordine e paginazione
    emails = query.order_by(Email.data_ricezione.desc()).offset(offset).limit(limit).all()

    return emails


@router.get("/stats", response_model=EmailStatsResponse)
def get_email_stats(db: Session = Depends(get_db)):
    """Statistiche email"""

    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)

    # Conteggi
    today_count = db.query(func.count(Email.id)).filter(
        Email.data_ricezione >= today_start
    ).scalar()

    week_count = db.query(func.count(Email.id)).filter(
        Email.data_ricezione >= week_start
    ).scalar()

    processing_count = db.query(func.count(Email.id)).filter(
        Email.stato.in_([EmailStatus.RICEVUTA, EmailStatus.IN_ELABORAZIONE])
    ).scalar()

    completed_count = db.query(func.count(Email.id)).filter(
        Email.stato == EmailStatus.COMPLETATA
    ).scalar()

    # Distribuzione categorie
    categories = db.query(
        Email.categoria,
        func.count(Email.id).label('count')
    ).group_by(Email.categoria).all()

    categories_data = [
        {"name": cat.value if cat else "non_categorizzata", "count": count}
        for cat, count in categories
    ]

    # Attività recenti (TODO: implementare log attività)
    recent_activities = []

    return {
        "today": today_count,
        "week": week_count,
        "processing": processing_count,
        "completed": completed_count,
        "total": db.query(func.count(Email.id)).scalar(),
        "categories": categories_data,
        "recent_activities": recent_activities
    }


@router.get("/{email_id}", response_model=EmailDetailResponse)
def get_email(email_id: int, db: Session = Depends(get_db)):
    """Dettaglio email con interpretazione e azioni"""

    email = db.query(Email).filter(Email.id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email non trovata")

    # Carica relazioni
    interpretazione = db.query(Interpretazione).filter(
        Interpretazione.email_id == email_id
    ).first()

    azioni = db.query(Azione).filter(Azione.email_id == email_id).all()

    return {
        **email.__dict__,
        "interpretazione": interpretazione,
        "azioni": azioni
    }


@router.post("/{email_id}/recategorize")
def recategorize_email(email_id: int, db: Session = Depends(get_db)):
    """Forza ri-categorizzazione email"""

    email = db.query(Email).filter(Email.id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email non trovata")

    # Reset stato
    email.stato = EmailStatus.RICEVUTA
    email.categoria = None
    email.categoria_confidence = None

    # Cancella interpretazione vecchia
    db.query(Interpretazione).filter(Interpretazione.email_id == email_id).delete()

    db.commit()

    # Trigger task rielaborazione
    from app.tasks.email_polling import process_single_email
    process_single_email.delay(email_id)

    return {"message": "Rielaborazione avviata"}
