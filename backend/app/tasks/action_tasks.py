"""
Celery Tasks per esecuzione azioni automatiche.

FASE 4: Azioni Automatiche
"""
import logging
from sqlalchemy.orm import Session
from celery.exceptions import SoftTimeLimitExceeded

from app.tasks import celery_app
from app.database import SessionLocal
from app.services.action_executor import ActionExecutor
from app.models.azione import Azione, StatoAzione

logger = logging.getLogger(__name__)


@celery_app.task(
    name='app.tasks.action_tasks.execute_pending_actions',
    bind=True,
    soft_time_limit=1200,  # 20 minuti soft limit (per rate limiting email)
    time_limit=1500        # 25 minuti hard limit
)
def execute_pending_actions(self):
    """
    Task periodico per eseguire azioni pending.

    Viene eseguito ogni 60 secondi per processare le azioni in coda.
    """
    logger.info("🔄 Esecuzione azioni pending...")

    db = SessionLocal()
    try:
        # Trova azioni in coda
        azioni_pending = db.query(Azione).filter(
            Azione.stato == StatoAzione.IN_CODA
        ).limit(10).all()

        if not azioni_pending:
            logger.info("✅ Nessuna azione in coda")
            return {
                'status': 'success',
                'azioni_processate': 0
            }

        executor = ActionExecutor(db)
        success_count = 0
        failed_count = 0

        for azione in azioni_pending:
            try:
                logger.info(f"Esecuzione azione {azione.id} ({azione.tipo.value})...")
                success = executor.execute_action(azione.id)

                if success:
                    success_count += 1
                    logger.info(f"✅ Azione {azione.id} completata")
                else:
                    failed_count += 1
                    logger.warning(f"⚠️ Azione {azione.id} fallita")

            except Exception as e:
                failed_count += 1
                logger.error(f"❌ Errore esecuzione azione {azione.id}: {e}")

        logger.info(f"✅ Processate {len(azioni_pending)} azioni: {success_count} successi, {failed_count} fallimenti")

        return {
            'status': 'success',
            'azioni_processate': len(azioni_pending),
            'success': success_count,
            'failed': failed_count
        }

    except SoftTimeLimitExceeded:
        logger.error("⏰ TIMEOUT: execute_pending_actions ha superato il tempo limite!")
        return {
            'status': 'timeout',
            'error': 'Task timeout - possibile blocco nelle azioni',
            'azioni_processate': success_count + failed_count,
            'success': success_count,
            'failed': failed_count
        }
    except Exception as e:
        logger.error(f"❌ Errore task execute_pending_actions: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }
    finally:
        db.close()


@celery_app.task(
    name='app.tasks.action_tasks.create_actions_for_email',
    bind=True,
    soft_time_limit=180,  # 3 minuti soft limit
    time_limit=240        # 4 minuti hard limit
)
def create_actions_for_email(self, email_id: int):
    """
    Task per creare azioni per una email specifica.

    Args:
        email_id: ID dell'email

    Returns:
        dict: Risultato task
    """
    logger.info(f"🔄 Creazione azioni per email {email_id}...")

    db = SessionLocal()
    try:
        executor = ActionExecutor(db)
        azioni = executor.execute_actions_for_email(email_id)

        logger.info(f"✅ Create {len(azioni)} azioni per email {email_id}")

        return {
            'status': 'success',
            'email_id': email_id,
            'azioni_create': len(azioni),
            'azioni_ids': [a.id for a in azioni]
        }

    except Exception as e:
        logger.error(f"❌ Errore creazione azioni per email {email_id}: {e}")
        return {
            'status': 'error',
            'email_id': email_id,
            'error': str(e)
        }
    finally:
        db.close()


@celery_app.task(
    name='app.tasks.action_tasks.retry_failed_actions',
    bind=True,
    soft_time_limit=1200,  # 20 minuti soft limit (per rate limiting email)
    time_limit=1500        # 25 minuti hard limit
)
def retry_failed_actions(self, max_retries: int = 3):
    """
    Task per ritentare azioni fallite.

    Args:
        max_retries: Numero massimo retry per azione

    Returns:
        dict: Risultato task
    """
    logger.info("🔄 Retry azioni fallite...")

    db = SessionLocal()
    try:
        # Trova azioni fallite con retry < max
        azioni_fallite = db.query(Azione).filter(
            Azione.stato == StatoAzione.FALLITA
        ).limit(10).all()

        if not azioni_fallite:
            logger.info("✅ Nessuna azione fallita da ritentare")
            return {
                'status': 'success',
                'azioni_ritentate': 0
            }

        executor = ActionExecutor(db)
        retried_count = 0
        success_count = 0

        for azione in azioni_fallite:
            try:
                # Resetta stato a in_coda
                azione.stato = StatoAzione.IN_CODA
                azione.errore = None
                db.commit()

                # Riprova esecuzione
                success = executor.execute_action(azione.id)

                retried_count += 1
                if success:
                    success_count += 1
                    logger.info(f"✅ Azione {azione.id} ritentata con successo")
                else:
                    logger.warning(f"⚠️ Azione {azione.id} ancora fallita")

            except Exception as e:
                logger.error(f"❌ Errore retry azione {azione.id}: {e}")

        logger.info(f"✅ Ritentate {retried_count} azioni: {success_count} successi")

        return {
            'status': 'success',
            'azioni_ritentate': retried_count,
            'success': success_count
        }

    except Exception as e:
        logger.error(f"❌ Errore task retry_failed_actions: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }
    finally:
        db.close()


@celery_app.task(
    name='app.tasks.action_tasks.worker_health_check',
    bind=True,
    soft_time_limit=30,
    time_limit=60
)
def worker_health_check(self):
    """
    Task watchdog per monitorare la salute del worker.

    Questo task viene eseguito ogni 5 minuti e:
    1. Verifica che il worker risponda
    2. Logga statistiche sul rate limiter
    3. Rileva eventuali blocchi
    """
    from datetime import datetime
    from app.services.email_rate_limiter import get_email_rate_limiter

    logger.info("🔍 Health check worker...")

    try:
        # Check rate limiter status
        rate_limiter = get_email_rate_limiter()
        status = rate_limiter.get_status()

        logger.info(
            f"📊 Rate limiter: {status['emails_last_hour']}/{status['max_per_hour']} email/ora, "
            f"{status['emails_last_minute']}/{status['max_per_minute']} email/min, "
            f"consecutive: {status['consecutive_sends']}, can_send: {status['can_send']}"
        )

        # Check pending actions count
        db = SessionLocal()
        try:
            pending_count = db.query(Azione).filter(
                Azione.stato == StatoAzione.IN_CODA
            ).count()

            failed_count = db.query(Azione).filter(
                Azione.stato == StatoAzione.FALLITA
            ).count()

            logger.info(f"📋 Azioni: {pending_count} in coda, {failed_count} fallite")

        finally:
            db.close()

        return {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'rate_limiter': status,
            'azioni_pending': pending_count,
            'azioni_failed': failed_count
        }

    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }
