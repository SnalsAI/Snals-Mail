"""
Task Celery per polling periodico email
"""
import re
import json
import redis
from celery.exceptions import SoftTimeLimitExceeded
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

# Channel Redis per notifiche nuove email
EMAIL_NOTIFICATION_CHANNEL = "email_notifications"


def notify_new_emails(count: int, account_type: str):
    """Pubblica notifica su Redis quando arrivano nuove email."""
    if count <= 0:
        return

    try:
        redis_url = settings.REDIS_URL.replace("localhost", "redis")
        r = redis.from_url(redis_url)
        message = json.dumps({
            "type": "new_emails",
            "count": count,
            "account": account_type,
            "timestamp": datetime.now().isoformat()
        })
        r.publish(EMAIL_NOTIFICATION_CHANNEL, message)
        logger.info(f"📢 Notifica inviata: {count} nuove email ({account_type})")
        r.close()
    except Exception as e:
        logger.warning(f"Errore invio notifica Redis: {e}")


def extract_school_code(mittente: str) -> str | None:
    """
    Estrae il codice meccanografico dal mittente.
    Formato: 4 lettere + 6 caratteri alfanumerici (es: TAIC853001)
    """
    if not mittente:
        return None
    match = re.search(r'([a-z]{4}[a-z0-9]{6})@(pec\.)?istruzione\.it', mittente.lower())
    return match.group(1).upper() if match else None


@celery_app.task(
    name='app.tasks.email_polling.poll_email_normal',
    soft_time_limit=180,  # 3 minuti soft limit
    time_limit=240        # 4 minuti hard limit
)
def poll_email_normal():
    """Polling email account normale"""
    logger.info("Inizio polling email normale")

    try:
        client = EmailNormalClient()
        emails_data = client.fetch_emails(limit=settings.EMAIL_FETCH_LIMIT)

        if not emails_data:
            logger.info("Nessuna nuova email normale")
            return {"new": 0, "total": 0}

        db = SessionLocal()
        try:
            categorizer = EmailCategorizer()
            interpreter = EmailInterpreter()

            new_count = 0

            for email_data in emails_data:
                try:
                    existing = db.query(Email).filter(
                        Email.message_id == email_data['message_id']
                    ).first()

                    if existing:
                        continue

                    # Categorizza (con testo estratto dagli allegati)
                    try:
                        categoria, confidence, sottocategoria, proposta_info = categorizer.categorize(
                            mittente=email_data['mittente'],
                            oggetto=email_data['oggetto'],
                            corpo=email_data['corpo'],
                            attachment_paths=email_data.get('allegati_path', []),
                            allegati_testo=email_data.get('allegati_testo', {})
                        )
                    except Exception as e:
                        logger.error(f"❌ Errore CRITICO categorizzazione email: {e}")
                        from app.models.email import EmailCategory
                        # IMPORTANTE: Non usare "varie" ma marcare come DA_CATEGORIZZARE
                        # Questa email verrà riprocessata automaticamente
                        categoria = EmailCategory.DA_CATEGORIZZARE
                        confidence = 0.0
                        sottocategoria = "Errore categorizzazione"
                        proposta_info = {
                            'proposta': 'Riprocessamento richiesto',
                            'motivo': f'Errore durante categorizzazione: {str(e)[:200]}'
                        }

                    # Interpreta (con testo estratto dagli allegati)
                    try:
                        interpretazione_data = interpreter.interpret(
                            categoria=categoria,
                            mittente=email_data['mittente'],
                            oggetto=email_data['oggetto'],
                            corpo=email_data['corpo'],
                            allegati=email_data.get('allegati_nomi', []),
                            data_oggi=datetime.now().isoformat(),
                            attachment_paths=email_data.get('allegati_path', []),
                            allegati_testo=email_data.get('allegati_testo', {})
                        )
                    except Exception as e:
                        logger.warning(f"Errore interpretazione email, salto: {e}")
                        interpretazione_data = {"error": str(e)}

                    # Salva email
                    email_record = Email(
                        message_id=email_data['message_id'],
                        account_type=AccountType.NORMALE,
                        mittente=email_data['mittente'],
                        destinatario=email_data['destinatario'],
                        oggetto=email_data['oggetto'],
                        corpo=email_data['corpo'],
                        corpo_testo=email_data['corpo'],  # Stesso valore di corpo (plain text)
                        corpo_html=email_data.get('corpo_html'),  # HTML se disponibile
                        data_ricezione=email_data['data_ricezione'],
                        categoria=categoria.value,  # Usa .value per convertire Enum a string
                        categoria_confidence=confidence,
                        sottocategoria=sottocategoria,
                        codice_scuola=extract_school_code(email_data['mittente']),
                        stato=EmailStatus.INTERPRETATA,
                        allegati_nomi=email_data.get('allegati_nomi', []),
                        allegati_path=email_data.get('allegati_path', []),
                        allegati_testo=email_data.get('allegati_testo', {}),
                        # Gestione proposta sottocategoria
                        sottocategoria_proposta=proposta_info['proposta'] if proposta_info else None,
                        motivo_proposta=proposta_info['motivo'] if proposta_info else None,
                        richiede_revisione=True if proposta_info else False
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
                    db.flush()  # Assicurati che l'interpretazione sia salvata
                    logger.info(f"Salvata email: {email_data['oggetto'][:50]}")
                    new_count += 1

                    # Verifica se la scuola è nota, altrimenti genera proposta
                    if email_record.codice_scuola:
                        try:
                            from app.services.school_identifier import get_school_identifier
                            school_identifier = get_school_identifier()
                            school_info = school_identifier.get_school_info(email_record.codice_scuola)

                            if not school_info:
                                # Scuola sconosciuta - genera proposta
                                logger.info(f"🏫 Scuola {email_record.codice_scuola} sconosciuta, genero proposta...")
                                proposal = school_identifier.propose_new_school(
                                    email_record.codice_scuola,
                                    allegati_testo=email_data.get('allegati_testo', {})
                                )
                                if proposal:
                                    from app.services.school_updater import get_school_updater
                                    updater = get_school_updater()
                                    updater.add_pending_school(email_record.codice_scuola, proposal)
                        except Exception as e:
                            logger.warning(f"Errore verifica scuola: {e}")

                    # Crea azioni automatiche per questa email (async)
                    try:
                        from app.tasks.action_tasks import create_actions_for_email
                        create_actions_for_email.delay(email_record.id)
                        logger.info(f"🔄 Task creazione azioni schedulato per email {email_record.id}")
                    except Exception as e:
                        logger.warning(f"Errore scheduling azioni per email {email_record.id}: {e}")

                except Exception as e:
                    logger.error(f"❌ Errore fatale processando email {email_data.get('oggetto', 'N/A')[:50]}: {e}", exc_info=True)
                    # Skip questa email ma continua con le altre
                    continue

            db.commit()
            logger.info(f"Polling completato: {new_count} nuove email su {len(emails_data)} processate")

            # Notifica frontend se ci sono nuove email
            if new_count > 0:
                notify_new_emails(new_count, "normale")

            return {"new": new_count, "total": len(emails_data)}

        except Exception as e:
            db.rollback()
            logger.error(f"Errore salvataggio: {e}")
            raise
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Errore polling: {e}")


@celery_app.task(
    name='app.tasks.email_polling.poll_email_pec',
    soft_time_limit=180,  # 3 minuti soft limit
    time_limit=240        # 4 minuti hard limit
)
def poll_email_pec():
    """Polling email account PEC"""
    logger.info("Inizio polling email PEC")

    try:
        client = EmailPECClient()
        emails_data = client.fetch_emails(limit=settings.EMAIL_FETCH_LIMIT)

        if not emails_data:
            logger.info("Nessuna nuova email PEC")
            return {"new": 0, "total": 0}

        db = SessionLocal()
        try:
            categorizer = EmailCategorizer()
            interpreter = EmailInterpreter()

            new_count = 0

            for email_data in emails_data:
                try:
                    existing = db.query(Email).filter(
                        Email.message_id == email_data['message_id']
                    ).first()

                    if existing:
                        continue

                    # Categorizza (con testo estratto dagli allegati)
                    try:
                        categoria, confidence, sottocategoria, proposta_info = categorizer.categorize(
                            mittente=email_data['mittente'],
                            oggetto=email_data['oggetto'],
                            corpo=email_data['corpo'],
                            attachment_paths=email_data.get('allegati_path', []),
                            allegati_testo=email_data.get('allegati_testo', {})
                        )
                    except Exception as e:
                        logger.error(f"❌ Errore CRITICO categorizzazione email: {e}")
                        from app.models.email import EmailCategory
                        # IMPORTANTE: Non usare "varie" ma marcare come DA_CATEGORIZZARE
                        # Questa email verrà riprocessata automaticamente
                        categoria = EmailCategory.DA_CATEGORIZZARE
                        confidence = 0.0
                        sottocategoria = "Errore categorizzazione"
                        proposta_info = {
                            'proposta': 'Riprocessamento richiesto',
                            'motivo': f'Errore durante categorizzazione: {str(e)[:200]}'
                        }

                    # Interpreta (con testo estratto dagli allegati)
                    try:
                        interpretazione_data = interpreter.interpret(
                            categoria=categoria,
                            mittente=email_data['mittente'],
                            oggetto=email_data['oggetto'],
                            corpo=email_data['corpo'],
                            allegati=email_data.get('allegati_nomi', []),
                            data_oggi=datetime.now().isoformat(),
                            attachment_paths=email_data.get('allegati_path', []),
                            allegati_testo=email_data.get('allegati_testo', {})
                        )
                    except Exception as e:
                        logger.warning(f"Errore interpretazione email, salto: {e}")
                        interpretazione_data = {"error": str(e)}

                    # Salva email
                    email_record = Email(
                        message_id=email_data['message_id'],
                        account_type=AccountType.PEC,
                        mittente=email_data['mittente'],
                        destinatario=email_data['destinatario'],
                        oggetto=email_data['oggetto'],
                        corpo=email_data['corpo'],
                        corpo_testo=email_data['corpo'],  # Stesso valore di corpo (plain text)
                        corpo_html=email_data.get('corpo_html'),  # HTML se disponibile
                        data_ricezione=email_data['data_ricezione'],
                        categoria=categoria.value,  # Usa .value per convertire Enum a string
                        categoria_confidence=confidence,
                        sottocategoria=sottocategoria,
                        codice_scuola=extract_school_code(email_data['mittente']),
                        stato=EmailStatus.INTERPRETATA,
                        allegati_nomi=email_data.get('allegati_nomi', []),
                        allegati_path=email_data.get('allegati_path', []),
                        allegati_testo=email_data.get('allegati_testo', {})
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
                    db.flush()  # Assicurati che l'interpretazione sia salvata
                    logger.info(f"Salvata email PEC: {email_data['oggetto'][:50]}")
                    new_count += 1

                    # Verifica se la scuola è nota, altrimenti genera proposta
                    if email_record.codice_scuola:
                        try:
                            from app.services.school_identifier import get_school_identifier
                            school_identifier = get_school_identifier()
                            school_info = school_identifier.get_school_info(email_record.codice_scuola)

                            if not school_info:
                                # Scuola sconosciuta - genera proposta
                                logger.info(f"🏫 Scuola {email_record.codice_scuola} sconosciuta, genero proposta...")
                                proposal = school_identifier.propose_new_school(
                                    email_record.codice_scuola,
                                    allegati_testo=email_data.get('allegati_testo', {})
                                )
                                if proposal:
                                    from app.services.school_updater import get_school_updater
                                    updater = get_school_updater()
                                    updater.add_pending_school(email_record.codice_scuola, proposal)
                        except Exception as e:
                            logger.warning(f"Errore verifica scuola PEC: {e}")

                    # Crea azioni automatiche per questa email (async)
                    try:
                        from app.tasks.action_tasks import create_actions_for_email
                        create_actions_for_email.delay(email_record.id)
                        logger.info(f"🔄 Task creazione azioni schedulato per email PEC {email_record.id}")
                    except Exception as e_action:
                        logger.warning(f"Errore scheduling azioni per email PEC {email_record.id}: {e_action}")

                except Exception as e:
                    logger.error(f"❌ Errore fatale processando email PEC {email_data.get('oggetto', 'N/A')[:50]}: {e}", exc_info=True)
                    # Skip questa email ma continua con le altre
                    continue

            db.commit()
            logger.info(f"Polling PEC completato: {new_count} nuove email su {len(emails_data)} processate")

            # Notifica frontend se ci sono nuove email
            if new_count > 0:
                notify_new_emails(new_count, "pec")

            return {"new": new_count, "total": len(emails_data)}

        except Exception as e:
            db.rollback()
            logger.error(f"Errore salvataggio PEC: {e}")
            raise
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Errore polling PEC: {e}")
