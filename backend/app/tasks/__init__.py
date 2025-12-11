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
        'app.tasks.auto_process',
        'app.tasks.interpello_tasks',
        'app.tasks.draft_tasks',
        'app.tasks.recategorize',
    ]
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Europe/Rome',
    enable_utc=True,
    # Memory leak prevention: restart worker after N tasks
    worker_max_tasks_per_child=100,  # Ricrea worker dopo 100 task per evitare memory leak
    worker_max_memory_per_child=512000,  # Ricrea worker se supera 512MB di RAM (in KB)
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
    'fetch-and-process': {
        'task': 'app.tasks.auto_process.fetch_and_process',
        'schedule': 600.0,  # Ogni 10 minuti (configurabile da UI)
    },
    'check-expired-interpelli': {
        'task': 'app.tasks.interpello_tasks.check_expired_interpelli',
        'schedule': crontab(hour=2, minute=0),  # Ogni giorno alle 2:00
    },
    'retry-failed-categorizations': {
        'task': 'app.tasks.recategorize.retry_failed_categorizations',
        'schedule': 300.0,  # Ogni 5 minuti - riprova email con categorizzazione fallita
    },
    'worker-health-check': {
        'task': 'app.tasks.action_tasks.worker_health_check',
        'schedule': 300.0,  # Ogni 5 minuti - monitora salute worker
    },
}
