#!/usr/bin/env python3
"""
Script per ricostruire gli allegati_path delle email con path vuoti.

Problema: Email vecchie hanno allegati_nomi ma allegati_path = []
Soluzione: Cerca i file nel filesystem e ricostruisce i path
"""
import os
import sys
from pathlib import Path

# Aggiungi parent directory al path per import
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.email import Email
from app.config import get_settings

settings = get_settings()


def find_attachment_path(message_id: str, filename: str) -> str | None:
    """
    Cerca il file dell'allegato nel filesystem.

    Args:
        message_id: Message-ID dell'email
        filename: Nome del file allegato

    Returns:
        Path completo se trovato, None altrimenti
    """
    # Pulisci message_id (stesso processo dell'ingest)
    clean_message_id = message_id.strip().strip('<>').replace('\n', '').replace('\r', '').replace('\t', '').replace('/', '_').replace('\\', '_')

    # Directory allegati per questo message_id
    attachments_dir = os.path.join(settings.ATTACHMENTS_PATH, clean_message_id)

    if not os.path.exists(attachments_dir):
        return None

    # Cerca il file
    filepath = os.path.join(attachments_dir, filename)
    if os.path.exists(filepath):
        return filepath

    # Prova anche senza newlines nel filename (alcuni hanno \n)
    clean_filename = filename.replace('\n', ' ').replace('\r', ' ')
    filepath_clean = os.path.join(attachments_dir, clean_filename)
    if os.path.exists(filepath_clean):
        return filepath_clean

    return None


def fix_email_paths(db: Session):
    """Fix allegati_path per email con path vuoti"""

    # Trova email con allegati ma path vuoti
    emails = db.query(Email).filter(
        Email.allegati_nomi.isnot(None)
    ).all()

    emails_fixed = 0
    emails_skipped = 0
    files_found = 0
    files_missing = 0

    for email in emails:
        # Skip se allegati_path già popolato CON VALORI (non null)
        if email.allegati_path and len(email.allegati_path) > 0:
            # Controlla se ci sono valori validi (non None/null)
            if any(p is not None and p != '' for p in email.allegati_path):
                emails_skipped += 1
                continue

        # Skip se nessun allegato
        if not email.allegati_nomi or len(email.allegati_nomi) == 0:
            emails_skipped += 1
            continue

        print(f"\n📧 Email {email.id} - {len(email.allegati_nomi)} allegati")

        new_paths = []
        for filename in email.allegati_nomi:
            # Cerca file nel filesystem
            filepath = find_attachment_path(email.message_id, filename)

            if filepath:
                new_paths.append(filepath)
                files_found += 1
                print(f"  ✅ Trovato: {filename}")
            else:
                # Se non trovato, aggiungi None per mantenere sincronizzazione
                new_paths.append(None)
                files_missing += 1
                print(f"  ❌ Mancante: {filename}")

        # Aggiorna database
        if new_paths:
            email.allegati_path = new_paths
            emails_fixed += 1
            print(f"  💾 Aggiornato allegati_path: {len([p for p in new_paths if p])} file trovati")

    # Commit
    db.commit()

    print(f"\n" + "="*60)
    print(f"📊 RIEPILOGO:")
    print(f"  Email processate: {len(emails)}")
    print(f"  Email fixate: {emails_fixed}")
    print(f"  Email già ok: {emails_skipped}")
    print(f"  File trovati: {files_found}")
    print(f"  File mancanti: {files_missing}")
    print("="*60)


if __name__ == "__main__":
    print("🔧 Fix allegati_path per email vecchie\n")

    db = SessionLocal()
    try:
        fix_email_paths(db)
        print("\n✅ Fix completato!")
    except Exception as e:
        print(f"\n❌ Errore: {e}")
        db.rollback()
    finally:
        db.close()
