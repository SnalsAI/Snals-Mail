"""
API Routes per gestione Regole.

FASE 7: Rules Engine
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel

from app.database import get_db
from app.models.regola import Regola
from app.services.rules_engine import RulesEngine

router = APIRouter(prefix="/regole", tags=["regole"])


class RegolaCreate(BaseModel):
    """Schema creazione regola."""
    nome: str
    descrizione: Optional[str] = None
    condizioni: Dict[str, Any]
    azioni: Dict[str, Any]
    priorita: int = 10
    attiva: bool = True


class RegolaUpdate(BaseModel):
    """Schema aggiornamento regola."""
    nome: Optional[str] = None
    descrizione: Optional[str] = None
    condizioni: Optional[Dict[str, Any]] = None
    azioni: Optional[Dict[str, Any]] = None
    priorita: Optional[int] = None
    attiva: Optional[bool] = None


@router.get("/")
def list_regole(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    attiva: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """
    Lista regole con filtri e paginazione.

    - **skip**: Numero regole da saltare
    - **limit**: Numero massimo regole da restituire
    - **attiva**: Filtra per regole attive/disattive
    """
    query = db.query(Regola)

    if attiva is not None:
        query = query.filter(Regola.attiva == attiva)

    total = query.count()
    regole = query.order_by(desc(Regola.priorita)).offset(skip).limit(limit).all()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "regole": regole
    }


@router.get("/{regola_id}")
def get_regola(regola_id: int, db: Session = Depends(get_db)):
    """Recupera dettagli regola singola."""
    regola = db.query(Regola).filter(Regola.id == regola_id).first()

    if not regola:
        raise HTTPException(status_code=404, detail="Regola non trovata")

    return regola


@router.post("/")
def create_regola(regola_data: RegolaCreate, db: Session = Depends(get_db)):
    """
    Crea nuova regola.

    Esempio body:
    ```json
    {
      "nome": "Inoltra urgenze a supervisore",
      "descrizione": "Inoltra email con 'urgente' nel subject",
      "condizioni": {
        "operator": "AND",
        "rules": [
          {"field": "oggetto", "condition": "contiene", "value": "urgente"}
        ]
      },
      "azioni": {
        "actions": [
          {"type": "inoltra_a", "params": {"to": "supervisore@snals.it"}}
        ]
      },
      "priorita": 20,
      "attiva": true
    }
    ```
    """
    regola = Regola(
        nome=regola_data.nome,
        descrizione=regola_data.descrizione,
        condizioni=regola_data.condizioni,
        azioni=regola_data.azioni,
        priorita=regola_data.priorita,
        attiva=regola_data.attiva
    )

    db.add(regola)
    db.commit()
    db.refresh(regola)

    return {"message": "Regola creata", "regola": regola}


@router.put("/{regola_id}")
def update_regola(
    regola_id: int,
    regola_data: RegolaUpdate,
    db: Session = Depends(get_db)
):
    """Aggiorna regola esistente."""
    regola = db.query(Regola).filter(Regola.id == regola_id).first()

    if not regola:
        raise HTTPException(status_code=404, detail="Regola non trovata")

    # Applica aggiornamenti
    if regola_data.nome is not None:
        regola.nome = regola_data.nome

    if regola_data.descrizione is not None:
        regola.descrizione = regola_data.descrizione

    if regola_data.condizioni is not None:
        regola.condizioni = regola_data.condizioni

    if regola_data.azioni is not None:
        regola.azioni = regola_data.azioni

    if regola_data.priorita is not None:
        regola.priorita = regola_data.priorita

    if regola_data.attiva is not None:
        regola.attiva = regola_data.attiva

    db.commit()
    db.refresh(regola)

    return {"message": "Regola aggiornata", "regola": regola}


@router.delete("/{regola_id}")
def delete_regola(regola_id: int, db: Session = Depends(get_db)):
    """Elimina regola."""
    regola = db.query(Regola).filter(Regola.id == regola_id).first()

    if not regola:
        raise HTTPException(status_code=404, detail="Regola non trovata")

    db.delete(regola)
    db.commit()

    return {"message": "Regola eliminata"}


@router.post("/{regola_id}/toggle")
def toggle_regola(regola_id: int, db: Session = Depends(get_db)):
    """Attiva/disattiva regola."""
    regola = db.query(Regola).filter(Regola.id == regola_id).first()

    if not regola:
        raise HTTPException(status_code=404, detail="Regola non trovata")

    regola.attiva = not regola.attiva
    db.commit()

    return {
        "message": f"Regola {'attivata' if regola.attiva else 'disattivata'}",
        "attiva": regola.attiva
    }


@router.post("/{regola_id}/test")
def test_regola(
    regola_id: int,
    email_id: int = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """
    Testa regola su una email specifica.

    Non esegue azioni, solo verifica se la regola sarebbe applicata.

    Body: `{"email_id": 123}`
    """
    engine = RulesEngine(db)

    try:
        result = engine.test_rule(regola_id, email_id)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore test regola: {str(e)}")


@router.post("/test-conditions")
def test_conditions(
    email_id: int = Body(...),
    condizioni: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    """
    Testa condizioni su una email senza salvare la regola.

    Utile per testare condizioni mentre si costruisce una regola.

    Body:
    ```json
    {
      "email_id": 123,
      "condizioni": {
        "operator": "AND",
        "rules": [
          {"field": "oggetto", "condition": "contiene", "value": "test"}
        ]
      }
    }
    ```
    """
    from app.models.email import Email

    email = db.query(Email).filter(Email.id == email_id).first()

    if not email:
        raise HTTPException(status_code=404, detail="Email non trovata")

    engine = RulesEngine(db)

    try:
        match = engine._evaluate_conditions(email, condizioni)

        return {
            "email_id": email_id,
            "email_oggetto": email.oggetto,
            "condizioni": condizioni,
            "match": match
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore valutazione: {str(e)}")
