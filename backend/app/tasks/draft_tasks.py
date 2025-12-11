"""
Celery Tasks per generazione bozze di risposta in background.

Permette la generazione intelligente di draft con RAG usando timeout lunghi,
senza bloccare il sistema principale.
"""

import logging
from datetime import datetime
from sqlalchemy.orm import Session

from app.tasks import celery_app
from app.database import SessionLocal
from app.services.draft_generator import SmartDraftGenerator
from app.models.email import Email
from app.models.azione import Azione, StatoAzione

logger = logging.getLogger(__name__)


@celery_app.task(
    name='app.tasks.draft_tasks.generate_smart_draft',
    bind=True,
    max_retries=2,
    default_retry_delay=180,  # 3 minuti tra i retry
    time_limit=300,  # 5 minuti massimo
    soft_time_limit=270  # Warning dopo 4.5 minuti
)
def generate_smart_draft(self, email_id: int, azione_id: int = None):
    """
    Task per generazione draft intelligente con RAG in background.

    Args:
        email_id: ID dell'email per cui generare draft
        azione_id: ID dell'azione associata (opzionale)

    Returns:
        dict con risultato della generazione
    """
    db = SessionLocal()

    try:
        logger.info(f"📝 Inizio generazione draft intelligente per email {email_id}")

        # Recupera email
        email = db.query(Email).filter(Email.id == email_id).first()
        if not email:
            logger.error(f"Email {email_id} non trovata")
            if azione_id:
                _update_azione_failed(db, azione_id, "Email non trovata")
            return {'status': 'error', 'error': 'Email non trovata'}

        # Aggiorna stato azione se presente
        if azione_id:
            azione = db.query(Azione).filter(Azione.id == azione_id).first()
            if azione:
                azione.stato = StatoAzione.IN_ESECUZIONE
                db.commit()

        # Inizializza generatore
        generator = SmartDraftGenerator()

        # Genera draft con contesto RAG (timeout 3 minuti)
        try:
            result = generator.generate_draft_with_context(
                email=email,
                categoria=email.categoria,
                timeout=180.0
            )

            draft_text = result['draft']
            referenced_docs = result['referenced_documents']
            context_summary = result['context_summary']

            logger.info(
                f"✅ Draft generata per email {email_id}: "
                f"{len(draft_text)} caratteri, "
                f"{len(referenced_docs)} documenti referenziati"
            )

            # Prepara risultato
            final_result = {
                'status': 'generated',
                'draft': draft_text,
                'referenced_documents': referenced_docs,
                'context_summary': context_summary,
                'metadata': result['metadata'],
                'email_id': email_id
            }

            # Aggiorna azione se presente
            if azione_id:
                _update_azione_completed(db, azione_id, final_result)

            return final_result

        except Exception as e:
            # Se fallisce con RAG, prova fallback senza RAG
            logger.warning(f"Errore generazione draft con RAG: {e}, tento fallback semplice...")

            try:
                draft_text = generator.generate_simple_draft(
                    email=email,
                    categoria=email.categoria,
                    timeout=120.0
                )

                fallback_result = {
                    'status': 'generated_fallback',
                    'draft': draft_text,
                    'referenced_documents': [],
                    'context_summary': 'Draft generata senza knowledge base (fallback)',
                    'metadata': {
                        'generated_at': datetime.utcnow().isoformat(),
                        'fallback': True,
                        'original_error': str(e)
                    },
                    'email_id': email_id
                }

                if azione_id:
                    _update_azione_completed(db, azione_id, fallback_result)

                logger.info(f"✅ Draft fallback generata per email {email_id}")
                return fallback_result

            except Exception as e2:
                logger.error(f"❌ Errore anche con draft fallback: {e2}")
                raise e2

    except Exception as e:
        logger.error(f"❌ Errore generazione draft email {email_id}: {e}", exc_info=True)

        if azione_id:
            _update_azione_failed(db, azione_id, str(e))

        # Retry automatico
        if self.request.retries < self.max_retries:
            logger.info(f"Retry {self.request.retries + 1}/{self.max_retries} tra 3 minuti...")
            raise self.retry(exc=e)

        return {
            'status': 'error',
            'error': str(e),
            'email_id': email_id
        }

    finally:
        db.close()


def _update_azione_completed(db: Session, azione_id: int, result: dict):
    """Aggiorna azione come completata"""
    try:
        azione = db.query(Azione).filter(Azione.id == azione_id).first()
        if azione:
            azione.stato = StatoAzione.COMPLETATA
            azione.risultato = result
            azione.timestamp_fine = datetime.utcnow()
            db.commit()
            logger.info(f"Azione {azione_id} marcata come COMPLETATA")
    except Exception as e:
        logger.error(f"Errore aggiornamento azione {azione_id}: {e}")


def _update_azione_failed(db: Session, azione_id: int, error_msg: str):
    """Aggiorna azione come fallita"""
    try:
        azione = db.query(Azione).filter(Azione.id == azione_id).first()
        if azione:
            azione.stato = StatoAzione.FALLITA
            azione.errore = error_msg
            azione.risultato = {'error': error_msg}
            azione.timestamp_fine = datetime.utcnow()
            db.commit()
            logger.info(f"Azione {azione_id} marcata come FALLITA: {error_msg}")
    except Exception as e:
        logger.error(f"Errore aggiornamento azione {azione_id}: {e}")
