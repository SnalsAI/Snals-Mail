"""
Motore regole personalizzate
"""

import logging
import re
from typing import List, Dict, Any
from datetime import datetime

from app.database import SessionLocal
from app.models.email import Email
from app.models.regola import Regola
from app.models.interpretazione import Interpretazione

logger = logging.getLogger(__name__)


class RulesEngine:
    """Motore applicazione regole"""

    def __init__(self):
        self.operators = {
            'equals': lambda a, b: str(a).lower() == str(b).lower(),
            'not_equals': lambda a, b: str(a).lower() != str(b).lower(),
            'contains': lambda a, b: str(b).lower() in str(a).lower(),
            'not_contains': lambda a, b: str(b).lower() not in str(a).lower(),
            'starts_with': lambda a, b: str(a).lower().startswith(str(b).lower()),
            'ends_with': lambda a, b: str(a).lower().endswith(str(b).lower()),
            'regex': lambda a, b: bool(re.search(b, str(a), re.IGNORECASE)),
            'greater_than': lambda a, b: float(a) > float(b),
            'less_than': lambda a, b: float(a) < float(b),
        }

    def evaluate_condition(self, condition: Dict, email: Email, interp: Interpretazione) -> bool:
        """
        Valuta singola condizione

        Args:
            condition: Dict con field, operator, value
            email: Email da testare
            interp: Interpretazione

        Returns:
            True se condizione soddisfatta
        """
        field = condition.get('field')
        operator = condition.get('operator')
        value = condition.get('value')

        if not all([field, operator]):
            return False

        # Ottieni valore campo
        field_value = self._get_field_value(field, email, interp)

        # Applica operatore
        op_func = self.operators.get(operator)
        if not op_func:
            logger.warning(f"Operatore sconosciuto: {operator}")
            return False

        try:
            return op_func(field_value, value)
        except Exception as e:
            logger.error(f"Errore valutazione condizione: {e}")
            return False

    def _get_field_value(self, field: str, email: Email, interp: Interpretazione) -> Any:
        """Ottieni valore campo da email o interpretazione"""

        # Campi email diretti
        if hasattr(email, field):
            value = getattr(email, field)
            # Converti enum in string
            if hasattr(value, 'value'):
                return value.value
            return value

        # Campi interpretazione
        if interp and field in interp.interpretazione_json:
            return interp.interpretazione_json[field]

        # Campi nested nell'interpretazione (es. "scuola" dentro interpretazione_json)
        if interp and interp.interpretazione_json:
            return interp.interpretazione_json.get(field, '')

        return ''

    def evaluate_conditions_group(self, conditions_group: Dict, email: Email, interp: Interpretazione) -> bool:
        """
        Valuta gruppo condizioni con operatore logico

        Args:
            conditions_group: Dict con operator (AND/OR) e conditions list

        Returns:
            True se gruppo soddisfatto
        """
        operator = conditions_group.get('operator', 'AND')
        conditions = conditions_group.get('conditions', [])

        if not conditions:
            return True

        results = []

        for condition in conditions:
            # Se è un gruppo nested, valuta ricorsivamente
            if 'operator' in condition and 'conditions' in condition:
                result = self.evaluate_conditions_group(condition, email, interp)
            else:
                result = self.evaluate_condition(condition, email, interp)

            results.append(result)

        # Applica operatore logico
        if operator == 'AND':
            return all(results)
        elif operator == 'OR':
            return any(results)
        else:
            return False

    def apply_rules(self, email: Email):
        """
        Applica tutte le regole attive a una email

        Returns:
            Lista azioni da eseguire
        """
        db = SessionLocal()
        actions_to_execute = []

        try:
            # Carica interpretazione
            interp = db.query(Interpretazione).filter(
                Interpretazione.email_id == email.id
            ).first()

            # Regole attive ordinate per priorità
            regole = db.query(Regola).filter(
                Regola.attivo == True
            ).order_by(Regola.priorita).all()

            for regola in regole:
                try:
                    # Valuta condizioni
                    if self.evaluate_conditions_group(regola.condizioni, email, interp):
                        logger.info(f"Regola '{regola.nome}' applicata a email {email.id}")

                        # Aggiungi azioni
                        actions_to_execute.extend(regola.azioni)

                        # Aggiorna statistiche
                        regola.volte_applicata += 1
                        regola.ultima_applicazione = datetime.utcnow()

                except Exception as e:
                    logger.error(f"Errore applicazione regola {regola.id}: {e}")

            db.commit()

        except Exception as e:
            logger.error(f"Errore generale apply_rules: {e}")
            db.rollback()
        finally:
            db.close()

        return actions_to_execute

    def execute_rule_actions(self, actions: List[Dict], email: Email):
        """Esegue azioni derivanti da regole"""

        from app.services.email_ingest import EmailNormalClient
        from app.database import SessionLocal
        from app.models.evento import EventoCalendario

        db = SessionLocal()
        email_client = EmailNormalClient()

        try:
            for action in actions:
                action_type = action.get('tipo')

                if action_type == 'inoltra':
                    # Inoltra email
                    destinatari = action.get('destinatari', [])
                    for dest in destinatari:
                        email_client.send_email(
                            to=dest,
                            subject=f"Fwd: {email.oggetto}",
                            body=f"Email inoltrata automaticamente da regola.\n\n--- Messaggio originale ---\n\n{email.corpo}"
                        )
                        logger.info(f"Email {email.id} inoltrata a {dest}")

                elif action_type == 'assegna':
                    # Assegna convocazione a utente
                    user_id = action.get('user_id')
                    if user_id:
                        # Trova evento associato
                        evento = db.query(EventoCalendario).filter(
                            EventoCalendario.email_id == email.id
                        ).first()

                        if evento:
                            evento.assegnatario_id = user_id
                            logger.info(f"Evento {evento.id} assegnato a utente {user_id}")

                elif action_type == 'tag':
                    # Aggiungi tag custom (TODO: implementare campo tags)
                    tag = action.get('tag')
                    logger.info(f"Tag '{tag}' applicato a email {email.id}")

                elif action_type == 'notifica':
                    # Invia notifica (TODO: implementare sistema notifiche)
                    logger.info(f"Notifica per email {email.id}")

            db.commit()

        except Exception as e:
            logger.error(f"Errore esecuzione azioni regole: {e}")
            db.rollback()
        finally:
            db.close()
