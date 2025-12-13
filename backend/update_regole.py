"""
Script per aggiornare le regole secondo il nuovo flusso di lavoro
"""
import sys
sys.path.insert(0, '/app')

from app.database import SessionLocal
from app.models.regola import Regola
from app.models.azione import Azione

db = SessionLocal()

# Elimina tutte le regole esistenti
print("Eliminazione regole esistenti...")
db.query(Regola).delete()
db.commit()

# Elimina tutte le azioni esistenti (hanno tipi sbagliati)
print("Eliminazione azioni esistenti...")
db.query(Azione).delete()
db.commit()

# Crea nuove regole secondo il flusso corretto
regole = [
    {
        "nome": "Info Generiche - Bozza Risposta LLM",
        "descrizione": "Genera bozza di risposta con LLM per info generiche",
        "priorita": 10,
        "condizioni": {"categoria": "info_generiche"},
        "azioni": [
            {
                "tipo": "BOZZA_RISPOSTA",
                "descrizione": "Genera bozza risposta con LLM",
                "params": {
                    "usa_llm": True,
                    "destinazione": "webmail_bozze"
                }
            }
        ]
    },
    {
        "nome": "Appuntamenti - Bozza con Link Prenotazione",
        "descrizione": "Genera bozza risposta con link piattaforma prenotazione",
        "priorita": 15,
        "condizioni": {"categoria": "richiesta_appuntamento"},
        "azioni": [
            {
                "tipo": "BOZZA_APPUNTAMENTO",
                "descrizione": "Genera bozza con link prenotazione",
                "params": {
                    "piattaforma": "calendario_snals",
                    "include_link": True
                }
            }
        ]
    },
    {
        "nome": "Tesseramento - Bozza con Allegati",
        "descrizione": "Genera bozza risposta con allegati da repository",
        "priorita": 20,
        "condizioni": {"categoria": "richiesta_tesseramento"},
        "azioni": [
            {
                "tipo": "BOZZA_TESSERAMENTO",
                "descrizione": "Genera bozza con allegati tesseramento",
                "params": {
                    "repository": "moduli_tesseramento",
                    "include_moduli": True
                }
            }
        ]
    },
    {
        "nome": "Convocazioni Scuole - Evento Calendario",
        "descrizione": "Crea evento calendario dopo analisi documento convocazione",
        "priorita": 25,
        "condizioni": {"categoria": "convocazione_scuola"},
        "azioni": [
            {
                "tipo": "EVENTO_CALENDARIO",
                "descrizione": "Crea evento calendario da convocazione",
                "params": {
                    "analizza_documento": True,
                    "estrai_data_ora": True,
                    "calendario": "snals_convocazioni"
                }
            },
            {
                "tipo": "SEGNA_IMPORTANTE",
                "descrizione": "Segna convocazione come importante",
                "params": {}
            }
        ]
    },
    {
        "nome": "UST/USR - Upload Drive + Sintesi",
        "descrizione": "Carica allegati su Google Drive con sintesi giornaliera opzionale",
        "priorita": 30,
        "condizioni": {"categoria": "comunicazione_ust_usr"},
        "azioni": [
            {
                "tipo": "UPLOAD_DRIVE",
                "descrizione": "Carica allegati su Google Drive",
                "params": {
                    "folder": "UST_USR",
                    "estrai_allegati": True
                }
            },
            {
                "tipo": "SINTESI",
                "descrizione": "Crea sintesi giornaliera (opzionale)",
                "params": {
                    "tipo_sintesi": "giornaliera",
                    "frequenza": "daily"
                }
            }
        ]
    },
    {
        "nome": "Comunicazioni Scuole - Interpretazione + Sintesi",
        "descrizione": "Interpreta comunicazione e genera sintesi opzionale",
        "priorita": 35,
        "condizioni": {"categoria": "comunicazione_scuola"},
        "azioni": [
            {
                "tipo": "SINTESI",
                "descrizione": "Genera sintesi comunicazione (opzionale)",
                "params": {
                    "tipo_sintesi": "per_comunicazione",
                    "salva_su": "archivio"
                }
            },
        ]
    },
    {
        "nome": "SNALS Centrale - Upload Drive + Sintesi",
        "descrizione": "Carica allegati su Drive con sintesi giornaliera opzionale",
        "priorita": 40,
        "condizioni": {"categoria": "comunicazione_snals_centrale"},
        "azioni": [
            {
                "tipo": "UPLOAD_DRIVE",
                "descrizione": "Carica allegati su Google Drive",
                "params": {
                    "folder": "SNALS_Centrale",
                    "estrai_allegati": True
                }
            },
            {
                "tipo": "SINTESI",
                "descrizione": "Crea sintesi giornaliera (opzionale)",
                "params": {
                    "tipo_sintesi": "giornaliera",
                    "frequenza": "daily"
                }
            }
        ]
    },
    {
        "nome": "Varie - Sintesi",
        "descrizione": "Genera sintesi per email varie",
        "priorita": 100,
        "condizioni": {"categoria": "varie"},
        "azioni": [
            {
                "tipo": "SINTESI",
                "descrizione": "Genera sintesi email",
                "params": {
                    "tipo_sintesi": "standard"
                }
            }
        ]
    }
]

print("\nCreazione nuove regole...")
for regola_data in regole:
    regola = Regola(
        nome=regola_data["nome"],
        descrizione=regola_data["descrizione"],
        priorita=regola_data["priorita"],
        condizioni=regola_data["condizioni"],
        azioni=regola_data["azioni"],
        attivo=True
    )
    db.add(regola)
    print(f"  ✓ {regola.nome}")

db.commit()

print(f"\n✓ Create {len(regole)} regole con successo!")

# Mostra riepilogo
print("\n" + "=" * 80)
print("REGOLE AGGIORNATE")
print("=" * 80)
for r in db.query(Regola).order_by(Regola.priorita).all():
    print(f"\n[{r.priorita}] {r.nome}")
    print(f"   Categoria: {r.condizioni.get('categoria')}")
    print(f"   Azioni: {', '.join([a['tipo'] for a in r.azioni])}")

db.close()
