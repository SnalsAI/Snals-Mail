"""
API routes per regole
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.regola import Regola
from app.schemas.regola import RegolaCreate, RegolaUpdate, RegolaResponse, RegolaTestRequest
from app.services.rules_engine import RulesEngine
from app.models.email import Email
from app.models.interpretazione import Interpretazione

router = APIRouter()


@router.get("/", response_model=List[RegolaResponse])
def get_regole(db: Session = Depends(get_db)):
    """Lista tutte le regole"""
    regole = db.query(Regola).order_by(Regola.priorita).all()
    return regole


@router.get("/{regola_id}", response_model=RegolaResponse)
def get_regola(regola_id: int, db: Session = Depends(get_db)):
    """Dettaglio regola"""
    regola = db.query(Regola).filter(Regola.id == regola_id).first()
    if not regola:
        raise HTTPException(status_code=404, detail="Regola non trovata")
    return regola


@router.post("/", response_model=RegolaResponse)
def create_regola(regola_data: RegolaCreate, db: Session = Depends(get_db)):
    """Crea nuova regola"""

    regola = Regola(
        nome=regola_data.nome,
        descrizione=regola_data.descrizione,
        attivo=regola_data.attivo,
        priorita=regola_data.priorita,
        condizioni=regola_data.condizioni,
        azioni=regola_data.azioni
    )

    db.add(regola)
    db.commit()
    db.refresh(regola)

    return regola


@router.put("/{regola_id}", response_model=RegolaResponse)
def update_regola(regola_id: int, regola_data: RegolaUpdate, db: Session = Depends(get_db)):
    """Aggiorna regola"""

    regola = db.query(Regola).filter(Regola.id == regola_id).first()
    if not regola:
        raise HTTPException(status_code=404, detail="Regola non trovata")

    # Aggiorna campi
    for field, value in regola_data.dict(exclude_unset=True).items():
        setattr(regola, field, value)

    db.commit()
    db.refresh(regola)

    return regola


@router.delete("/{regola_id}")
def delete_regola(regola_id: int, db: Session = Depends(get_db)):
    """Elimina regola"""

    regola = db.query(Regola).filter(Regola.id == regola_id).first()
    if not regola:
        raise HTTPException(status_code=404, detail="Regola non trovata")

    db.delete(regola)
    db.commit()

    return {"message": "Regola eliminata"}


@router.post("/{regola_id}/test")
def test_regola(regola_id: int, test_data: RegolaTestRequest, db: Session = Depends(get_db)):
    """
    Testa regola su email specifica o su ultime N email

    Returns:
        Lista email che soddisfano la regola
    """

    regola = db.query(Regola).filter(Regola.id == regola_id).first()
    if not regola:
        raise HTTPException(status_code=404, detail="Regola non trovata")

    engine = RulesEngine()
    matched_emails = []

    # Test su email specifica
    if test_data.email_id:
        email = db.query(Email).filter(Email.id == test_data.email_id).first()
        if not email:
            raise HTTPException(status_code=404, detail="Email non trovata")

        interp = db.query(Interpretazione).filter(
            Interpretazione.email_id == test_data.email_id
        ).first()

        if engine.evaluate_conditions_group(regola.condizioni, email, interp):
            matched_emails.append({
                "id": email.id,
                "oggetto": email.oggetto,
                "mittente": email.mittente
            })

    # Test su ultime N email
    else:
        limit = test_data.limit or 50
        emails = db.query(Email).order_by(Email.data_ricezione.desc()).limit(limit).all()

        for email in emails:
            interp = db.query(Interpretazione).filter(
                Interpretazione.email_id == email.id
            ).first()

            if engine.evaluate_conditions_group(regola.condizioni, email, interp):
                matched_emails.append({
                    "id": email.id,
                    "oggetto": email.oggetto,
                    "mittente": email.mittente,
                    "data_ricezione": email.data_ricezione
                })

    return {
        "regola": regola.nome,
        "matched_count": len(matched_emails),
        "matched_emails": matched_emails
    }


@router.post("/{regola_id}/toggle")
def toggle_regola(regola_id: int, db: Session = Depends(get_db)):
    """Attiva/disattiva regola"""

    regola = db.query(Regola).filter(Regola.id == regola_id).first()
    if not regola:
        raise HTTPException(status_code=404, detail="Regola non trovata")

    regola.attivo = not regola.attivo
    db.commit()

    return {"message": f"Regola {'attivata' if regola.attivo else 'disattivata'}"}
