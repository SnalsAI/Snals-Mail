"""
Task Celery per processamento automatico email
"""

import logging
from app.tasks import celery_app
from app.database import SessionLocal
from app.models.email import Email, EmailStatus
from app.models.system_settings import SystemSettings
from app.services.action_executor import ActionExecutor

logger = logging.getLogger(__name__)


@celery_app.task(name='app.tasks.auto_process.auto_process_emails')
def auto_process_emails():
    """
    Processa automaticamente le email interpretate ma non ancora processate.

    Questa funzione:
    1. Controlla se il processamento automatico è abilitato
    2. Trova tutte le email con stato INTERPRETATA
    3. Le processa chiamando l'ActionExecutor
    """
    db = SessionLocal()

    try:
        # Controlla se processamento automatico è abilitato
        setting = db.query(SystemSettings).filter(
            SystemSettings.key == 'auto_process_enabled'
        ).first()

        if not setting or not setting.get_typed_value():
            logger.debug("Processamento automatico disabilitato")
            return {'status': 'skipped', 'reason': 'disabled'}

        # Trova email da processare (interpretate ma non ancora processate)
        emails_to_process = db.query(Email).filter(
            Email.stato == EmailStatus.INTERPRETATA
        ).all()

        if not emails_to_process:
            logger.info("Nessuna email da processare automaticamente")
            return {'status': 'success', 'processed': 0}

        logger.info(f"🤖 Processamento automatico: {len(emails_to_process)} email da processare")

        # Processa ogni email
        executor = ActionExecutor(db)
        processed_count = 0
        error_count = 0

        for email in emails_to_process:
            # Usa sessione separata per ogni email per evitare che un errore blocchi le altre
            email_db = SessionLocal()
            try:
                email_id = email.id
                email_oggetto = email.oggetto[:50] if email.oggetto else "N/A"
                logger.info(f"Processamento email {email_id}: {email_oggetto}...")

                # Crea executor con nuova sessione
                email_executor = ActionExecutor(email_db)

                # Esegui processamento - crea ed esegue le azioni per l'email
                actions = email_executor.execute_actions_for_email(email_id)

                if actions:
                    processed_count += 1
                    logger.info(f"✅ Email {email_id} processata con successo ({len(actions)} azioni create)")
                else:
                    # Nessuna azione creata - potrebbe essere normale per alcune categorie
                    logger.debug(f"📋 Email {email_id}: nessuna azione automatica necessaria")

            except Exception as e:
                error_count += 1
                logger.error(f"❌ Errore processamento email: {e}")
                try:
                    email_db.rollback()
                except:
                    pass
            finally:
                try:
                    email_db.close()
                except:
                    pass

        logger.info(f"🎯 Processamento automatico completato: {processed_count} OK, {error_count} errori")

        return {
            'status': 'success',
            'total': len(emails_to_process),
            'processed': processed_count,
            'errors': error_count
        }

    except Exception as e:
        logger.error(f"Errore processamento automatico: {e}", exc_info=True)
        return {
            'status': 'error',
            'error': str(e)
        }
    finally:
        db.close()


@celery_app.task(name='app.tasks.auto_process.fetch_and_process')
def fetch_and_process():
    """
    Scarica nuove email e le processa automaticamente.

    Questa è la funzione principale schedulata dal beat che:
    1. Scarica le email (chiama i task di polling)
    2. Aspetta il completamento
    3. Avvia il processamento automatico
    """
    from app.tasks.email_polling import poll_email_normal, poll_email_pec

    logger.info("🔄 Fetch and Process: inizio")

    try:
        # Scarica email
        logger.info("📥 Download email...")
        normal_result = poll_email_normal()
        pec_result = poll_email_pec()

        # Conta nuove email
        total_new = 0
        if isinstance(normal_result, dict):
            total_new += normal_result.get('new', 0)
        if isinstance(pec_result, dict):
            total_new += pec_result.get('new', 0)

        logger.info(f"📨 Scaricate {total_new} nuove email")

        # Processa automaticamente
        logger.info("🤖 Avvio processamento automatico...")
        process_result = auto_process_emails()

        return {
            'status': 'success',
            'fetch': {
                'normal': normal_result,
                'pec': pec_result,
                'total_new': total_new
            },
            'process': process_result
        }

    except Exception as e:
        logger.error(f"Errore fetch and process: {e}", exc_info=True)
        return {
            'status': 'error',
            'error': str(e)
        }
