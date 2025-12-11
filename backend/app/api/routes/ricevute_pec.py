"""
API Routes per gestione Ricevute PEC (consegna/accettazione).
"""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.database import get_db
from app.models.email import Email

router = APIRouter(prefix="/ricevute-pec", tags=["ricevute-pec"])


@router.get("/")
def list_ricevute_pec(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    tipo: Optional[str] = Query(None, description="Filtro tipo: 'consegna' o 'accettazione'"),
    db: Session = Depends(get_db)
):
    """
    Lista ricevute PEC (accettazione e consegna).
    """
    query = db.query(Email).filter(Email.categoria == "ricevuta_pec")

    # Filtro opzionale per tipo
    if tipo == 'consegna':
        query = query.filter(Email.oggetto.ilike('CONSEGNA:%'))
    elif tipo == 'accettazione':
        query = query.filter(Email.oggetto.ilike('ACCETTAZIONE:%'))

    total = query.count()

    emails = query.order_by(desc(Email.data_ricezione)).offset(skip).limit(limit).all()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "emails": [email.to_dict() for email in emails]
    }


@router.get("/stats")
def get_ricevute_stats(db: Session = Depends(get_db)):
    """
    Statistiche ricevute PEC.
    """
    total = db.query(Email).filter(Email.categoria == "ricevuta_pec").count()

    consegne = db.query(Email).filter(
        Email.categoria == "ricevuta_pec",
        Email.oggetto.ilike('CONSEGNA:%')
    ).count()

    accettazioni = db.query(Email).filter(
        Email.categoria == "ricevuta_pec",
        Email.oggetto.ilike('ACCETTAZIONE:%')
    ).count()

    return {
        "total": total,
        "consegne": consegne,
        "accettazioni": accettazioni
    }


@router.get("/{email_id}")
def get_ricevuta_pec(email_id: int, db: Session = Depends(get_db)):
    """
    Dettaglio singola ricevuta PEC.
    """
    email = db.query(Email).filter(
        Email.id == email_id,
        Email.categoria == "ricevuta_pec"
    ).first()

    if not email:
        raise HTTPException(status_code=404, detail="Ricevuta PEC non trovata")

    return email.to_dict()
