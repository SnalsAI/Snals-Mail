"""
Pydantic schemas per regole
"""

from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime


class RegolaCreate(BaseModel):
    nome: str
    descrizione: Optional[str] = None
    attivo: bool = True
    priorita: int = 10
    condizioni: Dict
    azioni: List[Dict]


class RegolaUpdate(BaseModel):
    nome: Optional[str] = None
    descrizione: Optional[str] = None
    attivo: Optional[bool] = None
    priorita: Optional[int] = None
    condizioni: Optional[Dict] = None
    azioni: Optional[List[Dict]] = None


class RegolaResponse(BaseModel):
    id: int
    nome: str
    descrizione: Optional[str]
    attivo: bool
    priorita: int
    condizioni: Dict
    azioni: List[Dict]
    volte_applicata: int
    ultima_applicazione: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class RegolaTestRequest(BaseModel):
    email_id: Optional[int] = None
    limit: Optional[int] = 50
