"""
Task Celery per esecuzione azioni
"""

from app.tasks import celery_app
from app.services.action_executor import ActionExecutor
import logging

logger = logging.getLogger(__name__)


@celery_app.task(name='app.tasks.action_tasks.execute_email_actions')
def execute_email_actions(email_id: int):
    """
    Esegue azioni per email

    Args:
        email_id: ID email
    """
    logger.info(f"Esecuzione azioni per email {email_id}")

    try:
        executor = ActionExecutor()
        executor.execute_actions_for_email(email_id)
        logger.info(f"Azioni completate per email {email_id}")
    except Exception as e:
        logger.error(f"Errore esecuzione azioni email {email_id}: {e}")
        raise
