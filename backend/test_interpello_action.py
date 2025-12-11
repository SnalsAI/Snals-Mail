#!/usr/bin/env python3
"""
Script per testare la creazione di azioni PARSE_INTERPELLO
"""
import sys
sys.path.insert(0, '/app')

from app.database import SessionLocal
from app.models.email import Email
from app.models.azione import Azione
from app.services.action_executor import ActionExecutor
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    db = SessionLocal()
    try:
        # Trova email interpello
        email = db.query(Email).filter(
            Email.id == 174
        ).first()

        if not email:
            logger.error("Email 174 non trovata")
            return

        logger.info(f"Email 174: {email.oggetto}")
        logger.info(f"Categoria: {email.categoria.value}")
        logger.info(f"Sottocategoria: {email.sottocategoria}")

        # Elimina azioni esistenti per questa email
        db.query(Azione).filter(Azione.email_id == 174).delete()
        db.commit()
        logger.info("Azioni esistenti eliminate")

        # Crea nuove azioni
        executor = ActionExecutor(db)
        azioni = executor.execute_actions_for_email(174)

        logger.info(f"\n✅ Create {len(azioni)} azioni:")
        for azione in azioni:
            logger.info(f"   - ID {azione.id}: {azione.tipo.value}")

        db.commit()

    except Exception as e:
        logger.error(f"❌ Errore: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()

if __name__ == '__main__':
    main()
