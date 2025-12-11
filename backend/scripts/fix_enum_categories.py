"""
Script per allineare l'enum EmailCategory nel database con il modello Python.
Converte i valori da MAIUSCOLO a minuscolo.
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
    """Allinea enum EmailCategory"""

    # Lista dei nuovi valori minuscoli da aggiungere
    new_values = [
        'info_generiche', 'richiesta_appuntamento', 'richiesta_tesseramento',
        'convocazione_scuola', 'comunicazione_ust_usr', 'comunicazione_scuola',
        'comunicazione_snals_centrale', 'spam', 'pubblicita', 'varie'
    ]

    try:
        logger.info("🔧 Aggiunta valori minuscoli all'enum EmailCategory...")

        # Aggiungi ogni valore in una transazione separata
        for value in new_values:
            with engine.begin() as conn:
                conn.execute(text(f"ALTER TYPE emailcategory ADD VALUE IF NOT EXISTS '{value}'"))
                logger.info(f"  ✅ Aggiunto: {value}")

        logger.info("\n📊 Conversione valori esistenti da MAIUSCOLO a minuscolo...")

        # Converti i valori esistenti
        with engine.begin() as conn:
            result = conn.execute(text("""
                UPDATE emails
                SET categoria = CASE
                    WHEN categoria::text = 'INFO_GENERICHE' THEN 'info_generiche'::emailcategory
                    WHEN categoria::text = 'RICHIESTA_APPUNTAMENTO' THEN 'richiesta_appuntamento'::emailcategory
                    WHEN categoria::text = 'RICHIESTA_TESSERAMENTO' THEN 'richiesta_tesseramento'::emailcategory
                    WHEN categoria::text = 'CONVOCAZIONE_SCUOLA' THEN 'convocazione_scuola'::emailcategory
                    WHEN categoria::text = 'COMUNICAZIONE_UST_USR' THEN 'comunicazione_ust_usr'::emailcategory
                    WHEN categoria::text = 'COMUNICAZIONE_SCUOLA' THEN 'comunicazione_scuola'::emailcategory
                    WHEN categoria::text = 'COMUNICAZIONE_SNALS_CENTRALE' THEN 'comunicazione_snals_centrale'::emailcategory
                    WHEN categoria::text = 'SPAM' THEN 'spam'::emailcategory
                    WHEN categoria::text = 'PUBBLICITA' THEN 'pubblicita'::emailcategory
                    WHEN categoria::text = 'VARIE' THEN 'varie'::emailcategory
                    ELSE categoria
                END
                WHERE categoria IS NOT NULL
            """))

            logger.info(f"✅ Convertite {result.rowcount} righe")

        logger.info("\n✅ Migrazione completata con successo!")

        # Verifica risultati
        logger.info("\n📊 Categorie dopo migrazione:")
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
