"""
Servizio coda LLM - Gestisce l'elaborazione sequenziale delle richieste LLM.

Uso:
    from app.services.llm_queue_service import llm_queue

    # Aggiungi richiesta alla coda
    request_id = llm_queue.enqueue(
        tipo="evento_calendario",
        prompt="Estrai i dati...",
        riferimento_tipo="azione",
        riferimento_id=123
    )

    # Controlla stato
    result = llm_queue.get_result(request_id)

    # Oppure attendi risultato (bloccante)
    result = llm_queue.wait_for_result(request_id, timeout=60)
"""

import logging
import threading
import time
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.llm_queue import RichiestaLLM, StatoRichiestaLLM
from app.integrations.llm_client import LLMClient

logger = logging.getLogger(__name__)


class LLMQueueService:
    """Servizio per gestire la coda di richieste LLM"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern"""
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
        self._processing = False
        self._worker_thread = None
        self._stop_event = threading.Event()
        self._llm_client = LLMClient()

        logger.info("🔄 LLMQueueService inizializzato")

    def enqueue(
        self,
        tipo: str,
        prompt: str,
        model_type: str = "interpretation",
        format_json: bool = False,
        riferimento_tipo: str = None,
        riferimento_id: int = None,
        priorita: int = 5
    ) -> int:
        """
        Aggiunge una richiesta alla coda.

        Args:
            tipo: Tipo di richiesta (es: "evento_calendario", "sintesi")
            prompt: Il prompt da inviare al LLM
            model_type: Tipo di modello da usare
            format_json: Se True, richiede risposta JSON
            riferimento_tipo: Tipo oggetto di riferimento (es: "azione")
            riferimento_id: ID oggetto di riferimento
            priorita: Priorità (1=alta, 10=bassa)

        Returns:
            ID della richiesta in coda
        """
        db = SessionLocal()
        try:
            richiesta = RichiestaLLM(
                tipo=tipo,
                prompt=prompt,
                model_type=model_type,
                format_json=1 if format_json else 0,
                riferimento_tipo=riferimento_tipo,
                riferimento_id=riferimento_id,
                priorita=priorita,
                stato=StatoRichiestaLLM.IN_CODA.value
            )
            db.add(richiesta)
            db.commit()
            db.refresh(richiesta)

            request_id = richiesta.id
            logger.info(f"📥 Richiesta LLM {request_id} aggiunta alla coda (tipo: {tipo})")

            # Avvia worker se non attivo
            self._ensure_worker_running()

            return request_id

        finally:
            db.close()

    def get_result(self, request_id: int) -> Optional[Dict[str, Any]]:
        """
        Ottiene il risultato di una richiesta (non bloccante).

        Returns:
            Dict con stato e risultato, o None se non trovata
        """
        db = SessionLocal()
        try:
            richiesta = db.query(RichiestaLLM).filter(RichiestaLLM.id == request_id).first()
            if not richiesta:
                return None

            return {
                "id": richiesta.id,
                "stato": richiesta.stato,
                "risposta": richiesta.risposta,
                "risposta_parsed": richiesta.risposta_parsed,
                "errore": richiesta.errore,
                "completed_at": richiesta.completed_at
            }
        finally:
            db.close()

    def wait_for_result(self, request_id: int, timeout: int = 120, poll_interval: float = 0.5) -> Optional[Dict[str, Any]]:
        """
        Attende il risultato di una richiesta (bloccante).

        Args:
            request_id: ID della richiesta
            timeout: Timeout in secondi
            poll_interval: Intervallo di polling in secondi

        Returns:
            Dict con risultato o None se timeout
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            result = self.get_result(request_id)

            if result and result["stato"] in [StatoRichiestaLLM.COMPLETATA.value, StatoRichiestaLLM.FALLITA.value]:
                return result

            time.sleep(poll_interval)

        logger.warning(f"⏱️ Timeout attesa risultato richiesta {request_id}")
        return None

    def _ensure_worker_running(self):
        """Assicura che il worker sia in esecuzione"""
        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._stop_event.clear()
            self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self._worker_thread.start()
            logger.info("🚀 Worker LLM avviato")

    def _worker_loop(self):
        """Loop del worker che processa le richieste una alla volta"""
        logger.info("🔄 Worker LLM loop avviato")
        consecutive_errors = 0
        max_consecutive_errors = 10

        while not self._stop_event.is_set():
            try:
                processed = self._process_next_request()
                consecutive_errors = 0  # Reset su successo

                if not processed:
                    # Nessuna richiesta in coda, attendi un po'
                    time.sleep(1)
                else:
                    # Pausa tra le richieste per non sovraccaricare Ollama
                    time.sleep(2)

            except Exception as e:
                consecutive_errors += 1
                logger.error(f"❌ Errore nel worker LLM ({consecutive_errors}/{max_consecutive_errors}): {e}")
                import traceback
                logger.error(traceback.format_exc())

                if consecutive_errors >= max_consecutive_errors:
                    logger.error("🛑 Troppi errori consecutivi, riavvio worker...")
                    consecutive_errors = 0
                    time.sleep(10)
                else:
                    time.sleep(5)

        logger.info("🛑 Worker LLM loop terminato")

    def _ensure_worker_running(self):
        """Assicura che il worker sia in esecuzione"""
        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._stop_event.clear()
            self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True, name="LLMQueueWorker")
            self._worker_thread.start()
            logger.info("🚀 Worker LLM avviato")

    def _process_next_request(self) -> bool:
        """
        Processa la prossima richiesta in coda.

        Returns:
            True se ha processato una richiesta, False se coda vuota
        """
        db = SessionLocal()
        try:
            # Prendi la prossima richiesta (per priorità e data)
            richiesta = db.query(RichiestaLLM).filter(
                RichiestaLLM.stato == StatoRichiestaLLM.IN_CODA.value
            ).order_by(
                RichiestaLLM.priorita,
                RichiestaLLM.created_at
            ).first()

            if not richiesta:
                return False

            # Marca come in elaborazione
            richiesta.stato = StatoRichiestaLLM.IN_ELABORAZIONE.value
            richiesta.started_at = datetime.utcnow()
            db.commit()

            logger.info(f"⚙️ Elaborazione richiesta LLM {richiesta.id} (tipo: {richiesta.tipo})")

            try:
                # Esegui chiamata LLM
                response = self._llm_client.generate(
                    prompt=richiesta.prompt,
                    model_type=richiesta.model_type,
                    format_json=bool(richiesta.format_json),
                    timeout=180  # Timeout molto generoso per server lenti
                )

                # Salva risposta
                richiesta.risposta = response
                richiesta.stato = StatoRichiestaLLM.COMPLETATA.value
                richiesta.completed_at = datetime.utcnow()

                # Parse JSON se richiesto
                if richiesta.format_json and response:
                    try:
                        parsed = self._llm_client.parse_json_response(response)
                        richiesta.risposta_parsed = parsed
                    except Exception as parse_err:
                        logger.warning(f"⚠️ Errore parsing JSON: {parse_err}")

                logger.info(f"✅ Richiesta LLM {richiesta.id} completata")

            except Exception as e:
                richiesta.stato = StatoRichiestaLLM.FALLITA.value
                richiesta.errore = str(e)
                richiesta.completed_at = datetime.utcnow()
                logger.error(f"❌ Richiesta LLM {richiesta.id} fallita: {e}")

            db.commit()
            return True

        except Exception as e:
            logger.error(f"❌ Errore processamento coda: {e}")
            db.rollback()
            return False

        finally:
            db.close()

    def stop_worker(self):
        """Ferma il worker"""
        self._stop_event.set()
        if self._worker_thread:
            self._worker_thread.join(timeout=10)
        logger.info("🛑 Worker LLM fermato")

    def get_queue_stats(self) -> Dict[str, int]:
        """Ottiene statistiche sulla coda"""
        db = SessionLocal()
        try:
            in_coda = db.query(RichiestaLLM).filter(
                RichiestaLLM.stato == StatoRichiestaLLM.IN_CODA.value
            ).count()

            in_elaborazione = db.query(RichiestaLLM).filter(
                RichiestaLLM.stato == StatoRichiestaLLM.IN_ELABORAZIONE.value
            ).count()

            completate = db.query(RichiestaLLM).filter(
                RichiestaLLM.stato == StatoRichiestaLLM.COMPLETATA.value
            ).count()

            fallite = db.query(RichiestaLLM).filter(
                RichiestaLLM.stato == StatoRichiestaLLM.FALLITA.value
            ).count()

            return {
                "in_coda": in_coda,
                "in_elaborazione": in_elaborazione,
                "completate": completate,
                "fallite": fallite,
                "worker_attivo": self._worker_thread is not None and self._worker_thread.is_alive()
            }
        finally:
            db.close()

    def clear_old_requests(self, days: int = 7):
        """Pulisce richieste completate più vecchie di X giorni"""
        from datetime import timedelta

        db = SessionLocal()
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)
            deleted = db.query(RichiestaLLM).filter(
                RichiestaLLM.stato.in_([StatoRichiestaLLM.COMPLETATA.value, StatoRichiestaLLM.FALLITA.value]),
                RichiestaLLM.completed_at < cutoff
            ).delete()
            db.commit()
            logger.info(f"🧹 Eliminate {deleted} richieste LLM vecchie")
            return deleted
        finally:
            db.close()


# Singleton instance
llm_queue = LLMQueueService()


def get_llm_queue() -> LLMQueueService:
    """Ottiene l'istanza del servizio coda LLM"""
    return llm_queue
