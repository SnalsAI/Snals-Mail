"""
Task sincronizzazione calendario
"""

from app.tasks import celery_app
from app.database import SessionLocal
from app.models.evento import EventoCalendario
from app.integrations.google_calendar import GoogleCalendarClient
import logging

logger = logging.getLogger(__name__)


@celery_app.task(name='app.tasks.calendar_sync.sync_events_to_google')
def sync_events_to_google():
    """Sincronizza eventi non sincronizzati su Google Calendar"""

    logger.info("Inizio sync eventi Google Calendar")

    db = SessionLocal()
    calendar_client = GoogleCalendarClient()

    try:
        # Eventi non ancora sincronizzati
        eventi = db.query(EventoCalendario).filter(
            EventoCalendario.sincronizzato == False
        ).limit(50).all()

        if not eventi:
            logger.info("Nessun evento da sincronizzare")
            return

        synced_count = 0

        for evento in eventi:
            try:
                google_event_id = calendar_client.create_event(
                    summary=evento.titolo,
                    description=evento.descrizione,
                    start_datetime=evento.data_inizio,
                    end_datetime=evento.data_fine or evento.data_inizio,
                    location=evento.luogo
                )

                if google_event_id:
                    evento.google_event_id = google_event_id
                    evento.sincronizzato = True
                    synced_count += 1

            except Exception as e:
                logger.error(f"Errore sync evento {evento.id}: {e}")

        db.commit()
        logger.info(f"Sincronizzati {synced_count} eventi")

    except Exception as e:
        logger.error(f"Errore generale sync calendario: {e}")
        db.rollback()
    finally:
        db.close()
