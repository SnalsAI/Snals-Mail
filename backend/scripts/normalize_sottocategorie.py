"""
Script per normalizzare le sottocategorie esistenti nel database.
Rimuove i nomi delle scuole e lascia solo la categoria base.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.email import Email
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def normalize_sottocategoria(sottocategoria: str) -> str:
    """
    Normalizza una sottocategoria rimuovendo il nome della scuola.

    Esempi:
    - "Contrattazione Integrativa - Istituto Comprensivo Italiano di Stato (Maiuscolo)"
      -> "Contrattazione Integrativa"
    - "Convocazione RSU - IC Don Bosco (Taranto)"
      -> "Convocazione RSU"
    """
    # Pattern per rimuovere " - [nome scuola]"
    # Cerca " - " seguito da testo che finisce con "(comune)" opzionale
    pattern = r'\s*-\s+.*?(?:\([^)]+\))?$'
    normalized = re.sub(pattern, '', sottocategoria).strip()

    return normalized

def main():
    """Normalizza tutte le sottocategorie nel database"""
    db = SessionLocal()

    try:
        # Recupera tutte le email con sottocategoria
        emails = db.query(Email).filter(Email.sottocategoria.is_not(None)).all()

        logger.info(f"📊 Trovate {len(emails)} email con sottocategoria")

        updates = 0
        mappings = {}

        for email in emails:
            original = email.sottocategoria
            normalized = normalize_sottocategoria(original)

            if original != normalized:
                # Traccia le mappature
                if original not in mappings:
                    mappings[original] = normalized

                email.sottocategoria = normalized
                updates += 1

        # Mostra le mappature
        if mappings:
            logger.info(f"\n📝 Mappature applicate ({len(mappings)}):")
            for old, new in sorted(mappings.items()):
                logger.info(f"  '{old}' → '{new}'")

        # Commit
        if updates > 0:
            logger.info(f"\n💾 Salvando {updates} aggiornamenti...")
            db.commit()
            logger.info("✅ Normalizzazione completata!")
        else:
            logger.info("✅ Nessuna normalizzazione necessaria - tutte le sottocategorie sono già pulite")

        # Mostra statistiche finali
        logger.info("\n📊 Statistiche sottocategorie dopo normalizzazione:")
        from sqlalchemy import func
        sottocategorie = db.query(
            Email.sottocategoria,
            func.count(Email.id)
        ).filter(
            Email.sottocategoria.is_not(None)
        ).group_by(
            Email.sottocategoria
        ).order_by(
            Email.sottocategoria
        ).all()

        logger.info("Count | Sottocategoria")
        logger.info("------|---------------")
        for sottocat, count in sottocategorie:
            logger.info(f"{count:5d} | {sottocat}")

    except Exception as e:
        logger.error(f"❌ Errore: {e}")
        import traceback
        logger.error(traceback.format_exc())
        db.rollback()
    finally:
        db.close()

if __name__ == '__main__':
    main()
