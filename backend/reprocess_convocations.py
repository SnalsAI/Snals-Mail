#!/usr/bin/env python3
"""
Script per riprocessare tutte le email con convocazioni e rigenerare eventi calendario.
"""

import sys
import os

# Aggiungi la directory app al path
sys.path.insert(0, '/app')

from app.database import SessionLocal
from app.models.email import Email
from app.tasks import celery_app
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reprocess_convocations():
    """Riprocessa tutte le email con categoria convocazione_scuola"""
    db = SessionLocal()

    try:
        # Trova tutte le email con convocazioni
        emails = db.query(Email).filter(
            Email.categoria == 'convocazione_scuola'
        ).order_by(Email.id).all()

        logger.info(f"🔄 Trovate {len(emails)} email con convocazioni da riprocessare")

        for email in emails:
            logger.info(f"📧 Triggering action creation for email {email.id}: {email.oggetto[:60]}...")

            # Triggera task Celery per creare azioni
            from app.tasks.action_tasks import create_actions_for_email
            result = create_actions_for_email.delay(email.id)

            logger.info(f"  ✅ Task scheduled: {result.id}")

        logger.info(f"✅ Completato! Schedulati {len(emails)} task per riprocessamento")

    except Exception as e:
        logger.error(f"❌ Errore durante riprocessamento: {e}")
        raise
    finally:
        db.close()

if __name__ == '__main__':
    reprocess_convocations()
