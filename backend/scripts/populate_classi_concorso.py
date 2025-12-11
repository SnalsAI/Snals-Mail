"""
Script per popolare la tabella classi_concorso con i dati ufficiali
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.classe_concorso import ClasseConcorso
from app.data.classi_concorso import CLASSI_CONCORSO


def populate_classi_concorso():
    """Popola la tabella classi_concorso dal file dati."""
    db = SessionLocal()

    try:
        # Check se già popolata
        count = db.query(ClasseConcorso).count()
        if count > 0:
            print(f"⚠️  Tabella già popolata con {count} classi. Svuoto e ri-popolo...")
            db.query(ClasseConcorso).delete()
            db.commit()

        # Inserisci tutte le classi
        inserted = 0
        for codice_ufficiale, (codice_sidi, grado, descrizione) in CLASSI_CONCORSO.items():
            # Determina area (categorizzazione semplice)
            area = None
            if "MATEMATICA" in descrizione.upper() or "SCIENZE" in descrizione.upper():
                area = "MATEMATICA E SCIENZE"
            elif "LINGUA" in descrizione.upper() or "INGLESE" in descrizione.upper():
                area = "LINGUE STRANIERE"
            elif "LETTERARIE" in descrizione.upper() or "ITALIANO" in descrizione.upper():
                area = "LETTERE"
            elif "ARTE" in descrizione.upper() or "DESIGN" in descrizione.upper() or "DISEGNO" in descrizione.upper():
                area = "ARTE E DESIGN"
            elif "MUSICA" in descrizione.upper() or "STRUMENTO" in descrizione.upper():
                area = "MUSICA"
            elif "MOTORIE" in descrizione.upper() or "SPORTIVE" in descrizione.upper():
                area = "SCIENZE MOTORIE"
            elif "TECNOLOGIA" in descrizione.upper() or "INFORMATICA" in descrizione.upper():
                area = "TECNOLOGIA"

            classe = ClasseConcorso(
                codice=codice_ufficiale,
                codice_sidi=codice_sidi,
                grado=grado,
                descrizione=descrizione,
                area=area
            )
            db.add(classe)
            inserted += 1

        db.commit()
        print(f"✅ Inserite {inserted} classi di concorso!")

        # Mostra alcune classi inserite
        print("\n📋 Esempi classi inserite:")
        esempi = db.query(ClasseConcorso).limit(10).all()
        for classe in esempi:
            print(f"  {classe.codice} ({classe.codice_sidi}) - {classe.descrizione[:60]}...")

    except Exception as e:
        print(f"❌ Errore: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    populate_classi_concorso()
