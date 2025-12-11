"""
Servizio per processamento manuale email con logging dettagliato
"""
from typing import List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.email import Email, EmailStatus, EmailCategory
from app.models.regola import Regola
from app.models.azione import Azione, StatoAzione, TipoAzione
import logging

logger = logging.getLogger(__name__)


class EmailProcessorService:
    """Servizio per processare email e creare azioni con log dettagliato"""

    def __init__(self, db: Session):
        self.db = db
        self.log_steps = []

    def _add_log(self, step: str, details: Any = None, level: str = "info"):
        """Aggiungi step al log del processamento"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "step": step,
            "level": level,
            "details": details
        }
        self.log_steps.append(log_entry)
        logger.info(f"[EmailProcessor] {step}: {details}")

    def process_email(self, email_id: int) -> Dict[str, Any]:
        """
        Processa un'email applicando le regole e creando azioni.
        Restituisce un log dettagliato di tutto il processo.
        """
        self.log_steps = []

        try:
            # Step 1: Recupera email
            self._add_log("Recupero email", {"email_id": email_id})
            email = self.db.query(Email).filter(Email.id == email_id).first()

            if not email:
                self._add_log("Email non trovata", {"email_id": email_id}, "error")
                return {
                    "success": False,
                    "error": "Email non trovata",
                    "log": self.log_steps
                }

            self._add_log("Email recuperata", {
                "id": email.id,
                "oggetto": email.oggetto[:50],
                "categoria": email.get_categoria_value(),
                "stato": email.stato.value
            })

            # Step 2: Verifica categoria
            if not email.categoria:
                self._add_log("Email senza categoria", None, "warning")
                return {
                    "success": False,
                    "error": "Email non ha una categoria assegnata",
                    "log": self.log_steps
                }

            categoria_value = email.get_categoria_value()
            self._add_log("Categoria identificata", {
                "categoria": categoria_value,
                "confidence": email.categoria_confidence
            })

            # Step 3: Cerca regole applicabili
            self._add_log("Ricerca regole applicabili", {"categoria": categoria_value})

            regole = self.db.query(Regola).filter(
                Regola.attivo == True
            ).order_by(Regola.priorita.desc()).all()

            regole_applicabili = []
            for regola in regole:
                if self._regola_si_applica(regola, email):
                    regole_applicabili.append(regola)
                    self._add_log("Regola trovata", {
                        "regola_id": regola.id,
                        "nome": regola.nome,
                        "priorita": regola.priorita,
                        "num_azioni": len(regola.azioni) if regola.azioni else 0
                    })

            if not regole_applicabili:
                self._add_log("Nessuna regola applicabile", {"categoria": categoria_value}, "warning")
                return {
                    "success": False,
                    "error": f"Nessuna regola trovata per categoria '{categoria_value}'",
                    "log": self.log_steps
                }

            self._add_log("Regole applicabili trovate", {
                "count": len(regole_applicabili),
                "regole": [r.nome for r in regole_applicabili]
            })

            # Step 4: Crea azioni dalle regole usando RulesEngine
            # RulesEngine gestisce tutta la logica sofisticata (controllo allegati, intervento manuale, ecc)
            from app.services.rules_engine import RulesEngine
            rules_engine = RulesEngine(self.db)

            azioni_create = []

            for regola in regole_applicabili:
                # Conta azioni (supporta formato lista e dict)
                num_azioni = 0
                if regola.azioni:
                    if isinstance(regola.azioni, list):
                        num_azioni = len(regola.azioni)
                    elif isinstance(regola.azioni, dict):
                        num_azioni = len(regola.azioni.get('actions', []))

                self._add_log("Processamento regola", {
                    "regola": regola.nome,
                    "azioni_da_creare": num_azioni
                })

                if not regola.azioni:
                    self._add_log("Regola senza azioni", {"regola": regola.nome}, "warning")
                    continue

                try:
                    # Usa RulesEngine per creare azioni con tutta la logica avanzata
                    azioni_regola = rules_engine._execute_rule_actions(email, regola)

                    for azione in azioni_regola:
                        if azione:
                            azioni_create.append(azione)
                            self._add_log("Azione creata", {
                                "azione_id": azione.id,
                                "tipo": azione.tipo.value,
                                "stato": azione.stato.value
                            })

                except Exception as e:
                    self._add_log("Errore creazione azioni", {
                        "regola": regola.nome,
                        "errore": str(e)
                    }, "error")
                    logger.exception(f"Errore processamento regola {regola.nome}")

            # Step 5: Aggiorna stato email
            email.stato = EmailStatus.AZIONE_ESEGUITA
            self._add_log("Stato email aggiornato", {
                "nuovo_stato": "AZIONE_ESEGUITA"
            })

            # Commit
            self.db.commit()

            # Step 6: Auto-eliminazione spam se abilitata
            if email.categoria == EmailCategory.SPAM.value:
                from app.models.system_settings import SystemSettings
                auto_delete_setting = self.db.query(SystemSettings).filter(
                    SystemSettings.key == 'auto_delete_spam'
                ).first()

                if auto_delete_setting and auto_delete_setting.get_typed_value():
                    self._add_log("Auto-eliminazione spam attiva", {
                        "categoria": "SPAM"
                    }, "warning")

                    try:
                        from app.services.email_deletion import get_deletion_service
                        deletion_service = get_deletion_service(self.db)

                        if deletion_service.delete_from_server(email):
                            self._add_log("Email spam eliminata dal server", {
                                "email_id": email.id
                            }, "success")

                            # Elimina anche dal database locale
                            self.db.delete(email)
                            self.db.commit()

                            self._add_log("Email spam eliminata dal database locale", {
                                "email_id": email.id
                            }, "success")
                        else:
                            self._add_log("Errore eliminazione email spam dal server", {
                                "email_id": email.id
                            }, "error")
                    except Exception as e:
                        self._add_log("Errore auto-eliminazione spam", {
                            "error": str(e)
                        }, "error")
                        logger.exception("Errore auto-eliminazione spam")

            self._add_log("Processamento completato", {
                "azioni_create": len(azioni_create),
                "regole_applicate": len(regole_applicabili)
            }, "success")

            return {
                "success": True,
                "email_id": email_id,
                "azioni_create": len(azioni_create),
                "azioni": [
                    {
                        "id": a.id,
                        "tipo": a.tipo.value,
                        "descrizione": a.dettagli.get('descrizione', '') if a.dettagli else '',
                        "stato": a.stato.value
                    }
                    for a in azioni_create
                ],
                "log": self.log_steps
            }

        except Exception as e:
            self.db.rollback()
            self._add_log("Errore fatale", {
                "error": str(e),
                "type": type(e).__name__
            }, "error")

            return {
                "success": False,
                "error": str(e),
                "log": self.log_steps
            }

    def _regola_si_applica(self, regola: Regola, email: Email) -> bool:
        """Verifica se una regola si applica all'email - usa RulesEngine per supportare tutte le condizioni"""
        if not regola.condizioni:
            return False

        # Usa RulesEngine per valutare condizioni complesse (mittente, oggetto, categoria, ecc)
        from app.services.rules_engine import RulesEngine
        rules_engine = RulesEngine(self.db)

        try:
            return rules_engine._evaluate_conditions(email, regola.condizioni)
        except Exception as e:
            logger.error(f"Errore valutazione condizioni regola {regola.id}: {e}")
            return False

    def _crea_azione(self, email: Email, regola: Regola, azione_data: Dict) -> Azione:
        """Crea un'azione dal template della regola"""

        tipo_str = azione_data.get('tipo', 'ARCHIVIA')

        # Mappa string -> enum (cerca per valore, non per nome)
        tipo_enum = TipoAzione.ARCHIVIA  # default

        # Cerca l'enum che ha questo valore
        tipo_str_lower = tipo_str.lower()
        for azione_type in TipoAzione:
            if azione_type.value == tipo_str_lower or azione_type.name == tipo_str:
                tipo_enum = azione_type
                break
        else:
            logger.warning(f"Tipo azione sconosciuto: {tipo_str}, uso ARCHIVIA")

        # Controlla se esiste già un'azione dello stesso tipo per questa email
        existing_azione = self.db.query(Azione).filter(
            Azione.email_id == email.id,
            Azione.tipo == tipo_enum
        ).first()

        if existing_azione:
            logger.info(f"Azione {tipo_enum.value} già esistente per email {email.id}, skip")
            return existing_azione

        azione = Azione(
            email_id=email.id,
            tipo=tipo_enum,
            dettagli={
                'descrizione': azione_data.get('descrizione', f'Azione da regola: {regola.nome}'),
                'parametri': azione_data.get('params', {}),
                'regola_nome': regola.nome
            },
            stato=StatoAzione.IN_CODA
        )

        self.db.add(azione)
        self.db.flush()

        return azione
