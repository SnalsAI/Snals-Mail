"""
Celery Tasks per esecuzione azioni automatiche.

FASE 4: Azioni Automatiche
"""
import logging
from sqlalchemy.orm import Session

from app.tasks import celery_app
from app.database import SessionLocal
from app.services.action_executor import ActionExecutor
from app.models.azione import Azione, StatoAzione

logger = logging.getLogger(__name__)


@celery_app.task(name='app.tasks.action_tasks.execute_pending_actions', bind=True)
def execute_pending_actions(self):
    """
    Task periodico per eseguire azioni pending.

    Viene eseguito ogni 60 secondi per processare le azioni in coda.
    """
    logger.info("🔄 Esecuzione azioni pending...")

    db = SessionLocal()
    try:
        # Trova azioni pending
        azioni_pending = db.query(Azione).filter(
            Azione.stato == StatoAzione.PENDING
        ).limit(10).all()

        if not azioni_pending:
            logger.info("✅ Nessuna azione pending")
            return {
                'status': 'success',
                'azioni_processate': 0
            }

        executor = ActionExecutor(db)
        success_count = 0
        failed_count = 0

        for azione in azioni_pending:
            try:
                logger.info(f"Esecuzione azione {azione.id} ({azione.tipo_azione.value})...")
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

    except Exception as e:
        logger.error(f"❌ Errore task execute_pending_actions: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }
    finally:
        db.close()


@celery_app.task(name='app.tasks.action_tasks.create_actions_for_email', bind=True)
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


@celery_app.task(name='app.tasks.action_tasks.retry_failed_actions', bind=True)
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
                # Resetta stato a pending
                azione.stato = StatoAzione.PENDING
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
