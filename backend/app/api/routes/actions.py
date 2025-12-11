"""
API Routes per gestione Azioni e Processamento Email
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.email_processor import EmailProcessorService

router = APIRouter(prefix="/actions", tags=["actions"])


@router.post("/process-email/{email_id}")
def process_email(email_id: int, db: Session = Depends(get_db)):
    """
    Processa manualmente un'email: applica regole e crea azioni.

    Restituisce un log dettagliato di tutto il processo per debug.
    """
    processor = EmailProcessorService(db)
    result = processor.process_email(email_id)

    if not result['success']:
        raise HTTPException(status_code=400, detail={
            "error": result.get('error'),
            "log": result.get('log', [])
        })

    return result
