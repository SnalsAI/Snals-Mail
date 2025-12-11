"""
Script per ricreare l'enum EmailCategory in modo pulito con solo valori minuscoli.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Ricrea enum EmailCategory con solo valori minuscoli"""

    try:
        logger.info("🔧 Ricreazione enum EmailCategory...")

        with engine.begin() as conn:
            # 1. Converti colonna categoria a text temporaneamente
            logger.info("  1. Conversione colonna categoria a TEXT...")
            conn.execute(text("ALTER TABLE emails ALTER COLUMN categoria TYPE text USING categoria::text"))

            # 1.5. Converti tutti i valori MAIUSCOLI a minuscoli nella colonna text
            logger.info("  1.5. Conversione valori MAIUSCOLI a minuscoli...")
            conn.execute(text("""
                UPDATE emails
                SET categoria = LOWER(categoria)
                WHERE categoria IS NOT NULL
            """))

            # 2. Elimina il vecchio enum
            logger.info("  2. Eliminazione vecchio enum...")
            conn.execute(text("DROP TYPE IF EXISTS emailcategory CASCADE"))

            # 3. Crea nuovo enum con solo valori minuscoli
            logger.info("  3. Creazione nuovo enum con valori minuscoli...")
            conn.execute(text("""
                CREATE TYPE emailcategory AS ENUM (
                    'info_generiche',
                    'richiesta_appuntamento',
                    'richiesta_tesseramento',
                    'convocazione_scuola',
                    'comunicazione_ust_usr',
                    'comunicazione_scuola',
                    'comunicazione_snals_centrale',
                    'spam',
                    'pubblicita',
                    'varie'
                )
            """))

            # 4. Riconverti colonna categoria a enum
            logger.info("  4. Riconversione colonna categoria a EmailCategory...")
            conn.execute(text("ALTER TABLE emails ALTER COLUMN categoria TYPE emailcategory USING categoria::emailcategory"))

        logger.info("\n✅ Enum ricreato con successo!")

        # Verifica
        logger.info("\n📊 Verifica valori enum:")
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT enumlabel
                FROM pg_enum
                JOIN pg_type ON pg_enum.enumtypid = pg_type.oid
                WHERE pg_type.typname = 'emailcategory'
                ORDER BY enumsortorder;
            """))

            for row in result:
                logger.info(f"  ✓ {row[0]}")

        # Verifica email
        logger.info("\n📧 Verifica email:")
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT categoria::text, COUNT(*)
                FROM emails
                WHERE categoria IS NOT NULL
                GROUP BY categoria
                ORDER BY COUNT(*) DESC
            """))

            for row in result:
                logger.info(f"  {row[1]:3d} | {row[0]}")

    except Exception as e:
        logger.error(f"❌ Errore: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(main())
