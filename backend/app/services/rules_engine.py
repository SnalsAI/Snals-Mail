"""
Rules Engine - Motore regole personalizzabili per azioni automatiche.

FASE 7: Rules Engine
"""
import logging
import re
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.regola import Regola
from app.models.email import Email, EmailCategory
from app.models.azione import Azione, TipoAzione, StatoAzione

logger = logging.getLogger(__name__)


class RulesEngine:
    """Motore per valutare ed eseguire regole personalizzate."""

    def __init__(self, db: Session):
        """
        Inizializza il rules engine.

        Args:
            db: Sessione database
        """
        self.db = db

    def evaluate_rules_for_email(self, email: Email) -> List[Azione]:
        """
        Valuta tutte le regole attive per una email.

        Args:
            email: Email da valutare

        Returns:
            List[Azione]: Lista azioni create dalle regole
        """
        # Recupera regole attive
        regole_attive = self.db.query(Regola).filter(
            Regola.attiva == True
        ).order_by(Regola.priorita.desc()).all()

        if not regole_attive:
            logger.debug("Nessuna regola attiva")
            return []

        azioni_create = []

        for regola in regole_attive:
            try:
                # Valuta condizioni
                if self._evaluate_conditions(email, regola.condizioni):
                    logger.info(f"✅ Regola '{regola.nome}' soddisfatta per email {email.id}")

                    # Esegui azioni della regola
                    azioni = self._execute_rule_actions(email, regola)
                    azioni_create.extend(azioni)

                    # Se la regola ha stop_processing, ferma valutazione
                    if regola.condizioni.get('stop_on_match', False):
                        logger.info(f"Regola '{regola.nome}' ha stop_processing=True, fine valutazione")
                        break

            except Exception as e:
                logger.error(f"❌ Errore valutazione regola '{regola.nome}': {e}")

        logger.info(f"✅ Create {len(azioni_create)} azioni da {len(regole_attive)} regole")
        return azioni_create

    def _evaluate_conditions(self, email: Email, condizioni: Dict) -> bool:
        """
        Valuta se le condizioni di una regola sono soddisfatte.

        Args:
            email: Email da valutare
            condizioni: Dict con condizioni da valutare

        Returns:
            bool: True se tutte le condizioni sono soddisfatte
        """
        if not condizioni:
            return True

        operator = condizioni.get('operator', 'AND')
        rules = condizioni.get('rules', [])

        if not rules:
            return True

        results = []

        for rule in rules:
            field = rule.get('field')
            condition = rule.get('condition')
            value = rule.get('value')

            result = self._evaluate_single_condition(email, field, condition, value)
            results.append(result)

        # Applica operatore logico
        if operator == 'AND':
            return all(results)
        elif operator == 'OR':
            return any(results)
        else:
            return all(results)

    def _evaluate_single_condition(
        self,
        email: Email,
        field: str,
        condition: str,
        value: Any
    ) -> bool:
        """
        Valuta una singola condizione.

        Args:
            email: Email da valutare
            field: Campo email da controllare
            condition: Tipo condizione (uguale, contiene, regex, ecc.)
            value: Valore da confrontare

        Returns:
            bool: True se condizione soddisfatta
        """
        # Estrai valore campo dall'email
        email_value = self._get_email_field_value(email, field)

        if email_value is None:
            return False

        # Valuta condizione
        try:
            if condition == 'uguale':
                return str(email_value).lower() == str(value).lower()

            elif condition == 'diverso':
                return str(email_value).lower() != str(value).lower()

            elif condition == 'contiene':
                return str(value).lower() in str(email_value).lower()

            elif condition == 'non_contiene':
                return str(value).lower() not in str(email_value).lower()

            elif condition == 'inizia_con':
                return str(email_value).lower().startswith(str(value).lower())

            elif condition == 'finisce_con':
                return str(email_value).lower().endswith(str(value).lower())

            elif condition == 'regex':
                pattern = re.compile(value, re.IGNORECASE)
                return bool(pattern.search(str(email_value)))

            elif condition == 'maggiore':
                return float(email_value) > float(value)

            elif condition == 'minore':
                return float(email_value) < float(value)

            elif condition == 'in_lista':
                value_list = value if isinstance(value, list) else [value]
                return email_value in value_list

            elif condition == 'vuoto':
                return not email_value or email_value == ''

            elif condition == 'non_vuoto':
                return bool(email_value and email_value != '')

            else:
                logger.warning(f"Condizione non riconosciuta: {condition}")
                return False

        except Exception as e:
            logger.error(f"Errore valutazione condizione: {e}")
            return False

    def _get_email_field_value(self, email: Email, field: str) -> Any:
        """
        Estrae il valore di un campo dall'email.

        Args:
            email: Email
            field: Nome campo

        Returns:
            Any: Valore campo
        """
        field_map = {
            'mittente': email.mittente,
            'destinatario': email.destinatario,
            'oggetto': email.oggetto,
            'corpo': email.corpo_testo,
            'categoria': email.categoria.value if email.categoria else None,
            'account_type': email.account_type.value if email.account_type else None,
            'has_allegati': len(email.allegati) > 0 if email.allegati else False,
            'num_allegati': len(email.allegati) if email.allegati else 0,
            'data_ricezione': email.data_ricezione,
        }

        # Gestisci campi interpretazione
        if field.startswith('interpretazione.') and email.interpretazione:
            int_field = field.replace('interpretazione.', '')
            return email.interpretazione.dati_estratti.get(int_field)

        return field_map.get(field)

    def _execute_rule_actions(self, email: Email, regola: Regola) -> List[Azione]:
        """
        Esegue le azioni specificate da una regola.

        Args:
            email: Email su cui eseguire azioni
            regola: Regola con azioni da eseguire

        Returns:
            List[Azione]: Lista azioni create
        """
        azioni_dict = regola.azioni
        if not azioni_dict:
            return []

        azioni_create = []

        for azione_config in azioni_dict.get('actions', []):
            tipo = azione_config.get('type')
            params = azione_config.get('params', {})

            try:
                azione = None

                if tipo == 'crea_bozza_risposta':
                    azione = self._create_draft_action(email, params)

                elif tipo == 'crea_evento_calendario':
                    azione = self._create_calendar_action(email, params)

                elif tipo == 'carica_allegati_drive':
                    azione = self._create_drive_action(email, params)

                elif tipo == 'assegna_categoria':
                    self._assign_category(email, params)

                elif tipo == 'aggiungi_tag':
                    self._add_tag(email, params)

                elif tipo == 'inoltra_a':
                    azione = self._create_forward_action(email, params)

                elif tipo == 'marca_come_letto':
                    email.letto = True

                elif tipo == 'marca_priorita_alta':
                    # Aggiungere campo priorita al model se necessario
                    pass

                else:
                    logger.warning(f"Tipo azione non riconosciuto: {tipo}")

                if azione:
                    self.db.add(azione)
                    azioni_create.append(azione)

            except Exception as e:
                logger.error(f"Errore esecuzione azione regola '{tipo}': {e}")

        self.db.commit()
        return azioni_create

    def _create_draft_action(self, email: Email, params: Dict) -> Azione:
        """Crea azione bozza risposta."""
        template = params.get('template', 'Risposta automatica...')

        # Sostituisci variabili nel template
        body = self._replace_variables(template, email)

        return Azione(
            email_id=email.id,
            tipo_azione=TipoAzione.BOZZA_RISPOSTA,
            stato=StatoAzione.PENDING,
            parametri={
                'to': email.mittente,
                'subject': f"Re: {email.oggetto}",
                'body': body,
                'reply_to': email.message_id,
                'from_rule': True
            }
        )

    def _create_calendar_action(self, email: Email, params: Dict) -> Azione:
        """Crea azione evento calendario."""
        return Azione(
            email_id=email.id,
            tipo_azione=TipoAzione.CREA_EVENTO_CALENDARIO,
            stato=StatoAzione.PENDING,
            parametri={
                'summary': params.get('title', email.oggetto),
                'date': params.get('date'),
                'time': params.get('time'),
                'location': params.get('location'),
                'description': email.corpo_testo[:500],
                'from_rule': True
            }
        )

    def _create_drive_action(self, email: Email, params: Dict) -> Optional[Azione]:
        """Crea azione upload Drive."""
        if not email.allegati:
            return None

        return Azione(
            email_id=email.id,
            tipo_azione=TipoAzione.CARICA_SU_DRIVE,
            stato=StatoAzione.PENDING,
            parametri={
                'folder_name': params.get('folder_name', 'SNALS Allegati'),
                'from_rule': True
            }
        )

    def _create_forward_action(self, email: Email, params: Dict) -> Azione:
        """Crea azione inoltra email."""
        return Azione(
            email_id=email.id,
            tipo_azione=TipoAzione.INOLTRA_EMAIL,
            stato=StatoAzione.PENDING,
            parametri={
                'to': params.get('to'),
                'cc': params.get('cc'),
                'note': params.get('note', ''),
                'from_rule': True
            }
        )

    def _assign_category(self, email: Email, params: Dict):
        """Assegna categoria all'email."""
        categoria_str = params.get('categoria')
        if categoria_str:
            try:
                email.categoria = EmailCategory(categoria_str)
                logger.info(f"Categoria '{categoria_str}' assegnata a email {email.id}")
            except ValueError:
                logger.warning(f"Categoria non valida: {categoria_str}")

    def _add_tag(self, email: Email, params: Dict):
        """Aggiunge tag all'email."""
        tag = params.get('tag')
        if tag:
            # Implementare sistema tag se necessario
            logger.info(f"Tag '{tag}' aggiunto a email {email.id}")

    def _replace_variables(self, template: str, email: Email) -> str:
        """
        Sostituisce variabili nel template.

        Variabili supportate:
        - {mittente}
        - {oggetto}
        - {data}
        - {interpretazione.campo}
        """
        variables = {
            '{mittente}': email.mittente or '',
            '{oggetto}': email.oggetto or '',
            '{data}': email.data_ricezione.strftime('%d/%m/%Y %H:%M') if email.data_ricezione else '',
        }

        # Sostituisci variabili semplici
        result = template
        for var, value in variables.items():
            result = result.replace(var, value)

        # Sostituisci variabili interpretazione
        if email.interpretazione:
            for key, value in email.interpretazione.dati_estratti.items():
                var_name = f'{{interpretazione.{key}}}'
                if var_name in result:
                    result = result.replace(var_name, str(value))

        return result

    def test_rule(self, regola_id: int, email_id: int) -> Dict:
        """
        Testa una regola su una email specifica (senza eseguire azioni).

        Args:
            regola_id: ID regola da testare
            email_id: ID email su cui testare

        Returns:
            Dict: Risultato test
        """
        regola = self.db.query(Regola).filter(Regola.id == regola_id).first()
        email = self.db.query(Email).filter(Email.id == email_id).first()

        if not regola:
            return {'error': 'Regola non trovata'}

        if not email:
            return {'error': 'Email non trovata'}

        # Valuta condizioni
        match = self._evaluate_conditions(email, regola.condizioni)

        return {
            'regola_nome': regola.nome,
            'email_oggetto': email.oggetto,
            'match': match,
            'azioni_che_sarebbero_eseguite': len(regola.azioni.get('actions', [])) if match else 0
        }
