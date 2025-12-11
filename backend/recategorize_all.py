"""
Script per ricategorizzare tutte le email con l'ultimo modello
"""
from app.database import SessionLocal
from app.models.email import Email, EmailStatus
from app.services.email_interpreter import EmailInterpreter

db = SessionLocal()

# Conta email totali
total = db.query(Email).count()
print(f'📧 Email totali da ricategorizzare: {total}\n')

# Inizializza interprete
interpreter = EmailInterpreter(db)

# Ricategorizza tutte le email
emails = db.query(Email).all()
success_count = 0
error_count = 0
changed_count = 0

for i, email in enumerate(emails, 1):
    try:
        print(f'[{i}/{total}] Email ID {email.id}: {email.oggetto[:60]}...')

        # Salva vecchia categoria
        old_cat = email.categoria.value if email.categoria else 'N/A'
        old_subcat = email.sottocategoria or 'N/A'

        # Esegui interpretazione
        result = interpreter.interpret_email(email.id)

        # Ricarica email per vedere i cambiamenti
        db.refresh(email)
        new_cat = email.categoria.value if email.categoria else 'N/A'
        new_subcat = email.sottocategoria or 'N/A'

        if old_cat != new_cat or old_subcat != new_subcat:
            print(f'  ✓ Categoria: {old_cat} → {new_cat}')
            if old_subcat != new_subcat:
                print(f'    Sottocategoria: {old_subcat} → {new_subcat}')
            changed_count += 1
        else:
            print(f'  ✓ Confermata: {new_cat}')

        success_count += 1

    except Exception as e:
        print(f'  ✗ Errore: {str(e)[:100]}')
        error_count += 1
        continue

print(f'\n📊 Riepilogo:')
print(f'  ✅ Successi: {success_count}')
print(f'  🔄 Cambiate: {changed_count}')
print(f'  ❌ Errori: {error_count}')

db.close()
