"""
Task Celery per polling periodico email
"""

from app.tasks import celery_app
from app.services.email_ingest import EmailNormalClient, EmailPECClient
from app.services.categorizer import EmailCategorizer
from app.services.interpreter import EmailInterpreter
from app.database import SessionLocal
from app.models.email import Email, AccountType, EmailStatus
from app.models.interpretazione import Interpretazione
from app.config import get_settings
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


@celery_app.task(name='app.tasks.email_polling.poll_email_normal')
def poll_email_normal():
    """Polling email account normale"""
    logger.info("Inizio polling email normale")
    
    try:
        client = EmailNormalClient()
        emails_data = client.fetch_emails(limit=50)
        
        if not emails_data:
            logger.info("Nessuna nuova email normale")
            return
        
        db = SessionLocal()
        try:
            categorizer = EmailCategorizer()
            interpreter = EmailInterpreter()
            
            for email_data in emails_data:
                existing = db.query(Email).filter(
                    Email.message_id == email_data['message_id']
                ).first()
                
                if existing:
                    continue
                
                # Categorizza
                categoria, confidence = categorizer.categorize(
                    mittente=email_data['mittente'],
                    oggetto=email_data['oggetto'],
                    corpo=email_data['corpo']
                )
                
                # Interpreta
                interpretazione_data = interpreter.interpret(
                    categoria=categoria,
                    mittente=email_data['mittente'],
                    oggetto=email_data['oggetto'],
                    corpo=email_data['corpo'],
                    allegati=[],
                    data_oggi=datetime.now().isoformat()
                )
                
                # Salva email
                email_record = Email(
                    message_id=email_data['message_id'],
                    account_type=AccountType.NORMALE,
                    mittente=email_data['mittente'],
                    destinatario=email_data['destinatario'],
                    oggetto=email_data['oggetto'],
                    corpo=email_data['corpo'],
                    data_ricezione=email_data['data_ricezione'],
                    categoria=categoria,
                    categoria_confidence=confidence,
                    stato=EmailStatus.INTERPRETATA
                )
                
                db.add(email_record)
                db.flush()
                
                # Salva interpretazione
                interp_record = Interpretazione(
                    email_id=email_record.id,
                    categoria=categoria.value,
                    interpretazione_json=interpretazione_data,
                    confidence=confidence,
                    richiede_revisione=(confidence < 0.7)
                )
                
                db.add(interp_record)
                logger.info(f"Salvata email: {email_data['oggetto'][:50]}")
            
            db.commit()
            logger.info(f"Polling completato: {len(emails_data)} email")
            
        except Exception as e:
            db.rollback()
            logger.error(f"Errore salvataggio: {e}")
            raise
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Errore polling: {e}")


@celery_app.task(name='app.tasks.email_polling.poll_email_pec')
def poll_email_pec():
    """Polling email account PEC"""
    logger.info("Inizio polling email PEC")
    # Implementazione simile a poll_email_normal
    pass
