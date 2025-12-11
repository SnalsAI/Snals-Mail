"""
API Routes per gestione impostazioni di sistema (processamento automatico, ecc.)
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models.system_settings import SystemSettings

router = APIRouter(prefix="/system-settings", tags=["system-settings"])


class SystemSettingUpdateRequest(BaseModel):
    """Request per aggiornare un'impostazione"""
    value: str
    value_type: str = 'str'
    description: Optional[str] = None


@router.get("/")
def get_all_system_settings(db: Session = Depends(get_db)):
    """Recupera tutte le impostazioni di sistema"""
    settings = db.query(SystemSettings).all()

    result = {}
    for setting in settings:
        result[setting.key] = {
            'value': setting.get_typed_value(),
            'raw_value': setting.value,
            'type': setting.value_type,
            'description': setting.description
        }

    return result


@router.get("/{key}")
def get_system_setting(key: str, db: Session = Depends(get_db)):
    """Recupera singola impostazione"""
    setting = db.query(SystemSettings).filter(SystemSettings.key == key).first()

    if not setting:
        raise HTTPException(status_code=404, detail=f"Impostazione '{key}' non trovata")

    return {
        'key': setting.key,
        'value': setting.get_typed_value(),
        'raw_value': setting.value,
        'type': setting.value_type,
        'description': setting.description
    }


@router.put("/{key}")
def update_system_setting(key: str, request: SystemSettingUpdateRequest, db: Session = Depends(get_db)):
    """Aggiorna o crea un'impostazione"""
    setting = db.query(SystemSettings).filter(SystemSettings.key == key).first()

    if setting:
        # Aggiorna esistente
        setting.value = request.value
        setting.value_type = request.value_type
        if request.description:
            setting.description = request.description
    else:
        # Crea nuova
        setting = SystemSettings(
            key=key,
            value=request.value,
            value_type=request.value_type,
            description=request.description
        )
        db.add(setting)

    db.commit()
    db.refresh(setting)

    return {
        'message': f"Impostazione '{key}' aggiornata",
        'key': setting.key,
        'value': setting.get_typed_value()
    }


@router.post("/init-defaults")
def initialize_default_settings(db: Session = Depends(get_db)):
    """Inizializza impostazioni predefinite se non esistono"""
    defaults = {
        'auto_process_enabled': {
            'value': 'false',
            'value_type': 'bool',
            'description': 'Abilita processamento automatico email'
        },
        'auto_process_interval': {
            'value': '10',
            'value_type': 'int',
            'description': 'Intervallo processamento automatico (minuti)'
        },
        # ChatGPT / OpenAI settings
        'chatgpt_enabled': {
            'value': 'false',
            'value_type': 'bool',
            'description': 'Abilita uso di ChatGPT/OpenAI per estrazione dati'
        },
        'chatgpt_as_fallback': {
            'value': 'true',
            'value_type': 'bool',
            'description': 'Usa ChatGPT solo come fallback quando altri metodi falliscono'
        },
        'chatgpt_fallback_threshold': {
            'value': '0.5',
            'value_type': 'float',
            'description': 'Soglia completezza sotto cui attivare fallback ChatGPT (0-1)'
        },
    }

    created = []
    for key, data in defaults.items():
        existing = db.query(SystemSettings).filter(SystemSettings.key == key).first()
        if not existing:
            setting = SystemSettings(
                key=key,
                value=data['value'],
                value_type=data['value_type'],
                description=data['description']
            )
            db.add(setting)
            created.append(key)

    if created:
        db.commit()

    return {
        'message': f"{len(created)} impostazioni create",
        'created': created
    }
