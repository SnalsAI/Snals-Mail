"""
Celery app configuration
"""

from celery import Celery
from celery.schedules import crontab
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "snals_email_agent",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        'app.tasks.email_polling',
        'app.tasks.action_tasks',
    ]
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Europe/Rome',
    enable_utc=True,
)

celery_app.conf.beat_schedule = {
    'poll-email-normal': {
        'task': 'app.tasks.email_polling.poll_email_normal',
        'schedule': settings.EMAIL_POLL_INTERVAL,
    },
    'poll-email-pec': {
        'task': 'app.tasks.email_polling.poll_email_pec',
        'schedule': settings.EMAIL_POLL_INTERVAL,
    },
    'execute-pending-actions': {
        'task': 'app.tasks.action_tasks.execute_pending_actions',
        'schedule': 60.0,  # Ogni 60 secondi
    },
    'retry-failed-actions': {
        'task': 'app.tasks.action_tasks.retry_failed_actions',
        'schedule': 600.0,  # Ogni 10 minuti
    },
}
