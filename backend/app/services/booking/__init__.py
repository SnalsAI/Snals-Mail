"""
Servizi per il modulo Prenotazioni

Servizi disponibili:
- SlotGeneratorService: Genera slot da disponibilità
- BookingService: Logica prenotazioni
- NotificationService: Invio notifiche email
- ConfigService: Lettura/scrittura configurazioni
"""

from .slot_generator import SlotGeneratorService
from .config_service import ConfigService

__all__ = [
    "SlotGeneratorService",
    "ConfigService",
]
