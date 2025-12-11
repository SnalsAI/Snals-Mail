#!/usr/bin/env python3
"""Script per azzerare tutti gli interpelli e riprocessarli"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import get_db_session
from app.models.interpello import Interpello
from app.models.email import Email

def reset_interpelli():
    """Cancella tutti gli interpelli dal database"""
    with get_db_session() as db:
        # Count
        count = db.query(Interpello).count()
        print(f"Found {count} interpelli to delete")

        if count == 0:
            print("No interpelli to delete")
            return 0

        # Delete all
        deleted = db.query(Interpello).delete()
        db.commit()

        print(f"✅ Deleted {deleted} interpelli from database")
        return deleted

def get_interpello_emails():
    """Ottieni tutti gli email_id con sottocategoria Interpello"""
    with get_db_session() as db:
        emails = db.query(Email.id).filter(
            Email.sottocategoria == "Interpello"
        ).all()

        email_ids = [e[0] for e in emails]
        print(f"Found {len(email_ids)} emails with sottocategoria=Interpello")
        print(f"Email IDs: {email_ids}")

        return email_ids

if __name__ == "__main__":
    print("=" * 80)
    print("RESET INTERPELLI")
    print("=" * 80)

    # Step 1: Delete all interpelli
    deleted = reset_interpelli()

    # Step 2: Get list of emails to reprocess
    email_ids = get_interpello_emails()

    print("\n" + "=" * 80)
    print(f"SUMMARY: Deleted {deleted} interpelli, found {len(email_ids)} emails to reprocess")
    print("=" * 80)
