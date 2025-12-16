"""
Servizio per la gestione delle configurazioni del modulo Booking.

Permette di leggere e scrivere configurazioni dal database
con caching e conversione automatica dei tipi.
"""

from sqlalchemy.orm import Session
from typing import Any, Optional, Dict
from datetime import datetime
import json
import logging

from app.models.booking import BookingConfig, DEFAULT_BOOKING_CONFIG

logger = logging.getLogger(__name__)


class ConfigService:
    """Gestione configurazioni modulo prenotazioni."""

    # Cache in-memory (resettata a ogni riavvio)
    _cache: Dict[str, Any] = {}

    def __init__(self, db: Session):
        self.db = db

    def get(self, chiave: str, default: Any = None) -> Any:
        """
        Ottiene un valore di configurazione.

        Args:
            chiave: Chiave configurazione
            default: Valore default se non esiste

        Returns:
            Valore convertito nel tipo corretto
        """
        # Check cache
        if chiave in self._cache:
            return self._cache[chiave]

        # Query database
        config = self.db.query(BookingConfig).filter(
            BookingConfig.chiave == chiave
        ).first()

        if not config:
            # Usa default dal dizionario se esiste
            if chiave in DEFAULT_BOOKING_CONFIG:
                return self._convert_value(
                    DEFAULT_BOOKING_CONFIG[chiave]["valore"],
                    DEFAULT_BOOKING_CONFIG[chiave]["tipo"]
                )
            return default

        # Converti e cache
        value = self._convert_value(config.valore, config.tipo)
        self._cache[chiave] = value
        return value

    def set(self, chiave: str, valore: Any) -> bool:
        """
        Imposta un valore di configurazione.

        Args:
            chiave: Chiave configurazione
            valore: Nuovo valore

        Returns:
            True se salvato con successo
        """
        config = self.db.query(BookingConfig).filter(
            BookingConfig.chiave == chiave
        ).first()

        if not config:
            # Crea nuova configurazione
            tipo = self._detect_type(valore)
            config = BookingConfig(
                chiave=chiave,
                valore=str(valore),
                tipo=tipo
            )
            self.db.add(config)
        else:
            config.valore = str(valore)
            config.updated_at = datetime.utcnow()

        self.db.commit()

        # Aggiorna cache
        self._cache[chiave] = valore

        return True

    def get_all(self) -> Dict[str, Any]:
        """
        Ottiene tutte le configurazioni.

        Returns:
            Dizionario chiave -> valore
        """
        configs = self.db.query(BookingConfig).all()
        return {
            c.chiave: self._convert_value(c.valore, c.tipo)
            for c in configs
        }

    def init_defaults(self) -> int:
        """
        Inizializza configurazioni di default.

        Crea le configurazioni mancanti dal dizionario DEFAULT_BOOKING_CONFIG.

        Returns:
            Numero di configurazioni create
        """
        created = 0

        for chiave, data in DEFAULT_BOOKING_CONFIG.items():
            existing = self.db.query(BookingConfig).filter(
                BookingConfig.chiave == chiave
            ).first()

            if not existing:
                config = BookingConfig(
                    chiave=chiave,
                    valore=data["valore"],
                    tipo=data["tipo"],
                    descrizione=data.get("descrizione")
                )
                self.db.add(config)
                created += 1
                logger.info(f"Creata configurazione: {chiave} = {data['valore']}")

        self.db.commit()
        return created

    def clear_cache(self):
        """Pulisce la cache in-memory."""
        self._cache.clear()

    def _convert_value(self, valore: str, tipo: str) -> Any:
        """Converte il valore stringa nel tipo corretto."""
        if tipo == "int":
            return int(valore)
        elif tipo == "bool":
            return valore.lower() in ("true", "1", "yes", "si")
        elif tipo == "float":
            return float(valore)
        elif tipo == "json":
            return json.loads(valore)
        else:  # string
            return valore

    def _detect_type(self, valore: Any) -> str:
        """Rileva il tipo di un valore."""
        if isinstance(valore, bool):
            return "bool"
        elif isinstance(valore, int):
            return "int"
        elif isinstance(valore, float):
            return "float"
        elif isinstance(valore, (dict, list)):
            return "json"
        else:
            return "string"


# ============================================================================
# CONFIGURAZIONI PREDEFINITE
# ============================================================================

class BookingSettings:
    """
    Accesso tipizzato alle configurazioni più comuni.

    Uso:
        settings = BookingSettings(db)
        ore = settings.ore_minime_annullamento
    """

    def __init__(self, db: Session):
        self._config = ConfigService(db)

    @property
    def ore_minime_annullamento(self) -> int:
        """Ore minime di anticipo per annullare una prenotazione."""
        return self._config.get("ore_minime_annullamento", 24)

    @property
    def ore_minime_modifica(self) -> int:
        """Ore minime di anticipo per modificare una prenotazione."""
        return self._config.get("ore_minime_modifica", 24)

    @property
    def promemoria_ore_prima(self) -> int:
        """Ore prima dell'appuntamento per inviare promemoria."""
        return self._config.get("promemoria_ore_prima", 24)

    @property
    def privacy_version(self) -> str:
        """Versione attuale dell'informativa privacy."""
        return self._config.get("privacy_version", "2025.1")

    @property
    def email_mittente(self) -> str:
        """Indirizzo email mittente per notifiche."""
        return self._config.get("email_mittente", "prenotazioni@snals.it")

    @property
    def max_prenotazioni_utente_giorno(self) -> int:
        """Max prenotazioni per utente nello stesso giorno."""
        return self._config.get("max_prenotazioni_utente_giorno", 2)
