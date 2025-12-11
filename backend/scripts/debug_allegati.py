#!/usr/bin/env python3
"""Debug property allegati"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.models.email import Email

db = SessionLocal()
email = db.query(Email).filter(Email.id == 194).first()

print(f"Email ID: {email.id}")
print(f"Oggetto: {email.oggetto}")
print(f"\nAllegati_nomi ({type(email.allegati_nomi)}):")
print(f"  {email.allegati_nomi}")
print(f"\nAllegati_path ({type(email.allegati_path)}):")
print(f"  {email.allegati_path}")
print(f"\nProperty allegati ({type(email.allegati)}):")
print(f"  Count: {len(email.allegati)}")
for i, all in enumerate(email.allegati):
    print(f"  [{i}] {all}")

db.close()
