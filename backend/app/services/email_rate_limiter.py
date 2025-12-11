"""
Email Rate Limiter Service.

Previene il blocco dell'IP limitando la frequenza di invio email.
"""
import logging
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from threading import RLock

logger = logging.getLogger(__name__)


class EmailRateLimiter:
    """
    Gestisce il rate limiting per l'invio email.

    Implementa:
    - Limite email per ora
    - Limite email per minuto
    - Delay minimo tra invii
    - Tracking email inviate
    """

    _instance = None
    _lock = RLock()

    def __new__(cls):
        """Singleton pattern per condividere stato tra thread."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True

        # Configurazione rate limits (possono essere sovrascritti da settings)
        self.max_emails_per_hour = 100     # Max 100 email/ora
        self.max_emails_per_minute = 10    # Max 10 email/minuto
        self.min_delay_seconds = 3         # Minimo 3 secondi tra invii
        self.burst_delay_seconds = 15      # Pausa di 15 secondi dopo burst
        self.burst_threshold = 5           # Dopo 5 email consecutive, pausa
        self.max_wait_seconds = 60         # Timeout massimo attesa (1 minuto) - NON bloccare oltre

        # Tracking
        self.sent_timestamps: list[datetime] = []
        self.consecutive_sends = 0
        self.last_send_time: Optional[datetime] = None

        # RLock per thread safety (rientrante per evitare deadlock)
        self._send_lock = RLock()

        logger.info(f"📧 Rate Limiter inizializzato: max {self.max_emails_per_hour}/ora, "
                   f"{self.max_emails_per_minute}/min, delay {self.min_delay_seconds}s")

    def configure(self,
                  max_per_hour: int = None,
                  max_per_minute: int = None,
                  min_delay: int = None,
                  burst_delay: int = None,
                  burst_threshold: int = None):
        """
        Configura i limiti del rate limiter.

        Args:
            max_per_hour: Massimo email per ora
            max_per_minute: Massimo email per minuto
            min_delay: Delay minimo tra invii (secondi)
            burst_delay: Pausa dopo burst (secondi)
            burst_threshold: Numero email prima della pausa burst
        """
        if max_per_hour is not None:
            self.max_emails_per_hour = max_per_hour
        if max_per_minute is not None:
            self.max_emails_per_minute = max_per_minute
        if min_delay is not None:
            self.min_delay_seconds = min_delay
        if burst_delay is not None:
            self.burst_delay_seconds = burst_delay
        if burst_threshold is not None:
            self.burst_threshold = burst_threshold

        logger.info(f"📧 Rate Limiter riconfigurato: max {self.max_emails_per_hour}/ora, "
                   f"{self.max_emails_per_minute}/min")

    def _clean_old_timestamps(self):
        """Rimuove timestamp più vecchi di 1 ora."""
        cutoff = datetime.now() - timedelta(hours=1)
        self.sent_timestamps = [ts for ts in self.sent_timestamps if ts > cutoff]

    def get_emails_sent_last_hour(self) -> int:
        """Ritorna il numero di email inviate nell'ultima ora."""
        self._clean_old_timestamps()
        return len(self.sent_timestamps)

    def get_emails_sent_last_minute(self) -> int:
        """Ritorna il numero di email inviate nell'ultimo minuto."""
        cutoff = datetime.now() - timedelta(minutes=1)
        return len([ts for ts in self.sent_timestamps if ts > cutoff])

    def can_send(self) -> tuple[bool, Optional[str], Optional[int]]:
        """
        Verifica se è possibile inviare una email.

        Returns:
            tuple: (can_send, reason, wait_seconds)
        """
        with self._send_lock:
            self._clean_old_timestamps()

            # Check limite orario
            emails_last_hour = self.get_emails_sent_last_hour()
            if emails_last_hour >= self.max_emails_per_hour:
                oldest = min(self.sent_timestamps) if self.sent_timestamps else datetime.now()
                wait = int((oldest + timedelta(hours=1) - datetime.now()).total_seconds())
                return False, f"Limite orario raggiunto ({emails_last_hour}/{self.max_emails_per_hour})", max(1, wait)

            # Check limite al minuto
            emails_last_minute = self.get_emails_sent_last_minute()
            if emails_last_minute >= self.max_emails_per_minute:
                return False, f"Limite al minuto raggiunto ({emails_last_minute}/{self.max_emails_per_minute})", 60

            # Check burst threshold
            if self.consecutive_sends >= self.burst_threshold:
                return False, f"Pausa anti-burst dopo {self.consecutive_sends} invii consecutivi", self.burst_delay_seconds

            return True, None, 0

    def wait_if_needed(self) -> Dict[str, Any]:
        """
        Attende se necessario prima di inviare.

        IMPORTANTE: Non usa lock durante sleep per evitare deadlock tra worker.

        Returns:
            dict: Info sull'attesa effettuata, incluso 'rate_limited' se non si può inviare
        """
        result = {
            'waited': False,
            'wait_seconds': 0,
            'reason': None,
            'rate_limited': False
        }

        # Calcola tempo di attesa senza tenere il lock
        wait_time = 0
        reason = None

        with self._send_lock:
            # Verifica delay minimo dall'ultimo invio
            if self.last_send_time:
                elapsed = (datetime.now() - self.last_send_time).total_seconds()
                if elapsed < self.min_delay_seconds:
                    wait_time = min(self.min_delay_seconds - elapsed, self.max_wait_seconds)
                    reason = 'min_delay'

            # Verifica altri limiti solo se non dobbiamo già aspettare
            if wait_time == 0:
                can_send, limit_reason, wait_seconds = self.can_send()
                if not can_send and wait_seconds > 0:
                    wait_time = min(wait_seconds, self.max_wait_seconds)
                    reason = limit_reason
                    if wait_seconds > self.max_wait_seconds:
                        result['rate_limited'] = True

        # Sleep FUORI dal lock per non bloccare altri worker
        if wait_time > 0:
            logger.info(f"⏳ Rate limit: attendo {wait_time:.1f}s ({reason})")
            time.sleep(wait_time)
            result['waited'] = True
            result['wait_seconds'] = wait_time
            result['reason'] = reason

        return result

    def record_send(self, success: bool = True):
        """
        Registra un invio email.

        Args:
            success: Se l'invio è andato a buon fine
        """
        with self._send_lock:
            now = datetime.now()

            if success:
                self.sent_timestamps.append(now)
                self.consecutive_sends += 1
                self.last_send_time = now

                logger.debug(f"📧 Email registrata: {self.get_emails_sent_last_hour()}/ora, "
                           f"{self.consecutive_sends} consecutive")
            else:
                # Su errore, aggiungi pausa extra per sicurezza
                self.consecutive_sends = 0

    def reset_burst_counter(self):
        """Reset del contatore burst (chiamare dopo pause naturali)."""
        with self._send_lock:
            self.consecutive_sends = 0

    def get_status(self) -> Dict[str, Any]:
        """Ritorna lo stato corrente del rate limiter."""
        return {
            'emails_last_hour': self.get_emails_sent_last_hour(),
            'emails_last_minute': self.get_emails_sent_last_minute(),
            'max_per_hour': self.max_emails_per_hour,
            'max_per_minute': self.max_emails_per_minute,
            'consecutive_sends': self.consecutive_sends,
            'min_delay_seconds': self.min_delay_seconds,
            'can_send': self.can_send()[0]
        }


# Singleton instance
_rate_limiter: Optional[EmailRateLimiter] = None


def get_email_rate_limiter() -> EmailRateLimiter:
    """Ottiene l'istanza singleton del rate limiter."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = EmailRateLimiter()
    return _rate_limiter
