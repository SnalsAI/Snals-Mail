#!/usr/bin/env python3
"""
Script per ricategorizzare le email esistenti con il nuovo prompt migliorato
"""
import sys
sys.path.insert(0, '/app')

from app.database import SessionLocal
from app.models.email import Email
from app.services.categorizer import EmailCategorizer
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def recategorize_emails(limit: int = 10):
    """Ricategorizza le ultime N email"""

    db = SessionLocal()

    try:
        # Prendi le ultime N email
        emails = db.query(Email).order_by(Email.id.desc()).limit(limit).all()

        if not emails:
            logger.info("Nessuna email trovata")
            return

        logger.info(f"📧 Trovate {len(emails)} email da ricategorizzare")
        print("\n" + "="*80)

        categorizer = EmailCategorizer()

        success_count = 0
        error_count = 0

        for i, email in enumerate(emails, 1):
            print(f"\n[{i}/{len(emails)}] Email ID: {email.id}")
            print(f"Da: {email.mittente}")
            print(f"Oggetto: {email.oggetto[:80]}")
            print(f"Categoria vecchia: {email.categoria if email.categoria else 'N/A'} (conf: {email.categoria_confidence})")

            try:
                # Ricategorizza
                nuova_categoria, confidence, sottocategoria, proposta_info = categorizer.categorize(
                    mittente=email.mittente,
                    oggetto=email.oggetto,
                    corpo=email.corpo
                )

                # Aggiorna
                old_category = email.categoria if email.categoria else 'N/A'
                # Converti EmailCategory enum a string per compatibilità
                nuova_categoria_str = nuova_categoria.value if hasattr(nuova_categoria, 'value') else str(nuova_categoria)
                email.categoria = nuova_categoria_str
                email.categoria_confidence = confidence
                email.sottocategoria = sottocategoria

                # Gestione proposta sottocategoria
                if proposta_info:
                    email.sottocategoria_proposta = proposta_info['proposta']
                    email.motivo_proposta = proposta_info['motivo']
                    email.richiede_revisione = True
                    print(f"⚠️ Proposta nuova sottocategoria: {proposta_info['proposta']}")
                else:
                    email.sottocategoria_proposta = None
                    email.motivo_proposta = None

                sottocat_str = f" | Sottocat: {sottocategoria}" if sottocategoria else ""
                if old_category != nuova_categoria_str:
                    print(f"✅ Categoria NUOVA: {nuova_categoria_str} (conf: {confidence:.2f}){sottocat_str} - CAMBIATA!")
                else:
                    print(f"✓  Categoria confermata: {nuova_categoria_str} (conf: {confidence:.2f}){sottocat_str}")

                success_count += 1

            except Exception as e:
                logger.error(f"❌ Errore ricategorizzazione email {email.id}: {e}")
                print(f"❌ ERRORE: {e}")
                error_count += 1

        # Salva tutte le modifiche
        db.commit()

        print("\n" + "="*80)
        print(f"\n📊 RIEPILOGO:")
        print(f"   Totale email: {len(emails)}")
        print(f"   ✅ Successi: {success_count}")
        print(f"   ❌ Errori: {error_count}")
        print()

        logger.info("✅ Ricategorizzazione completata!")

    except Exception as e:
        db.rollback()
        logger.error(f"❌ Errore generale: {e}")
        raise
    finally:
        db.close()


if __name__ == '__main__':
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    recategorize_emails(limit)
