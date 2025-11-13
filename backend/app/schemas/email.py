"""
Pydantic schemas per Email API.

FASE 6: API Complete per Frontend
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr
from app.models.email import EmailCategory, EmailStatus, AccountType


class EmailBase(BaseModel):
    """Schema base Email."""
    mittente: str
    destinatario: Optional[str] = None
    oggetto: str
    corpo_testo: Optional[str] = None


class EmailResponse(BaseModel):
    """Schema risposta Email dettagliata."""
    id: int
    message_id: str
    mittente: str
    destinatario: Optional[str]
    oggetto: str
    corpo_testo: Optional[str]
    corpo_html: Optional[str]
    data_ricezione: datetime
    account_type: str
    categoria: Optional[str]
    stato: str
    letto: bool
    confidence_score: Optional[float]
    allegati: Optional[List[Dict[str, Any]]]
    note: Optional[str]
    interpretazione: Optional[Dict[str, Any]] = None
    azioni: Optional[List[Dict[str, Any]]] = None

    class Config:
        from_attributes = True


class EmailListResponse(BaseModel):
    """Schema risposta lista email."""
    total: int
    skip: int
    limit: int
    emails: List[EmailResponse]


class EmailUpdateRequest(BaseModel):
    """Schema richiesta aggiornamento email."""
    stato: Optional[EmailStatus] = None
    letto: Optional[bool] = None
    categoria: Optional[EmailCategory] = None
    note: Optional[str] = None
