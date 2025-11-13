"""
API Routes per gestione Azioni.

FASE 6: API Complete per Frontend
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models.azione import Azione, TipoAzione, StatoAzione
from app.services.action_executor import ActionExecutor

router = APIRouter(prefix="/azioni", tags=["azioni"])


@router.get("/")
def list_azioni(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    email_id: Optional[int] = None,
    tipo_azione: Optional[str] = None,
    stato: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Lista azioni con filtri e paginazione.

    - **skip**: Numero azioni da saltare
    - **limit**: Numero massimo azioni da restituire
    - **email_id**: Filtra per email specifica
    - **tipo_azione**: Filtra per tipo azione
    - **stato**: Filtra per stato
    """
    query = db.query(Azione)

    if email_id:
        query = query.filter(Azione.email_id == email_id)

    if tipo_azione:
        try:
            tipo_enum = TipoAzione(tipo_azione)
            query = query.filter(Azione.tipo_azione == tipo_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Tipo azione non valido: {tipo_azione}")

    if stato:
        try:
            stato_enum = StatoAzione(stato)
            query = query.filter(Azione.stato == stato_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Stato non valido: {stato}")

    total = query.count()
    azioni = query.order_by(desc(Azione.creata_at)).offset(skip).limit(limit).all()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "azioni": azioni
    }


@router.get("/{azione_id}")
def get_azione(azione_id: int, db: Session = Depends(get_db)):
    """Recupera dettagli azione singola."""
    azione = db.query(Azione).filter(Azione.id == azione_id).first()

    if not azione:
        raise HTTPException(status_code=404, detail="Azione non trovata")

    return azione


@router.post("/{azione_id}/execute")
def execute_azione(azione_id: int, db: Session = Depends(get_db)):
    """
    Esegue manualmente un'azione.

    Utile per eseguire azioni pending o ritentare azioni fallite.
    """
    executor = ActionExecutor(db)

    try:
        success = executor.execute_action(azione_id)

        if success:
            return {"message": "Azione eseguita con successo", "azione_id": azione_id}
        else:
            raise HTTPException(status_code=500, detail="Esecuzione azione fallita")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore esecuzione: {str(e)}")


@router.post("/{azione_id}/retry")
def retry_azione(azione_id: int, db: Session = Depends(get_db)):
    """
    Ritenta un'azione fallita.

    Resetta lo stato a PENDING e la reinserisce nella coda.
    """
    azione = db.query(Azione).filter(Azione.id == azione_id).first()

    if not azione:
        raise HTTPException(status_code=404, detail="Azione non trovata")

    if azione.stato != StatoAzione.FALLITA:
        raise HTTPException(status_code=400, detail="Solo azioni fallite possono essere ritentate")

    # Resetta stato
    azione.stato = StatoAzione.PENDING
    azione.errore = None
    db.commit()

    return {"message": "Azione reinserita in coda", "azione_id": azione_id}


@router.delete("/{azione_id}")
def delete_azione(azione_id: int, db: Session = Depends(get_db)):
    """Elimina azione."""
    azione = db.query(Azione).filter(Azione.id == azione_id).first()

    if not azione:
        raise HTTPException(status_code=404, detail="Azione non trovata")

    db.delete(azione)
    db.commit()

    return {"message": "Azione eliminata"}


@router.get("/stats/summary")
def get_azioni_stats(db: Session = Depends(get_db)):
    """
    Statistiche azioni.

    Restituisce conteggi per stato e tipo.
    """
    from sqlalchemy import func

    # Conta per stato
    stati = db.query(
        Azione.stato,
        func.count(Azione.id).label('count')
    ).group_by(Azione.stato).all()

    # Conta per tipo
    tipi = db.query(
        Azione.tipo_azione,
        func.count(Azione.id).label('count')
    ).group_by(Azione.tipo_azione).all()

    return {
        "stati": [{"stato": s.stato.value, "count": s.count} for s in stati],
        "tipi": [{"tipo": t.tipo_azione.value, "count": t.count} for t in tipi],
        "total": db.query(Azione).count()
    }
