"""
Servizio per accesso centralizzato alle impostazioni di sistema.

Fornisce funzioni helper per leggere le impostazioni senza bisogno
di gestire direttamente la sessione DB.
"""

import logging
from typing import Any, Optional
from functools import lru_cache
from datetime import datetime, timedelta

from app.database import SessionLocal
from app.models.system_settings import SystemSettings

logger = logging.getLogger(__name__)

# Cache per le impostazioni (TTL 60 secondi)
_settings_cache = {}
_cache_expiry = {}
_CACHE_TTL_SECONDS = 60


def get_system_setting(key: str, default: Any = None) -> Any:
    """
    Recupera un'impostazione di sistema.

    Args:
        key: Chiave dell'impostazione
        default: Valore di default se non trovata

    Returns:
        Valore tipizzato dell'impostazione
    """
    global _settings_cache, _cache_expiry

    # Check cache
    now = datetime.utcnow()
    if key in _settings_cache and _cache_expiry.get(key, now) > now:
        return _settings_cache[key]

    # Query DB
    db = SessionLocal()
    try:
        setting = db.query(SystemSettings).filter(SystemSettings.key == key).first()
        if setting:
            value = setting.get_typed_value()
            # Update cache
            _settings_cache[key] = value
            _cache_expiry[key] = now + timedelta(seconds=_CACHE_TTL_SECONDS)
            return value
        return default
    except Exception as e:
        logger.warning(f"Errore lettura setting '{key}': {e}")
        return default
    finally:
        db.close()


def set_system_setting(key: str, value: Any, value_type: str = 'str', description: str = None) -> bool:
    """
    Imposta un'impostazione di sistema.

    Args:
        key: Chiave dell'impostazione
        value: Valore da impostare
        value_type: Tipo del valore ('bool', 'int', 'float', 'str', 'json')
        description: Descrizione opzionale

    Returns:
        True se impostato con successo
    """
    global _settings_cache, _cache_expiry

    db = SessionLocal()
    try:
        setting = db.query(SystemSettings).filter(SystemSettings.key == key).first()

        # Converti valore a stringa
        if value_type == 'bool':
            str_value = 'true' if value else 'false'
        elif value_type == 'json':
            import json
            str_value = json.dumps(value)
        else:
            str_value = str(value)

        if setting:
            setting.value = str_value
            setting.value_type = value_type
            if description:
                setting.description = description
        else:
            setting = SystemSettings(
                key=key,
                value=str_value,
                value_type=value_type,
                description=description
            )
            db.add(setting)

        db.commit()

        # Invalida cache
        if key in _settings_cache:
            del _settings_cache[key]
        if key in _cache_expiry:
            del _cache_expiry[key]

        return True
    except Exception as e:
        logger.error(f"Errore impostazione setting '{key}': {e}")
        db.rollback()
        return False
    finally:
        db.close()


def clear_settings_cache():
    """Svuota la cache delle impostazioni."""
    global _settings_cache, _cache_expiry
    _settings_cache = {}
    _cache_expiry = {}


# ============================================
# Helper specifici per ChatGPT
# ============================================

def is_chatgpt_enabled() -> bool:
    """Verifica se ChatGPT/OpenAI e' abilitato."""
    return get_system_setting('chatgpt_enabled', False)


def is_chatgpt_fallback_enabled() -> bool:
    """Verifica se ChatGPT e' usato come fallback."""
    return get_system_setting('chatgpt_as_fallback', True)


def get_chatgpt_fallback_threshold() -> float:
    """Soglia completezza per attivare fallback ChatGPT."""
    return get_system_setting('chatgpt_fallback_threshold', 0.5)


def get_chatgpt_settings() -> dict:
    """
    Recupera tutte le impostazioni ChatGPT.

    Returns:
        Dict con enabled, as_fallback, threshold
    """
    return {
        'enabled': is_chatgpt_enabled(),
        'as_fallback': is_chatgpt_fallback_enabled(),
        'fallback_threshold': get_chatgpt_fallback_threshold()
    }
