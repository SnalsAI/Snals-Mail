"""
Test di validazione interpelli - Confronta parsing PRIMA vs DOPO le modifiche
"""
import sys
sys.path.insert(0, '/app')

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import json

# Connessione DB
DATABASE_URL = "postgresql://snals_user:snals_password@postgres:5432/snals_email_agent"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

# Import extractors
from app.services.interpello_extractors import RegexExtractor
from app.services.semantic_validator import SemanticValidator

def test_all_interpelli():
    """Testa tutti gli interpelli e confronta risultati"""

    # Prendi tutti gli interpelli
    result = session.execute(text("""
        SELECT id, provincia, citta, istituto, classe_concorso, testo_completo
        FROM interpelli
        ORDER BY id
    """))
    interpelli = result.fetchall()

    print(f"\n{'='*80}")
    print(f"TEST VALIDAZIONE INTERPELLI - {len(interpelli)} interpelli")
    print(f"{'='*80}\n")

    regex_extractor = RegexExtractor()
    semantic_validator = SemanticValidator()

    errori = []
    corretti = []

    for row in interpelli:
        id, provincia_db, citta_db, istituto_db, classe_db, testo = row

        if not testo:
            print(f"[{id}] SKIP - nessun testo")
            continue

        print(f"\n{'─'*60}")
        print(f"INTERPELLO #{id}")
        print(f"{'─'*60}")

        # STEP 1: Dati attuali nel DB
        print(f"\n📦 DATI ATTUALI (DB):")
        print(f"   provincia: {provincia_db}")
        print(f"   citta: {citta_db}")
        print(f"   istituto: {istituto_db}")
        print(f"   classe: {classe_db}")

        # STEP 2: Ri-estrai con regex migliorato
        print(f"\n🔍 STEP 2 - REGEX EXTRACTION:")
        dati_regex = regex_extractor.extract(testo)

        if dati_regex:
            provincia_new = dati_regex.get('provincia', 'N/A')
            istituto_new = dati_regex.get('istituto', 'N/A')
            classe_new = dati_regex.get('classe_concorso', 'N/A')

            print(f"   provincia: {provincia_new}")
            print(f"   istituto: {istituto_new}")
            print(f"   classe: {classe_new}")

            # STEP 3: Validazione semantica provincia
            print(f"\n✅ STEP 3 - VALIDAZIONE SEMANTICA:")

            if dati_regex.get('provincia'):
                validation = semantic_validator.validate_provincia(
                    dati_regex['provincia'],
                    testo_originale=testo
                )

                print(f"   valid: {validation['valid']}")
                print(f"   reason: {validation.get('reason', 'N/A')}")
                print(f"   codice_mecc: {validation.get('codice_mecc_found', 'N/A')}")

                if validation.get('corrected'):
                    print(f"   CORREZIONE: {dati_regex['provincia']} → {validation['corrected']}")

                # CONFRONTO
                print(f"\n📊 CONFRONTO:")

                # Provincia diversa?
                if provincia_db and provincia_new and provincia_db.upper() != provincia_new.upper():
                    if validation.get('corrected'):
                        status = "🔧 ERRORE CORRETTO"
                        if provincia_db.upper() == validation['corrected'].upper():
                            status = "⚠️ DB GIÀ CORRETTO"
                    else:
                        status = "⚠️ DIFFERENZA"
                    print(f"   provincia: DB='{provincia_db}' vs NEW='{provincia_new}' [{status}]")

                    if not validation['valid']:
                        errori.append({
                            'id': id,
                            'db': provincia_db,
                            'new': provincia_new,
                            'corrected': validation.get('corrected'),
                            'codice': validation.get('codice_mecc_found')
                        })
                elif validation['valid']:
                    print(f"   provincia: OK ✓")
                    corretti.append(id)
                else:
                    print(f"   provincia: ERRORE (ma non rilevato differenza)")
            else:
                print(f"   Provincia non estratta")
        else:
            print(f"   Regex non ha estratto dati")

    # RIEPILOGO
    print(f"\n{'='*80}")
    print(f"RIEPILOGO")
    print(f"{'='*80}")
    print(f"\nInterpelli testati: {len(interpelli)}")
    print(f"Corretti: {len(corretti)}")
    print(f"Errori rilevati: {len(errori)}")

    if errori:
        print(f"\n❌ ERRORI TROVATI:")
        for err in errori:
            print(f"   #{err['id']}: DB='{err['db']}' → Corretto='{err['corrected']}' (codice: {err['codice']})")

    return errori, corretti

if __name__ == "__main__":
    test_all_interpelli()
