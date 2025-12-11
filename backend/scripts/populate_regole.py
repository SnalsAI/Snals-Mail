"""
Script per popolare le regole iniziali nel database
"""
import sys
sys.path.insert(0, '/app')

from app.database import SessionLocal
from app.models.regola import Regola

def create_regole():
    db = SessionLocal()

    try:
        # Cancella regole esistenti (per testing)
        db.query(Regola).delete()

        regole = [
            {
                "nome": "Comunicazioni Scuola - Archivia",
                "descrizione": "Archivia comunicazioni generiche dalla scuola",
                "condizioni": {
                    "categoria": "comunicazione_scuola"
                },
                "azioni": [
                    {
                        "tipo": "ARCHIVIA",
                        "descrizione": "Archivia comunicazione scolastica",
                        "params": {
                            "folder": "comunicazioni_scuola"
                        }
                    }
                ],
                "priorita": 10
            },
            {
                "nome": "Convocazioni Scuola - Notifica",
                "descrizione": "Notifica e segna come importante le convocazioni",
                "condizioni": {
                    "categoria": "convocazione_scuola"
                },
                "azioni": [
                    {
                        "tipo": "INVIA_NOTIFICA",
                        "descrizione": "Notifica convocazione scolastica",
                        "params": {
                            "urgente": True,
                            "destinatari": ["segretario@snals.it"]
                        }
                    },
                    {
                        "tipo": "SEGNA_IMPORTANTE",
                        "descrizione": "Segna convocazione come importante",
                        "params": {}
                    }
                ],
                "priorita": 20
            },
            {
                "nome": "Comunicazioni SNALS Centrale - Inoltra",
                "descrizione": "Inoltra comunicazioni dalla sede centrale ai coordinatori",
                "condizioni": {
                    "categoria": "comunicazione_snals_centrale"
                },
                "azioni": [
                    {
                        "tipo": "INOLTRA_EMAIL",
                        "descrizione": "Inoltra a coordinatori provinciali",
                        "params": {
                            "destinatari": ["coordinatori@snals-taranto.it"],
                            "mantieni_originale": True
                        }
                    },
                    {
                        "tipo": "ARCHIVIA",
                        "descrizione": "Archivia comunicazione centrale",
                        "params": {
                            "folder": "snals_centrale"
                        }
                    }
                ],
                "priorita": 15
            },
            {
                "nome": "Richieste Assistenza Docenti - Crea Task",
                "descrizione": "Crea task per richieste di assistenza dai docenti",
                "condizioni": {
                    "categoria": "richiesta_assistenza_docente"
                },
                "azioni": [
                    {
                        "tipo": "CREA_TASK",
                        "descrizione": "Crea task per assistenza docente",
                        "params": {
                            "assegnato_a": "assistenza@snals.it",
                            "priorita": "alta"
                        }
                    },
                    {
                        "tipo": "INVIA_RISPOSTA_AUTOMATICA",
                        "descrizione": "Conferma ricezione richiesta",
                        "params": {
                            "template": "conferma_richiesta_assistenza"
                        }
                    }
                ],
                "priorita": 25
            },
            {
                "nome": "Richieste Iscrizione - Processa",
                "descrizione": "Processa richieste di iscrizione al sindacato",
                "condizioni": {
                    "categoria": "richiesta_iscrizione"
                },
                "azioni": [
                    {
                        "tipo": "INVIA_NOTIFICA",
                        "descrizione": "Notifica nuova iscrizione",
                        "params": {
                            "urgente": True,
                            "destinatari": ["iscrizioni@snals.it"]
                        }
                    },
                    {
                        "tipo": "CREA_TASK",
                        "descrizione": "Crea task per processare iscrizione",
                        "params": {
                            "assegnato_a": "iscrizioni@snals.it",
                            "priorita": "alta"
                        }
                    },
                    {
                        "tipo": "INVIA_RISPOSTA_AUTOMATICA",
                        "descrizione": "Conferma ricezione richiesta",
                        "params": {
                            "template": "conferma_richiesta_iscrizione"
                        }
                    }
                ],
                "priorita": 30
            },
            {
                "nome": "Questioni Legali - Urgente",
                "descrizione": "Gestione urgente per questioni legali",
                "condizioni": {
                    "categoria": "questione_legale"
                },
                "azioni": [
                    {
                        "tipo": "INVIA_NOTIFICA",
                        "descrizione": "Notifica urgente questione legale",
                        "params": {
                            "urgente": True,
                            "destinatari": ["legale@snals.it", "segretario@snals.it"]
                        }
                    },
                    {
                        "tipo": "SEGNA_IMPORTANTE",
                        "descrizione": "Segna come importante",
                        "params": {}
                    },
                    {
                        "tipo": "CREA_TASK",
                        "descrizione": "Crea task per ufficio legale",
                        "params": {
                            "assegnato_a": "legale@snals.it",
                            "priorita": "critica"
                        }
                    }
                ],
                "priorita": 50
            },
            {
                "nome": "Newsletter - Pubblica",
                "descrizione": "Pubblica newsletter su sito e social",
                "condizioni": {
                    "categoria": "newsletter"
                },
                "azioni": [
                    {
                        "tipo": "PUBBLICA_SU_SITO",
                        "descrizione": "Pubblica newsletter sul sito",
                        "params": {
                            "sezione": "news"
                        }
                    },
                    {
                        "tipo": "ARCHIVIA",
                        "descrizione": "Archivia newsletter",
                        "params": {
                            "folder": "newsletter"
                        }
                    }
                ],
                "priorita": 5
            },
            {
                "nome": "Varie - Archivia Semplice",
                "descrizione": "Archiviazione semplice per email varie",
                "condizioni": {
                    "categoria": "varie"
                },
                "azioni": [
                    {
                        "tipo": "ARCHIVIA",
                        "descrizione": "Archivia email generica",
                        "params": {
                            "folder": "varie"
                        }
                    }
                ],
                "priorita": 1
            },
            {
                "nome": "Spam - Elimina",
                "descrizione": "Elimina automaticamente spam",
                "condizioni": {
                    "categoria": "spam"
                },
                "azioni": [
                    {
                        "tipo": "ELIMINA",
                        "descrizione": "Elimina spam",
                        "params": {
                            "permanente": False
                        }
                    }
                ],
                "priorita": 100
            }
        ]

        for regola_data in regole:
            regola = Regola(**regola_data, attivo=True)
            db.add(regola)

        db.commit()
        print(f"✅ Create {len(regole)} regole con successo!")

        # Mostra riepilogo
        for r in db.query(Regola).order_by(Regola.priorita.desc()).all():
            print(f"  - {r.nome} (priorità: {r.priorita})")

    except Exception as e:
        db.rollback()
        print(f"❌ Errore: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    create_regole()
