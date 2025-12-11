#!/usr/bin/env python3
"""
Script per testare la creazione di azioni per le email esistenti
"""
import sys
sys.path.insert(0, '/app')

from app.database import SessionLocal
from app.models.email import Email
from app.services.action_executor import ActionExecutor
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    db = SessionLocal()
    try:
        # Trova email con interpretazione
        emails = db.query(Email).filter(
            Email.interpretazione != None
        ).order_by(Email.id.desc()).limit(5).all()

        logger.info(f"Trovate {len(emails)} email con interpretazione")

        executor = ActionExecutor(db)

        for email in emails:
            logger.info(f"\n{'='*60}")
            logger.info(f"Email {email.id}: {email.oggetto[:50]}")
            logger.info(f"Categoria: {email.categoria.value if email.categoria else 'N/A'}")
            logger.info(f"Sottocategoria: {email.sottocategoria or 'N/A'}")

            # Crea azioni
            azioni = executor.execute_actions_for_email(email.id)

            if azioni:
                logger.info(f"✅ Create {len(azioni)} azioni:")
                for azione in azioni:
                    logger.info(f"   - {azione.tipo.value}: {azione.dettagli}")
            else:
                logger.info(f"⚠️  Nessuna azione creata")

        db.commit()
        logger.info(f"\n{'='*60}")
        logger.info("✅ Test completato")

    except Exception as e:
        logger.error(f"❌ Errore: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()

if __name__ == '__main__':
    main()
