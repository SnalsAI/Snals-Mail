"""
Pydantic schemas per email
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class EmailListResponse(BaseModel):
    id: int
    mittente: str
    oggetto: str
    categoria: Optional[str]
    data_ricezione: datetime
    stato: str

    class Config:
        from_attributes = True


class InterpretazioneResponse(BaseModel):
    id: int
    interpretazione_json: dict
    confidence: float

    class Config:
        from_attributes = True


class AzioneResponse(BaseModel):
    id: int
    tipo: str
    stato: str
    timestamp_inizio: datetime

    class Config:
        from_attributes = True


class EmailDetailResponse(BaseModel):
    id: int
    mittente: str
    destinatario: str
    oggetto: str
    corpo: str
    data_ricezione: datetime
    categoria: Optional[str]
    categoria_confidence: Optional[float]
    stato: str
    allegati_nomi: Optional[List[str]]
    interpretazione: Optional[InterpretazioneResponse]
    azioni: List[AzioneResponse]

    class Config:
        from_attributes = True


class EmailStatsResponse(BaseModel):
    today: int
    week: int
    processing: int
    completed: int
    total: int
    categories: List[dict]
    recent_activities: List[dict]
