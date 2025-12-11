#!/usr/bin/env python3
"""
Script per scaricare le ultime 30 email per testing
"""
import sys
sys.path.insert(0, '/app')

from app.services.email_ingest import EmailNormalClient, EmailPECClient
from app.services.categorizer import EmailCategorizer
from app.services.interpreter import EmailInterpreter
from app.database import SessionLocal
from app.models.email import Email, AccountType, EmailStatus
from app.models.interpretazione import Interpretazione
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_emails(limit=30):
    """Scarica ultime N email"""

    db = SessionLocal()
    categorizer = EmailCategorizer()
    interpreter = EmailInterpreter()

    total_new = 0

    # Account Normale
    print(f'\n📧 Scaricamento ultime {limit} email - Account NORMALE...')
    try:
        client = EmailNormalClient()
        emails_data = client.fetch_emails(limit=limit)

        print(f'   Trovate {len(emails_data)} email sul server')

        new_count = 0
        for email_data in emails_data:
            existing = db.query(Email).filter(
                Email.message_id == email_data['message_id']
            ).first()

            if existing:
                continue

            # Categorizza
            categoria, confidence, sottocategoria, proposta_info = categorizer.categorize(
                mittente=email_data['mittente'],
                oggetto=email_data['oggetto'],
                corpo=email_data['corpo'],
                attachment_paths=email_data.get('allegati_path', [])
            )

            # Interpreta
            interpretazione_data = interpreter.interpret(
                categoria=categoria,
                mittente=email_data['mittente'],
                oggetto=email_data['oggetto'],
                corpo=email_data['corpo'],
                allegati=email_data.get('allegati_nomi', []),
                data_oggi=datetime.now().isoformat(),
                attachment_paths=email_data.get('allegati_path', [])
            )

            # Salva email
            email_record = Email(
                message_id=email_data['message_id'],
                account_type=AccountType.NORMALE,
                mittente=email_data['mittente'],
                destinatario=email_data['destinatario'],
                oggetto=email_data['oggetto'],
                corpo=email_data['corpo'],
                corpo_html=email_data.get('corpo_html'),
                corpo_testo=email_data.get('corpo'),
                data_ricezione=email_data['data_ricezione'],
                allegati_nomi=email_data.get('allegati_nomi'),
                allegati_path=email_data.get('allegati_path'),
                categoria=categoria,
                categoria_confidence=confidence,
                sottocategoria=sottocategoria,
                stato=EmailStatus.INTERPRETATA,
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

            new_count += 1
            print(f'   ✓ Email {new_count}: {email_data["oggetto"][:60]}... (categoria: {categoria.value})')

        db.commit()
        total_new += new_count
        print(f'   ✅ Salvate {new_count} nuove email normali')

    except Exception as e:
        print(f'   ❌ Errore account normale: {e}')
        db.rollback()

    # Account PEC
    print(f'\n📧 Scaricamento ultime {limit} email - Account PEC...')
    try:
        client = EmailPECClient()
        emails_data = client.fetch_emails(limit=limit)

        print(f'   Trovate {len(emails_data)} email sul server')

        new_count = 0
        for email_data in emails_data:
            existing = db.query(Email).filter(
                Email.message_id == email_data['message_id']
            ).first()

            if existing:
                continue

            # Categorizza
            categoria, confidence, sottocategoria, proposta_info = categorizer.categorize(
                mittente=email_data['mittente'],
                oggetto=email_data['oggetto'],
                corpo=email_data['corpo'],
                attachment_paths=email_data.get('allegati_path', [])
            )

            # Interpreta
            interpretazione_data = interpreter.interpret(
                categoria=categoria,
                mittente=email_data['mittente'],
                oggetto=email_data['oggetto'],
                corpo=email_data['corpo'],
                allegati=email_data.get('allegati_nomi', []),
                data_oggi=datetime.now().isoformat(),
                attachment_paths=email_data.get('allegati_path', [])
            )

            # Salva email
            email_record = Email(
                message_id=email_data['message_id'],
                account_type=AccountType.PEC,
                mittente=email_data['mittente'],
                destinatario=email_data['destinatario'],
                oggetto=email_data['oggetto'],
                corpo=email_data['corpo'],
                corpo_html=email_data.get('corpo_html'),
                corpo_testo=email_data.get('corpo'),
                data_ricezione=email_data['data_ricezione'],
                allegati_nomi=email_data.get('allegati_nomi'),
                allegati_path=email_data.get('allegati_path'),
                categoria=categoria,
                categoria_confidence=confidence,
                sottocategoria=sottocategoria,
                stato=EmailStatus.INTERPRETATA,
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

            new_count += 1
            print(f'   ✓ Email {new_count}: {email_data["oggetto"][:60]}... (categoria: {categoria.value})')

        db.commit()
        total_new += new_count
        print(f'   ✅ Salvate {new_count} nuove email PEC')

    except Exception as e:
        print(f'   ❌ Errore account PEC: {e}')
        db.rollback()

    db.close()

    print(f'\n✅ Download completato! Totale nuove email: {total_new}')
    return total_new

if __name__ == '__main__':
    fetch_emails(limit=30)
