"""
OpenAI Rate Limiter - Controllo costi giornalieri
Limite: max 1€/giorno
"""
import logging
import json
from typing import Dict, Optional
from datetime import datetime, date
from pathlib import Path

logger = logging.getLogger(__name__)


class OpenAIRateLimiter:
    """
    Rate limiter per controllare costi OpenAI.
    Traccia spesa giornaliera e blocca richieste se supera soglia.
    """

    def __init__(self, daily_limit_eur: float = 1.0, storage_path: str = "storage/openai_usage.json"):
        """
        Inizializza rate limiter.

        Args:
            daily_limit_eur: Limite giornaliero in Euro
            storage_path: Path file per persistenza dati
        """
        self.daily_limit_eur = daily_limit_eur
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        # Carica dati esistenti
        self.usage_data = self._load_usage()

    def _load_usage(self) -> Dict:
        """Carica dati utilizzo da file."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Errore caricamento usage: {e}")

        return {
            'daily_usage': {},  # date -> cost
            'total_requests': 0,
            'total_cost_eur': 0.0
        }

    def _save_usage(self):
        """Salva dati utilizzo su file."""
        try:
            with open(self.storage_path, 'w') as f:
                json.dump(self.usage_data, f, indent=2)
        except Exception as e:
            logger.error(f"Errore salvataggio usage: {e}")

    def get_today_usage(self) -> float:
        """
        Ritorna spesa di oggi in Euro.

        Returns:
            float: Spesa odierna
        """
        today = str(date.today())
        return self.usage_data['daily_usage'].get(today, 0.0)

    def get_remaining_budget(self) -> float:
        """
        Ritorna budget rimanente oggi.

        Returns:
            float: Euro rimanenti
        """
        return self.daily_limit_eur - self.get_today_usage()

    def can_make_request(self, estimated_cost_eur: float = 0.001) -> bool:
        """
        Verifica se è possibile fare una richiesta.

        Args:
            estimated_cost_eur: Costo stimato richiesta

        Returns:
            bool: True se budget sufficiente
        """
        remaining = self.get_remaining_budget()
        return remaining >= estimated_cost_eur

    def record_request(
        self,
        cost_eur: float,
        tokens_prompt: int,
        tokens_completion: int,
        model: str
    ) -> Dict:
        """
        Registra una richiesta OpenAI.

        Args:
            cost_eur: Costo effettivo in Euro
            tokens_prompt: Token prompt
            tokens_completion: Token completion
            model: Modello usato

        Returns:
            Dict con info aggiornate
        """
        today = str(date.today())

        # Aggiorna usage giornaliero
        if today not in self.usage_data['daily_usage']:
            self.usage_data['daily_usage'][today] = 0.0

        self.usage_data['daily_usage'][today] += cost_eur

        # Aggiorna totali
        self.usage_data['total_requests'] += 1
        self.usage_data['total_cost_eur'] += cost_eur

        # Salva
        self._save_usage()

        usage_info = {
            'date': today,
            'request_cost_eur': cost_eur,
            'today_total_eur': self.usage_data['daily_usage'][today],
            'remaining_budget_eur': self.daily_limit_eur - self.usage_data['daily_usage'][today],
            'daily_limit_eur': self.daily_limit_eur,
            'budget_used_pct': (self.usage_data['daily_usage'][today] / self.daily_limit_eur) * 100,
            'tokens': {
                'prompt': tokens_prompt,
                'completion': tokens_completion,
                'total': tokens_prompt + tokens_completion
            },
            'model': model
        }

        logger.info(
            f"💰 OpenAI: €{cost_eur:.6f} | "
            f"Oggi: €{usage_info['today_total_eur']:.6f}/{self.daily_limit_eur:.2f} "
            f"({usage_info['budget_used_pct']:.1f}%)"
        )

        # Warning se vicini al limite
        if usage_info['budget_used_pct'] >= 80:
            logger.warning(f"⚠️ Budget giornaliero OpenAI quasi esaurito: {usage_info['budget_used_pct']:.1f}%")

        return usage_info

    def get_stats(self, days: int = 7) -> Dict:
        """
        Ritorna statistiche ultimi N giorni.

        Args:
            days: Numero giorni da includere

        Returns:
            Dict con statistiche
        """
        today = date.today()
        dates_to_check = [
            str(today - timedelta(days=i))
            for i in range(days)
        ]

        daily_costs = {
            d: self.usage_data['daily_usage'].get(d, 0.0)
            for d in dates_to_check
        }

        total_period = sum(daily_costs.values())
        avg_daily = total_period / days

        return {
            'daily_limit_eur': self.daily_limit_eur,
            'today_usage_eur': self.get_today_usage(),
            'today_remaining_eur': self.get_remaining_budget(),
            'period_days': days,
            'period_total_eur': total_period,
            'period_avg_daily_eur': avg_daily,
            'daily_costs': daily_costs,
            'total_requests_alltime': self.usage_data['total_requests'],
            'total_cost_alltime_eur': self.usage_data['total_cost_eur']
        }

    def reset_if_new_day(self):
        """Resetta contatori se è un nuovo giorno (chiamato automaticamente)."""
        today = str(date.today())
        if today not in self.usage_data['daily_usage']:
            logger.info(f"📅 Nuovo giorno: reset budget OpenAI (limite: €{self.daily_limit_eur})")


# Importa timedelta per stats
from datetime import timedelta


# Singleton globale
_rate_limiter_instance = None


def get_rate_limiter(daily_limit_eur: float = 1.0) -> OpenAIRateLimiter:
    """
    Ottieni istanza singleton del rate limiter.

    Args:
        daily_limit_eur: Limite giornaliero (solo prima inizializzazione)

    Returns:
        OpenAIRateLimiter
    """
    global _rate_limiter_instance

    if _rate_limiter_instance is None:
        _rate_limiter_instance = OpenAIRateLimiter(daily_limit_eur=daily_limit_eur)
        logger.info(f"✅ Rate limiter OpenAI inizializzato: €{daily_limit_eur}/giorno")

    return _rate_limiter_instance
