"""
API Routes per gestione Settings e Test Connessioni Email.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict

from app.services.email_ingest import EmailNormalClient, EmailPECClient

router = APIRouter(prefix="/settings", tags=["settings"])


class TestEmailResponse(BaseModel):
    """Response del test email"""
    pop3: Dict
    smtp: Dict
    overall_success: bool


@router.post("/test-email-normal", response_model=TestEmailResponse)
async def test_email_normal():
    """
    Test della configurazione email NORMALE:
    - Test POP3: connessione e lettura prima email
    - Test SMTP: invio email di test a se stesso
    """
    try:
        client = EmailNormalClient()
        results = client.test_connection()
        return results
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Errore durante il test: {str(e)}"
        )


@router.post("/test-email-pec", response_model=TestEmailResponse)
async def test_email_pec():
    """
    Test della configurazione email PEC:
    - Test POP3: connessione e lettura prima email
    - Test SMTP: invio email di test a se stesso
    """
    try:
        client = EmailPECClient()
        results = client.test_connection()
        return results
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Errore durante il test: {str(e)}"
        )
