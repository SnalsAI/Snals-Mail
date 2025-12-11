"""
Utility per gestione datetime con timezone
"""

from datetime import datetime
from zoneinfo import ZoneInfo
from app.config import get_settings

settings = get_settings()


def get_timezone():
    """Ottiene il timezone configurato"""
    return ZoneInfo(settings.TIMEZONE)


def now_with_tz():
    """Ottiene datetime corrente nel timezone configurato"""
    return datetime.now(get_timezone())


def utc_to_local(dt: datetime):
    """Converte datetime UTC a timezone locale"""
    if dt.tzinfo is None:
        # Se è naive, assume sia UTC
        dt = dt.replace(tzinfo=ZoneInfo('UTC'))
    return dt.astimezone(get_timezone())


def local_to_utc(dt: datetime):
    """Converte datetime locale a UTC"""
    if dt.tzinfo is None:
        # Se è naive, assume sia nel timezone locale
        dt = dt.replace(tzinfo=get_timezone())
    return dt.astimezone(ZoneInfo('UTC'))


def make_aware(dt: datetime, tz=None):
    """Rende un datetime naive timezone-aware"""
    if dt.tzinfo is not None:
        return dt

    if tz is None:
        tz = get_timezone()

    return dt.replace(tzinfo=tz)
