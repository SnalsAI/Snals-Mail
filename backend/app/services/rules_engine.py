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
from app.models.delegato import Zona

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
            Regola.attivo == True
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

        Supporta due formati:
        1. Formato semplice: {"categoria": "valore"}
        2. Formato avanzato: {"operator": "AND", "rules": [...]}

        Args:
            email: Email da valutare
            condizioni: Dict con condizioni da valutare

        Returns:
            bool: True se tutte le condizioni sono soddisfatte
        """
        if not condizioni:
            return True

        # FORMATO SEMPLICE (database attuale): {"categoria": "valore", "mittente": "xyz"}
        if 'rules' not in condizioni and 'operator' not in condizioni:
            # Valuta ogni chiave come condizione uguale
            for field, value in condizioni.items():
                email_value = self._get_email_field_value(email, field)

                # Confronto case-insensitive per stringhe
                if isinstance(value, str) and isinstance(email_value, str):
                    if email_value.lower() != value.lower():
                        return False
                elif email_value != value:
                    return False

            return True

        # FORMATO AVANZATO: {"operator": "AND", "rules": [...]}
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
        # Condizioni speciali che non richiedono un campo specifico
        # devono essere gestite PRIMA del check del valore del campo
        if condition == 'scuola_in_zona':
            # Verifica se la scuola mittente appartiene a una zona specifica
            # Questa condizione usa sempre il mittente, indipendentemente dal field
            return self._check_school_in_zona(email.mittente, value)

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
            'categoria': email.get_categoria_value(),
            'sottocategoria': email.sottocategoria,
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

    def _check_school_in_zona(self, mittente: str, zona_nome: str) -> bool:
        """
        Verifica se la scuola mittente appartiene alla zona specificata.

        Args:
            mittente: Email mittente (es: taic12345@istruzione.it)
            zona_nome: Nome della zona da verificare

        Returns:
            bool: True se la scuola appartiene alla zona
        """
        try:
            import re

            # Prima prova a estrarre mittente reale da "Per conto di:" nelle PEC
            per_conto_match = re.search(r'per conto di:\s*([^\s<>"]+@[^\s<>"]+)', mittente.lower())
            if per_conto_match:
                real_sender = per_conto_match.group(1)
                logger.debug(f"Estratto mittente reale da 'Per conto di:': {real_sender}")
                mittente = real_sender

            # Estrai codice scuola dal mittente (formato: codice meccanografico)
            # 4 lettere + 6 caratteri alfanumerici (es: taic858004 o taic84300a)
            match = re.search(r'([a-z]{4}[a-z0-9]{6})@(pec\.)?istruzione\.it', mittente.lower())
            if not match:
                logger.debug(f"Mittente {mittente} non è una scuola valida")
                return False

            school_code = match.group(1).upper()

            # Identifica la scuola e ottieni il comune
            from app.services.school_identifier import get_school_identifier
            school_identifier = get_school_identifier()
            school_info = school_identifier.get_school_info(school_code)

            if not school_info:
                logger.debug(f"Scuola {school_code} non trovata nel database")
                return False

            comune = school_info.get('comune', '').upper()
            if not comune:
                logger.debug(f"Comune non disponibile per scuola {school_code}")
                return False

            # Cerca la zona specificata
            zona = self.db.query(Zona).filter(
                Zona.nome == zona_nome,
                Zona.attiva == True
            ).first()

            if not zona:
                logger.warning(f"Zona '{zona_nome}' non trovata nel database")
                return False

            # Verifica se il comune è nella zona
            comuni_zona = [c.upper() for c in zona.get_comuni()]
            is_in_zona = comune in comuni_zona

            if is_in_zona:
                logger.info(f"✅ Scuola {school_code} ({comune}) appartiene alla zona '{zona_nome}'")
            else:
                logger.debug(f"Scuola {school_code} ({comune}) NON appartiene alla zona '{zona_nome}'")

            return is_in_zona

        except Exception as e:
            logger.error(f"Errore verifica scuola in zona: {e}")
            return False

    def _execute_rule_actions(self, email: Email, regola: Regola) -> List[Azione]:
        """
        Esegue le azioni specificate da una regola.

        Supporta due formati:
        1. Formato database: lista diretta [{"tipo": "BOZZA_RISPOSTA", "params": {...}}]
        2. Formato avanzato: {"actions": [{"type": "crea_bozza_risposta", "params": {...}}]}

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

        # Determina formato
        if isinstance(azioni_dict, list):
            # FORMATO DATABASE: lista diretta
            azioni_list = azioni_dict
        else:
            # FORMATO AVANZATO: dict con chiave "actions"
            azioni_list = azioni_dict.get('actions', [])

        for azione_config in azioni_list:
            # Supporta entrambi i formati: "tipo" e "type"
            tipo = azione_config.get('tipo') or azione_config.get('type')
            params = azione_config.get('params', {})

            try:
                azione = None

                # Mappatura tipi azione database → handler
                if tipo in ['BOZZA_RISPOSTA', 'crea_bozza_risposta']:
                    azione = self._create_draft_response_action(email, params)

                elif tipo in ['BOZZA_APPUNTAMENTO', 'crea_bozza_appuntamento']:
                    azione = self._create_draft_appointment_action(email, params)

                elif tipo in ['BOZZA_TESSERAMENTO', 'crea_bozza_tesseramento']:
                    azione = self._create_draft_membership_action(email, params)

                elif tipo in ['EVENTO_CALENDARIO', 'crea_evento_calendario']:
                    azione = self._create_calendar_event_action(email, params)

                # Google Drive upload disabilitato - non disponibile con account Gmail personale
                # elif tipo in ['UPLOAD_DRIVE', 'carica_allegati_drive']:
                #     azione = self._create_drive_upload_action(email, params)

                elif tipo in ['SINTESI', 'genera_sintesi']:
                    azione = self._create_summary_action(email, params)

                elif tipo in ['INDICIZZA_RAG', 'indicizza_rag']:
                    azione = self._create_rag_index_action(email, params)

                elif tipo in ['PARSE_INTERPELLO', 'parse_interpello']:
                    azione = self._create_parse_interpello_action(email, params)

                elif tipo in ['ARCHIVIA', 'archivia']:
                    azione = self._create_archive_action(email, params)

                elif tipo in ['SEGNA_IMPORTANTE', 'marca_importante']:
                    azione = self._create_mark_important_action(email, params)

                elif tipo in ['INOLTRA', 'INOLTRA_EMAIL', 'inoltra_a']:
                    azione = self._create_forward_action(email, params)

                elif tipo in ['INOLTRA_DELEGATI_ZONA', 'inoltra_delegati_zona']:
                    azione = self._create_forward_delegati_zona_action(email, params)

                elif tipo in ['INVIA_NOTIFICA', 'NOTIFICA', 'invia_notifica', 'notifica']:
                    azione = self._create_notify_action(email, params)

                elif tipo == 'assegna_categoria':
                    self._assign_category(email, params)

                elif tipo == 'aggiungi_tag':
                    self._add_tag(email, params)

                elif tipo == 'marca_come_letto':
                    email.letto = True

                elif tipo in ['SPAM', 'spam']:
                    azione = self._create_spam_action(email, params)

                else:
                    logger.warning(f"Tipo azione non riconosciuto: {tipo}")

                if azione:
                    # Controlla se esiste già un'azione dello stesso tipo per questa email
                    existing = self.db.query(Azione).filter(
                        Azione.email_id == email.id,
                        Azione.tipo == azione.tipo
                    ).first()

                    if existing:
                        logger.info(f"Azione {azione.tipo.value} già esistente per email {email.id}, skip")
                    else:
                        self.db.add(azione)
                        azioni_create.append(azione)

            except Exception as e:
                logger.error(f"Errore esecuzione azione regola '{tipo}': {e}", exc_info=True)

        # Aggiorna statistiche regola
        regola.volte_applicata = (regola.volte_applicata or 0) + 1
        regola.ultima_applicazione = datetime.now()

        self.db.commit()
        logger.info(f"✅ Regola '{regola.nome}' applicata → {len(azioni_create)} azioni create")
        return azioni_create

    def _create_draft_response_action(self, email: Email, params: Dict) -> Azione:
        """Crea azione bozza risposta generica o con LLM."""
        parametri = {
            'to': email.mittente,
            'subject': f"Re: {email.oggetto}",
            'reply_to': email.message_id,
            'from_rule': True
        }

        # Se usa LLM, non serve body predefinito
        if params.get('usa_llm'):
            parametri['usa_llm'] = True
            parametri['destinazione'] = params.get('destinazione', 'webmail_bozze')
        else:
            # Usa template se fornito
            template = params.get('template', 'Risposta automatica...')
            parametri['body'] = self._replace_variables(template, email)

        return Azione(
            email_id=email.id,
            tipo=TipoAzione.BOZZA_RISPOSTA,
            stato=StatoAzione.IN_CODA,
            dettagli={'parametri': parametri, 'from_rule': True}
        )

    def _create_draft_appointment_action(self, email: Email, params: Dict) -> Azione:
        """Crea azione bozza appuntamento."""
        parametri = {
            'to': email.mittente,
            'subject': f"Re: {email.oggetto}",
            'reply_to': email.message_id,
            'piattaforma': params.get('piattaforma', 'calendario_snals'),
            'include_link': params.get('include_link', True),
            'from_rule': True
        }

        return Azione(
            email_id=email.id,
            tipo=TipoAzione.BOZZA_APPUNTAMENTO,
            stato=StatoAzione.IN_CODA,
            dettagli={'parametri': parametri, 'from_rule': True}
        )

    def _create_draft_membership_action(self, email: Email, params: Dict) -> Azione:
        """Crea azione bozza tesseramento."""
        parametri = {
            'to': email.mittente,
            'subject': f"Re: {email.oggetto}",
            'reply_to': email.message_id,
            'repository': params.get('repository', 'moduli_tesseramento'),
            'include_moduli': params.get('include_moduli', True),
            'from_rule': True
        }

        return Azione(
            email_id=email.id,
            tipo=TipoAzione.BOZZA_TESSERAMENTO,
            stato=StatoAzione.IN_CODA,
            dettagli={'parametri': parametri, 'from_rule': True}
        )

    def _create_calendar_event_action(self, email: Email, params: Dict) -> Azione:
        """Crea azione evento calendario."""
        parametri = {
            'analizza_documento': params.get('analizza_documento', False),
            'estrai_data_ora': params.get('estrai_data_ora', False),
            'calendario': params.get('calendario', 'primary'),
            'from_rule': True
        }

        # Se forniti manualmente, usa quelli
        if params.get('summary'):
            parametri['summary'] = params.get('summary')
        if params.get('date'):
            parametri['date'] = params.get('date')
        if params.get('time'):
            parametri['time'] = params.get('time')
        if params.get('location'):
            parametri['location'] = params.get('location')

        return Azione(
            email_id=email.id,
            tipo=TipoAzione.EVENTO_CALENDARIO,
            stato=StatoAzione.IN_CODA,
            dettagli={'parametri': parametri, 'from_rule': True}
        )

    # Google Drive upload disabilitato - non disponibile con account Gmail personale
    # def _create_drive_upload_action(self, email: Email, params: Dict) -> Optional[Azione]:
    #     """Crea azione upload Drive."""
    #     pass  # Metodo disabilitato

    def _create_summary_action(self, email: Email, params: Dict) -> Azione:
        """Crea azione genera sintesi."""
        parametri = {
            'tipo_sintesi': params.get('tipo_sintesi', 'giornaliera'),
            'frequenza': params.get('frequenza', 'daily'),
            'salva_su': params.get('salva_su', 'archivio'),
            'from_rule': True
        }

        return Azione(
            email_id=email.id,
            tipo=TipoAzione.SINTESI,
            stato=StatoAzione.IN_CODA,
            dettagli={'parametri': parametri, 'from_rule': True}
        )

    def _create_rag_index_action(self, email: Email, params: Dict) -> Azione:
        """Crea azione indicizza documenti nel RAG."""
        parametri = {
            'mantieni_metadati': params.get('mantieni_metadati', True),
            'from_rule': True
        }

        return Azione(
            email_id=email.id,
            tipo=TipoAzione.INDICIZZA_RAG,
            stato=StatoAzione.IN_CODA,
            dettagli={'parametri': parametri, 'from_rule': True}
        )

    def _create_archive_action(self, email: Email, params: Dict) -> Azione:
        """Crea azione archivia."""
        parametri = {
            'folder': params.get('folder', 'archivio'),
            'from_rule': True
        }

        return Azione(
            email_id=email.id,
            tipo=TipoAzione.ARCHIVIA,
            stato=StatoAzione.IN_CODA,
            dettagli={'parametri': parametri, 'from_rule': True}
        )

    def _create_mark_important_action(self, email: Email, params: Dict) -> Azione:
        """Crea azione segna importante."""
        return Azione(
            email_id=email.id,
            tipo=TipoAzione.SEGNA_IMPORTANTE,
            stato=StatoAzione.IN_CODA,
            dettagli={'parametri': {}, 'from_rule': True}
        )

    def _create_forward_action(self, email: Email, params: Dict) -> Azione:
        """Crea azione inoltra email."""
        return Azione(
            email_id=email.id,
            tipo=TipoAzione.INOLTRA_EMAIL,
            stato=StatoAzione.IN_CODA,
            dettagli={
                'parametri': {
                    'to': params.get('to'),
                    'cc': params.get('cc'),
                    'note': params.get('note', ''),
                    'from_rule': True
                }
            }
        )

    def _create_forward_delegati_zona_action(self, email: Email, params: Dict) -> Azione:
        """
        Crea azione inoltra ai delegati della zona.
        Identifica automaticamente la zona della scuola mittente e inoltra ai delegati.
        """
        return Azione(
            email_id=email.id,
            tipo=TipoAzione.INOLTRA_DELEGATI_ZONA,
            stato=StatoAzione.IN_CODA,
            dettagli={
                'parametri': {
                    'zone': params.get('zone', []),
                    'note': params.get('note', 'Email inoltrata automaticamente ai delegati della zona.'),
                    'from_rule': True
                }
            }
        )

    def _create_parse_interpello_action(self, email: Email, params: Dict) -> Azione:
        """Crea azione parsing interpello."""
        parametri = {
            'strategy': params.get('strategy', 'smart'),
            'from_rule': True
        }

        return Azione(
            email_id=email.id,
            tipo=TipoAzione.PARSE_INTERPELLO,
            stato=StatoAzione.IN_CODA,
            dettagli={'parametri': parametri, 'from_rule': True}
        )

    def _create_notify_action(self, email: Email, params: Dict) -> Azione:
        """Crea azione invio notifica."""
        parametri = {
            'destinatari': params.get('destinatari', []),
            'messaggio': params.get('messaggio', ''),
            'canale': params.get('canale', 'email'),  # email, telegram, webhook
            'priorita': params.get('priorita', 'normale'),
            'from_rule': True
        }

        return Azione(
            email_id=email.id,
            tipo=TipoAzione.INVIA_NOTIFICA,
            stato=StatoAzione.IN_CODA,
            dettagli={'parametri': parametri, 'from_rule': True}
        )

    def _create_spam_action(self, email: Email, params: Dict) -> Azione:
        """Crea azione SPAM (senza sintesi, solo marcatura)."""
        return Azione(
            email_id=email.id,
            tipo=TipoAzione.SPAM,
            stato=StatoAzione.COMPLETATA,  # Già completata, non richiede elaborazione
            dettagli={
                'from_rule': True,
                'categoria': 'SPAM',
                'motivo': params.get('motivo', 'Email identificata come spam')
            },
            risultato={
                'status': 'completed',
                'message': 'Email marcata come SPAM',
                'timestamp': datetime.now().isoformat()
            }
        )

    def _assign_category(self, email: Email, params: Dict):
        """Assegna categoria all'email."""
        categoria_str = params.get('categoria')
        if categoria_str:
            try:
                # Valida che sia una categoria valida
                EmailCategory(categoria_str)
                # Assegna la stringa direttamente (categoria ora è String, non Enum)
                email.categoria = categoria_str
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
