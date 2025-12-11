"""
Pydantic schemas per Email API.

FASE 6: API Complete per Frontend
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr, field_validator
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
    corpo: Optional[str]
    corpo_html: Optional[str]
    data_ricezione: datetime
    account_type: str
    categoria: Optional[str]
    sottocategoria: Optional[str] = None
    codice_scuola: Optional[str] = None
    stato: str
    letto: bool
    confidence_score: Optional[float]
    allegati_nomi: Optional[List[str]]
    allegati_path: Optional[List[str]]
    note: Optional[str]
    interpretazione: Optional[Dict[str, Any]] = None
    azioni: Optional[List[Dict[str, Any]]] = None

    class Config:
        from_attributes = True

    @field_validator('allegati_path', mode='before')
    @classmethod
    def filter_none_paths(cls, v):
        """Filtra valori None da allegati_path."""
        if v is None:
            return None
        if isinstance(v, list):
            return [p for p in v if p is not None]
        return v

    @field_validator('allegati_nomi', mode='before')
    @classmethod
    def filter_none_nomi(cls, v):
        """Filtra valori None da allegati_nomi."""
        if v is None:
            return None
        if isinstance(v, list):
            return [n for n in v if n is not None]
        return v

    @classmethod
    def model_validate(cls, obj: Any) -> "EmailResponse":
        """Custom validation to handle relationships"""
        if hasattr(obj, '__dict__'):
            data = {}
            for field in cls.model_fields:
                if field == 'interpretazione' and hasattr(obj, 'interpretazione'):
                    # Serialize interpretazione relationship
                    if obj.interpretazione:
                        data['interpretazione'] = obj.interpretazione.interpretazione_json or {}
                    else:
                        data['interpretazione'] = None
                elif field == 'azioni' and hasattr(obj, 'azioni'):
                    # Serialize azioni relationship
                    data['azioni'] = [
                        {
                            'id': a.id,
                            'tipo': a.tipo.value if hasattr(a.tipo, 'value') else str(a.tipo),
                            'descrizione': a.descrizione,
                            'stato': a.stato.value if hasattr(a.stato, 'value') else str(a.stato)
                        }
                        for a in obj.azioni
                    ] if obj.azioni else []
                elif field == 'account_type':
                    # Serialize enum as string
                    data['account_type'] = obj.account_type.value if hasattr(obj.account_type, 'value') else str(obj.account_type)
                elif field == 'categoria' and hasattr(obj, 'categoria'):
                    # Serialize enum as string
                    data['categoria'] = obj.categoria.value if obj.categoria and hasattr(obj.categoria, 'value') else None
                elif field == 'stato' and hasattr(obj, 'stato'):
                    # Serialize enum as string
                    data['stato'] = obj.stato.value if hasattr(obj.stato, 'value') else str(obj.stato)
                elif field == 'allegati_path' and hasattr(obj, 'allegati_path'):
                    # Filter out None values from allegati_path list
                    paths = getattr(obj, 'allegati_path', None) or []
                    data['allegati_path'] = [p for p in paths if p is not None] if paths else None
                elif field == 'allegati_nomi' and hasattr(obj, 'allegati_nomi'):
                    # Filter out None values from allegati_nomi list (consistency)
                    nomi = getattr(obj, 'allegati_nomi', None) or []
                    data['allegati_nomi'] = [n for n in nomi if n is not None] if nomi else None
                else:
                    data[field] = getattr(obj, field, None)
            return cls(**data)
        return super().model_validate(obj)


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
    sottocategoria: Optional[str] = None
    note: Optional[str] = None
