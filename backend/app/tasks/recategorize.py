"""
Task Celery per riprocessare email con categorizzazione fallita
"""

from app.tasks import celery_app
from app.database import SessionLocal
from app.models.email import Email, EmailCategory
from app.services.categorizer import EmailCategorizer
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@celery_app.task(name='app.tasks.recategorize.retry_failed_categorizations')
def retry_failed_categorizations():
    """
    Riprocessa email con categoria DA_CATEGORIZZARE.

    Logica:
    - Trova tutte le email con categoria = 'da_categorizzare'
    - Limita a max 10 email per esecuzione per evitare sovraccarico
    - Riprova categorizzazione con sistema ibrido (rule-based + LLM)
    - Se categorizzazione ha successo, aggiorna email
    - Se fallisce ancora, mantiene DA_CATEGORIZZARE (verrà riprovato al prossimo ciclo)
    """
    logger.info("🔄 Inizio riprocessamento email con categorizzazione fallita")

    db = SessionLocal()
    try:
        # Trova email da ricategorizzare
        # Limita a 10 per esecuzione per non sovraccaricare il sistema
        emails_to_retry = db.query(Email).filter(
            Email.categoria == 'da_categorizzare'
        ).order_by(Email.created_at.desc()).limit(10).all()

        if not emails_to_retry:
            logger.info("✅ Nessuna email da riprocessare")
            return {"status": "success", "processed": 0, "success": 0, "failed": 0}

        logger.info(f"📧 Trovate {len(emails_to_retry)} email da riprocessare")

        categorizer = EmailCategorizer()
        success_count = 0
        failed_count = 0

        for email in emails_to_retry:
            try:
                logger.info(f"🔄 Riprocessamento email {email.id}: {email.oggetto[:50]}")

                # Riprova categorizzazione
                categoria, confidence, sottocategoria, proposta_info = categorizer.categorize(
                    mittente=email.mittente,
                    oggetto=email.oggetto,
                    corpo=email.corpo or "",
                    attachment_paths=email.allegati_path if email.allegati_path else [],
                    allegati_testo=email.allegati_testo if email.allegati_testo else {}
                )

                # Se la categorizzazione ha avuto successo (non è più DA_CATEGORIZZARE)
                if categoria != EmailCategory.DA_CATEGORIZZARE:
                    # Aggiorna email
                    email.categoria = categoria.value
                    email.categoria_confidence = confidence
                    email.sottocategoria = sottocategoria

                    # Aggiorna proposta se presente
                    if proposta_info:
                        email.sottocategoria_proposta = proposta_info.get('proposta')
                        email.motivo_proposta = proposta_info.get('motivo')
                        email.richiede_revisione = True
                    else:
                        email.richiede_revisione = False

                    db.commit()
                    success_count += 1
                    logger.info(f"✅ Email {email.id} ricategorizzata con successo: {categoria.value} (conf: {confidence})")
                else:
                    # Categorizzazione fallita ancora
                    failed_count += 1
                    logger.warning(f"⚠️ Email {email.id} ancora non categorizzabile, verrà riprovata al prossimo ciclo")

            except Exception as e:
                db.rollback()
                failed_count += 1
                logger.error(f"❌ Errore riprocessando email {email.id}: {e}", exc_info=True)

        logger.info(f"✅ Riprocessamento completato: {success_count} successo, {failed_count} fallite")

        return {
            "status": "success",
            "processed": len(emails_to_retry),
            "success": success_count,
            "failed": failed_count
        }

    except Exception as e:
        db.rollback()
        logger.error(f"❌ Errore durante riprocessamento: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}
    finally:
        db.close()


@celery_app.task(name='app.tasks.recategorize.recategorize_single_email')
def recategorize_single_email(email_id: int):
    """
    Riprocessa una singola email (per riprocessamento manuale dal frontend)

    Args:
        email_id: ID dell'email da riprocessare

    Returns:
        Dict con esito dell'operazione
    """
    logger.info(f"🔄 Riprocessamento manuale email {email_id}")

    db = SessionLocal()
    try:
        email = db.query(Email).filter(Email.id == email_id).first()

        if not email:
            logger.error(f"❌ Email {email_id} non trovata")
            return {"status": "error", "error": "Email non trovata"}

        categorizer = EmailCategorizer()

        # Riprova categorizzazione
        categoria, confidence, sottocategoria, proposta_info = categorizer.categorize(
            mittente=email.mittente,
            oggetto=email.oggetto,
            corpo=email.corpo or "",
            attachment_paths=email.allegati_path if email.allegati_path else [],
            allegati_testo=email.allegati_testo if email.allegati_testo else {}
        )

        # Aggiorna email
        old_categoria = email.categoria
        email.categoria = categoria.value
        email.categoria_confidence = confidence
        email.sottocategoria = sottocategoria

        # Aggiorna proposta se presente
        if proposta_info:
            email.sottocategoria_proposta = proposta_info.get('proposta')
            email.motivo_proposta = proposta_info.get('motivo')
            email.richiede_revisione = True
        else:
            email.richiede_revisione = False

        db.commit()

        logger.info(f"✅ Email {email_id} ricategorizzata: {old_categoria} → {categoria.value} (conf: {confidence})")

        return {
            "status": "success",
            "email_id": email_id,
            "old_categoria": old_categoria,
            "new_categoria": categoria.value,
            "confidence": confidence,
            "sottocategoria": sottocategoria
        }

    except Exception as e:
        db.rollback()
        logger.error(f"❌ Errore riprocessando email {email_id}: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}
    finally:
        db.close()
