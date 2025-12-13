"""
Action Executor - Esegue azioni automatiche sulle email.

FASE 4: Azioni Automatiche
"""
import logging
from typing import Optional, Dict, List
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.azione import Azione, TipoAzione, StatoAzione
from app.models.email import Email
from app.models.interpretazione import Interpretazione
from app.models.evento import EventoCalendario
from app.integrations.llm_client import LLMClient
# Google Drive rimosso - non disponibile con account Gmail personale
# from app.integrations.google_drive_client import GoogleDriveClient
from app.integrations.google_calendar_client import GoogleCalendarClient
from app.integrations.webmail_client import WebmailClient
from app.services.smart_generator import SmartResponseGenerator, TaskType
from app.services.unified_extractor import get_unified_extractor
from app.services.email_rate_limiter import get_email_rate_limiter
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class ActionExecutor:
    """Esecutore di azioni automatiche sulle email."""

    def __init__(self, db: Session):
        """
        Inizializza l'action executor.

        Args:
            db: Sessione database
        """
        self.db = db
        self.llm_client = LLMClient()
        # Google Drive rimosso - non disponibile con account Gmail personale
        # self.drive_client = GoogleDriveClient()
        self.calendar_client = GoogleCalendarClient()

        # Inizializza SmartResponseGenerator per generazione risposte intelligenti
        openai_key = getattr(settings, 'OPENAI_API_KEY', None)
        openai_model = getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini')
        daily_limit = getattr(settings, 'OPENAI_DAILY_LIMIT_EUR', 1.0)

        if openai_key:
            self.smart_generator = SmartResponseGenerator(
                openai_api_key=openai_key,
                openai_model=openai_model,
                daily_limit_eur=daily_limit
            )
            logger.info(f"✅ SmartResponseGenerator inizializzato (budget: €{daily_limit}/giorno)")
        else:
            self.smart_generator = None
            logger.warning("⚠️ SmartResponseGenerator non disponibile (OPENAI_API_KEY mancante)")

        # Inizializza UnifiedExtractor per estrazione dati (calendario e interpello)
        # Usa coda LLM per evitare sovraccarichi e legge impostazioni ChatGPT da sistema
        self.unified_extractor = get_unified_extractor()
        logger.info("✅ UnifiedExtractor inizializzato per estrazione dati eventi")

    def _normalize_luogo(self, luogo) -> Optional[str]:
        """Normalizza il campo luogo in una stringa."""
        if luogo is None:
            return None
        if isinstance(luogo, str):
            return luogo
        if isinstance(luogo, dict):
            # Estrai l'indirizzo dal dict
            for key in ['sede/indirizzo', 'indirizzo', 'sede', 'address', 'luogo']:
                if key in luogo and luogo[key]:
                    return str(luogo[key])
            # Se non trova chiavi note, converti in stringa
            return ', '.join(f"{v}" for v in luogo.values() if v)
        return str(luogo)

    def _ensure_scuola_and_luogo(self, event_data: Dict, email: Email) -> Dict:
        """
        Garantisce che scuola e luogo siano sempre correttamente popolati.

        LOGICA:
        1. Estrae SEMPRE il codice meccanografico dal mittente
        2. Cerca SEMPRE la scuola nel database per ottenere nome e indirizzo
        3. Scuola = NOME scuola (non codice meccanografico)
        4. Luogo = luogo originale + indirizzo scuola (es. "Ufficio del dirigente - Via Roma 1, Taranto - IC MORLEO")

        Args:
            event_data: Dizionario con dati evento estratti
            email: Email sorgente

        Returns:
            event_data aggiornato con scuola e luogo corretti
        """
        import re
        from app.services.school_identifier import get_school_identifier

        school_identifier = get_school_identifier()

        # 1. ESTRAI SEMPRE IL CODICE SCUOLA DAL MITTENTE
        codice_scuola = None
        if email.mittente:
            # Pattern per codici meccanografici: 4 lettere + 6 alfanumerici
            match = re.search(r'([a-zA-Z]{4}[a-zA-Z0-9]{6})', email.mittente)
            if match:
                codice_scuola = match.group(1).upper()
                logger.info(f"📍 Codice scuola estratto da mittente: {codice_scuola}")

        # 2. CERCA NEL DATABASE PER OTTENERE NOME E INDIRIZZO
        school_info = None
        if codice_scuola:
            school_info = school_identifier.get_school_info(codice_scuola)
            if school_info:
                logger.info(f"🏫 Scuola trovata nel database: {school_info.get('nome')} - {school_info.get('comune')}")

        # 3. POPOLA SCUOLA CON IL NOME (non il codice!)
        if school_info and not event_data.get('scuola'):
            nome_scuola = school_info.get('nome', '')
            comune = school_info.get('comune', '')
            if nome_scuola:
                # Usa nome scuola con comune
                event_data['scuola'] = f"{nome_scuola} ({comune})" if comune else nome_scuola
                logger.info(f"🏫 Campo scuola impostato: {event_data['scuola']}")

        # 4. ARRICCHISCI LUOGO (mantieni originale + aggiungi indirizzo scuola)
        luogo_attuale = event_data.get('luogo') or event_data.get('sede') or ''
        luogo_ha_indirizzo = self._is_valid_address(luogo_attuale)

        if school_info:
            indirizzo_db = school_info.get('indirizzo', '')
            comune_db = school_info.get('comune', '')
            nome_scuola = school_info.get('nome', '')
            indirizzo_completo = f"{indirizzo_db}, {comune_db} (TA)" if indirizzo_db else f"{comune_db} (TA)"

            if not luogo_attuale:
                # Nessun luogo → usa indirizzo completo
                event_data['luogo'] = f"{indirizzo_completo} - {nome_scuola}"
                logger.info(f"📍 Luogo impostato da database: {event_data['luogo']}")
            elif not luogo_ha_indirizzo:
                # Luogo generico (es. "Ufficio del dirigente") → mantieni + aggiungi indirizzo
                event_data['luogo'] = f"{luogo_attuale} - {indirizzo_completo} - {nome_scuola}"
                logger.info(f"📍 Luogo arricchito: {event_data['luogo']}")
            else:
                # Luogo ha già indirizzo → aggiungi solo nome scuola se manca
                if nome_scuola and nome_scuola.upper() not in luogo_attuale.upper():
                    event_data['luogo'] = f"{luogo_attuale} - {nome_scuola}"
                    logger.info(f"📍 Aggiunto nome scuola al luogo: {event_data['luogo']}")

        elif codice_scuola and not luogo_ha_indirizzo:
            # Scuola non nel database ma abbiamo codice → segnala
            if luogo_attuale:
                event_data['luogo'] = f"{luogo_attuale} - Scuola {codice_scuola}"
            else:
                event_data['luogo'] = f"Scuola {codice_scuola}"
            logger.warning(f"⚠️ Scuola {codice_scuola} non trovata nel database")

        return event_data

    def _is_valid_address(self, luogo: str) -> bool:
        """
        Verifica se un luogo è un indirizzo valido (non generico).

        Un indirizzo è valido se contiene:
        - Via/Viale/Piazza/Corso/Contrada + numero civico

        NON è valido se è solo:
        - "Ufficio del dirigente"
        - "Presidenza"
        - Nome scuola senza indirizzo
        - Stringa troppo corta

        Args:
            luogo: Stringa con il luogo

        Returns:
            True se è un indirizzo valido
        """
        if not luogo or len(luogo) < 10:
            return False

        luogo_lower = luogo.lower()

        # Parole chiave che indicano un luogo generico (non valido)
        luoghi_generici = [
            'ufficio', 'presidenza', 'dirigente', 'segreteria',
            'ai rappresentanti', 'alle oo.ss', 'alle rsu'
        ]
        if any(generico in luogo_lower for generico in luoghi_generici):
            # Controlla se c'è anche un indirizzo valido
            has_address = any(prefix in luogo_lower for prefix in [
                'via ', 'viale ', 'piazza ', 'p.zza ', 'corso ',
                'contrada ', 'c.da ', 'vicolo ', 'largo '
            ])
            if not has_address:
                return False

        # Verifica presenza di un tipo di via
        prefissi_via = ['via ', 'viale ', 'piazza ', 'p.zza ', 'corso ',
                       'contrada ', 'c.da ', 'vicolo ', 'largo ', 'loc.', 's.s.']
        has_prefix = any(prefix in luogo_lower for prefix in prefissi_via)

        return has_prefix

    def _detect_event_modification(self, oggetto: str, corpo: str, allegati_testo: str = None) -> Dict:
        """
        Rileva se un'email riguarda una modifica/rinvio/annullamento di un evento esistente.

        IMPORTANTE: Distingue tra:
        - "Rinvio del tavolo del 26.11" → CANCELLAZIONE del 26.11 (is_modification=True)
        - "Convocazione per il giorno 11.12" → NUOVA DATA, non è una modifica (is_modification=False)

        Args:
            oggetto: Oggetto dell'email
            corpo: Corpo dell'email
            allegati_testo: Testo estratto dagli allegati

        Returns:
            Dict con:
                - is_modification: True se CANCELLA/MODIFICA un evento esistente
                - modification_type: 'rinvio', 'annullamento', 'modifica_data', 'modifica_ora', None
                - keywords_found: lista di parole chiave trovate
                - cancelled_date: data che viene cancellata/rinviata (se rilevata)
        """
        import re

        # Combina tutto il testo disponibile
        full_text = f"{oggetto or ''} {corpo or ''} {allegati_testo or ''}".lower()
        oggetto_lower = (oggetto or '').lower()

        result = {
            'is_modification': False,
            'modification_type': None,
            'keywords_found': [],
            'cancelled_date': None
        }

        # Pattern che indicano CANCELLAZIONE di una data specifica
        # Questi pattern catturano "rinvio DEL [data]", "rinviato IL [data]", etc.
        CANCELLATION_PATTERNS = [
            # "Rinvio ... del XX.XX" - cattura qualsiasi cosa tra rinvio e la data
            r'\brinvio\b[\w\s]*del\s+(\d{1,2}[\.\/]\d{1,2}(?:[\.\/]\d{2,4})?)',
            # "tavolo/riunione del XX.XX rinviato/a"
            r'(?:tavolo|incontro|riunione)\s+del\s+(\d{1,2}[\.\/]\d{1,2})\s+[\w\s]*rinviat[oa]',
            # "rinviato/a la riunione del XX.XX"
            r'rinviat[oa]\s+[\w\s]*del\s+(\d{1,2}[\.\/]\d{1,2})',
            # "rinviato a data da destinarsi" (senza data specifica)
            r'(?:è\s+)?rinviat[oa]\s+a\s+data\s+da\s+destinarsi',
            # "posticipato/a la riunione"
            r'(?:è\s+)?posticipal[oa]\s+(?:la\s+)?(?:riunione|convocazione)',
            # "sospeso il tavolo"
            r'(?:è\s+)?sospeso\s+(?:il\s+)?(?:tavolo|incontro)',
        ]

        # Pattern che indicano ANNULLAMENTO definitivo
        ANNULLAMENTO_PATTERNS = [
            r'(?:è\s+)?annullat[oa]\s+(?:la\s+)?(?:riunione|convocazione|tavolo)',
            r'(?:è\s+)?cancel+at[oa]\s+(?:la\s+)?(?:riunione|convocazione)',
            r'(?:la\s+)?(?:riunione|convocazione)\s+(?:è\s+)?annullat[oa]',
            r'non\s+(?:si\s+)?terrà\s+(?:più\s+)?(?:la\s+)?(?:riunione|convocazione)',
            r'non\s+avrà\s+(?:più\s+)?luogo',
        ]

        # Pattern per modifiche orario
        MODIFICA_ORA_PATTERNS = [
            r'nuov[oa]\s+orario',
            r'orario\s+modificat[oa]',
            r'(?:alle\s+)?ore\s+\d{1,2}[:\.]?\d{0,2}\s+anziché',
            r'cambio\s+(?:di\s+)?orario',
        ]

        # ESCLUSIONE: Se l'oggetto è una semplice convocazione senza menzione di rinvio
        # Pattern: "Convocazione per il giorno X" senza parole di rinvio
        is_simple_convocation = bool(re.search(
            r'convocazione\s+(?:delegazione\s+)?(?:trattante\s+)?per\s+(?:il\s+)?(?:giorno\s+)?\d{1,2}',
            oggetto_lower
        ))

        # Se è una semplice convocazione E non contiene parole di rinvio nell'oggetto, è una NUOVA data
        has_rinvio_in_oggetto = bool(re.search(r'\brinvi[oa]', oggetto_lower))

        if is_simple_convocation and not has_rinvio_in_oggetto:
            logger.info(f"📅 Rilevata NUOVA convocazione (non rinvio): {oggetto[:60]}")
            return result  # Non è una modifica, è una nuova convocazione

        # Cerca pattern di CANCELLAZIONE
        for pattern in CANCELLATION_PATTERNS:
            match = re.search(pattern, full_text)
            if match:
                result['is_modification'] = True
                result['modification_type'] = 'rinvio'
                result['keywords_found'].append(match.group(0)[:50])
                # Estrai la data cancellata se presente nel match
                if match.groups():
                    result['cancelled_date'] = match.group(1)
                break

        # Cerca pattern di ANNULLAMENTO (priorità più alta)
        for pattern in ANNULLAMENTO_PATTERNS:
            match = re.search(pattern, full_text)
            if match:
                result['is_modification'] = True
                result['modification_type'] = 'annullamento'
                result['keywords_found'].append(match.group(0)[:50])
                break

        # Cerca modifiche orario
        if not result['is_modification']:
            for pattern in MODIFICA_ORA_PATTERNS:
                match = re.search(pattern, full_text)
                if match:
                    result['is_modification'] = True
                    result['modification_type'] = 'modifica_ora'
                    result['keywords_found'].append(match.group(0)[:50])
                    break

        if result['is_modification']:
            logger.info(
                f"🔍 Rilevata MODIFICA evento: tipo={result['modification_type']}, "
                f"keywords={result['keywords_found']}, data_cancellata={result.get('cancelled_date')}"
            )
        else:
            logger.debug(f"📅 Nessuna modifica rilevata, trattata come nuova convocazione")

        return result

    def _find_existing_event(self, email: Email, event_data: Dict, data_inizio: datetime = None) -> Optional[EventoCalendario]:
        """
        Cerca eventi esistenti che potrebbero essere correlati a questa email.

        Args:
            email: Email corrente
            event_data: Dati estratti dall'email
            data_inizio: Data inizio estratta (se disponibile)

        Returns:
            EventoCalendario esistente se trovato, None altrimenti
        """
        from datetime import timedelta
        import re

        # Cerca per scuola mittente
        codice_mecc = None
        if email.mittente and '@istruzione.it' in email.mittente.lower():
            match = re.search(r'([a-z]{4}\d{5,}[a-z]?)@istruzione\.it', email.mittente.lower())
            if match:
                codice_mecc = match.group(1).upper()

        # Costruisci query base
        query = self.db.query(EventoCalendario)

        # Se abbiamo una data, cerca eventi in un range di ±7 giorni
        if data_inizio:
            data_min = data_inizio - timedelta(days=7)
            data_max = data_inizio + timedelta(days=7)
            query = query.filter(
                EventoCalendario.data_inizio >= data_min,
                EventoCalendario.data_inizio <= data_max
            )

        # Se abbiamo codice meccanografico, cerca per scuola
        if codice_mecc:
            # Cerca eventi che contengono il codice meccanografico nella scuola o sono della stessa scuola
            eventi = query.filter(
                EventoCalendario.scuola.ilike(f'%{codice_mecc}%')
            ).order_by(EventoCalendario.data_inizio.desc()).all()

            if eventi:
                logger.info(f"🔍 Trovati {len(eventi)} eventi esistenti per scuola {codice_mecc}")
                # Restituisci l'evento più recente (probabile quello da modificare)
                return eventi[0]

        # Fallback: cerca per data esatta se disponibile
        if data_inizio:
            # Cerca evento nello stesso giorno
            data_giorno_inizio = data_inizio.replace(hour=0, minute=0, second=0)
            data_giorno_fine = data_inizio.replace(hour=23, minute=59, second=59)

            eventi = self.db.query(EventoCalendario).filter(
                EventoCalendario.data_inizio >= data_giorno_inizio,
                EventoCalendario.data_inizio <= data_giorno_fine
            ).all()

            if eventi:
                # Cerca match per titolo simile
                titolo_email = (email.oggetto or '').lower()
                for evento in eventi:
                    titolo_evento = (evento.titolo or '').lower()
                    # Match se contengono parole chiave comuni
                    if ('contrattazione' in titolo_email and 'contrattazione' in titolo_evento) or \
                       ('rsu' in titolo_email and 'rsu' in titolo_evento) or \
                       ('tavolo' in titolo_email and 'tavolo' in titolo_evento):
                        logger.info(f"🔍 Trovato evento correlato per titolo: {evento.titolo[:50]}...")
                        return evento

        return None

    def _extract_new_date_from_email(self, oggetto: str, corpo: str) -> Optional[Dict]:
        """
        Estrae la nuova data da un'email di rinvio.

        Cerca pattern come:
        - "nuova data 20/11/2025"
        - "rinviato al 22.11"
        - "spostato al giorno 15 dicembre"
        - "nuova convocazione per il 10/12/2025"

        Returns:
            Dict con 'data' e 'ora' se trovati, None altrimenti
        """
        import re

        full_text = f"{oggetto or ''} {corpo or ''}".lower()

        # Pattern per nuova data
        NEW_DATE_PATTERNS = [
            # "nuova data DD/MM/YYYY" o "nuova data DD.MM.YYYY"
            r'nuov[ao]\s+dat[ao]\s+(?:del\s+)?(\d{1,2})[\.\/](\d{1,2})[\.\/](\d{2,4})',
            # "rinviato al DD/MM" o "spostato al DD.MM"
            r'(?:rinviat[oa]|spostat[oa]|posticipal[oa])\s+al\s+(?:giorno\s+)?(\d{1,2})[\.\/](\d{1,2})(?:[\.\/](\d{2,4}))?',
            # "nuova convocazione per il DD/MM/YYYY"
            r'nuov[ao]\s+convocazione\s+per\s+(?:il\s+)?(?:giorno\s+)?(\d{1,2})[\.\/](\d{1,2})[\.\/](\d{2,4})',
            # "per il giorno DD/MM/YYYY" (dopo menzione di rinvio)
            r'per\s+(?:il\s+)?giorno\s+(\d{1,2})[\.\/](\d{1,2})[\.\/](\d{2,4})',
            # "al DD mese YYYY" (es: "al 15 dicembre 2025")
            r'(?:rinviat[oa]|spostat[oa])\s+al\s+(\d{1,2})\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s*(\d{4})?',
        ]

        mesi_map = {
            'gennaio': '01', 'febbraio': '02', 'marzo': '03', 'aprile': '04',
            'maggio': '05', 'giugno': '06', 'luglio': '07', 'agosto': '08',
            'settembre': '09', 'ottobre': '10', 'novembre': '11', 'dicembre': '12'
        }

        for pattern in NEW_DATE_PATTERNS:
            match = re.search(pattern, full_text)
            if match:
                groups = match.groups()

                # Gestione pattern con mese testuale
                if any(m in pattern for m in ['gennaio', 'febbraio']):
                    giorno = groups[0].zfill(2)
                    mese = mesi_map.get(groups[1], '01')
                    anno = groups[2] if groups[2] else str(datetime.now().year)
                else:
                    giorno = groups[0].zfill(2)
                    mese = groups[1].zfill(2)
                    anno = groups[2] if len(groups) > 2 and groups[2] else str(datetime.now().year)
                    # Normalizza anno a 4 cifre
                    if len(anno) == 2:
                        anno = f"20{anno}"

                # Cerca anche l'ora
                ora = '09:00'  # default
                ora_match = re.search(r'(?:ore|alle|h\.?)\s*(\d{1,2})[:\.]?(\d{2})?', full_text)
                if ora_match:
                    ora_h = ora_match.group(1).zfill(2)
                    ora_m = ora_match.group(2) if ora_match.group(2) else '00'
                    ora = f"{ora_h}:{ora_m}"

                logger.info(f"📅 Estratta nuova data da email: {giorno}/{mese}/{anno} ore {ora}")
                return {
                    'data': f"{anno}-{mese}-{giorno}",
                    'ora': ora
                }

        return None

    def _update_existing_event(self, evento: EventoCalendario, modification_type: str,
                                email: Email, new_sintesi: str = None,
                                new_date_info: Dict = None) -> bool:
        """
        Aggiorna un evento esistente con le informazioni di modifica.

        Args:
            evento: Evento da aggiornare
            modification_type: Tipo di modifica ('rinvio', 'annullamento', etc.)
            email: Email di riferimento
            new_sintesi: Nuova sintesi motivo (opzionale)
            new_date_info: Dict con 'data' e 'ora' per la nuova data (opzionale)

        Returns:
            True se aggiornato con successo
        """
        try:
            prefix_map = {
                'rinvio': '[RINVIATO]',
                'annullamento': '[ANNULLATO]',
                'modifica_data': '[DATA MODIFICATA]',
                'modifica_ora': '[ORARIO MODIFICATO]'
            }

            stato_map = {
                'rinvio': 'rinviato',
                'annullamento': 'annullato',
                'modifica_data': 'confermato',
                'modifica_ora': 'confermato'
            }

            prefix = prefix_map.get(modification_type, '[MODIFICATO]')

            # Aggiorna titolo se non ha già il prefisso
            if not evento.titolo.startswith('['):
                evento.titolo = f"{prefix} {evento.titolo}"

            # ===== FIX 1: Aggiorna lo STATO dell'evento =====
            nuovo_stato = stato_map.get(modification_type, 'confermato')
            evento.stato = nuovo_stato
            logger.info(f"📊 Stato evento aggiornato: {nuovo_stato}")

            # ===== FIX 2: Popola email_modifica_id per tracciabilità =====
            evento.email_modifica_id = email.id
            evento.note_modifica = f"Modifica ({modification_type}) da email ID {email.id}: {email.oggetto[:100]}"
            logger.info(f"🔗 Collegata email modifica ID {email.id} all'evento")

            # ===== FIX 3: Preserva data originale e aggiorna con nuova data =====
            if modification_type in ('rinvio', 'modifica_data') and new_date_info:
                # Salva la data originale se non già salvata
                if not evento.data_inizio_originale:
                    evento.data_inizio_originale = evento.data_inizio
                    logger.info(f"📅 Data originale preservata: {evento.data_inizio_originale}")

                # Aggiorna con la nuova data
                try:
                    from datetime import datetime as dt
                    nuova_data_str = f"{new_date_info['data']} {new_date_info['ora']}"
                    nuova_data = dt.strptime(nuova_data_str, "%Y-%m-%d %H:%M")

                    # Calcola nuova data_fine mantenendo la stessa durata
                    if evento.data_fine and evento.data_inizio:
                        durata = evento.data_fine - evento.data_inizio
                        evento.data_fine = nuova_data + durata

                    evento.data_inizio = nuova_data

                    # Aggiorna titolo per riflettere il cambio data
                    if modification_type == 'rinvio':
                        # Cambia prefisso da [RINVIATO] a [POST RINVIO] se abbiamo nuova data
                        evento.titolo = evento.titolo.replace('[RINVIATO]', '[POST RINVIO]')
                        evento.stato = 'confermato'  # Torna confermato con la nuova data

                    logger.info(f"📅 Data evento aggiornata: {evento.data_inizio} (originale: {evento.data_inizio_originale})")
                except Exception as e:
                    logger.warning(f"⚠️ Impossibile aggiornare data evento: {e}")

            # Aggiorna sintesi motivo
            if modification_type == 'rinvio':
                if new_date_info:
                    evento.sintesi_motivo = f"EVENTO RINVIATO al {new_date_info['data']} - {new_sintesi or 'Vedi email per dettagli'}"
                else:
                    evento.sintesi_motivo = f"EVENTO RINVIATO - {new_sintesi or 'Data da destinarsi'}"
            elif modification_type == 'annullamento':
                evento.sintesi_motivo = f"EVENTO ANNULLATO - {new_sintesi or 'Vedi email per dettagli'}"
            else:
                if new_sintesi:
                    evento.sintesi_motivo = new_sintesi

            # Aggiungi riferimento all'email di modifica nella descrizione
            desc_update = f"\n\n--- Aggiornamento del {datetime.now().strftime('%d/%m/%Y %H:%M')} ---\n"
            desc_update += f"Email ID: {email.id}\n"
            desc_update += f"Oggetto: {email.oggetto}\n"
            desc_update += f"Tipo modifica: {modification_type}\n"
            desc_update += f"Stato: {nuovo_stato}"
            if evento.data_inizio_originale:
                desc_update += f"\nData originale: {evento.data_inizio_originale.strftime('%d/%m/%Y %H:%M')}"
            if new_date_info:
                desc_update += f"\nNuova data: {new_date_info['data']} ore {new_date_info['ora']}"

            if evento.descrizione:
                evento.descrizione += desc_update
            else:
                evento.descrizione = desc_update

            self.db.commit()
            logger.info(f"✅ Evento {evento.id} aggiornato come {modification_type} (stato={nuovo_stato})")
            return True

        except Exception as e:
            logger.error(f"❌ Errore aggiornamento evento: {e}")
            self.db.rollback()
            return False

    def execute_actions_for_email(self, email_id: int) -> List[Azione]:
        """
        Esegue tutte le azioni necessarie per una email usando il RulesEngine.

        Args:
            email_id: ID dell'email

        Returns:
            List[Azione]: Lista azioni create
        """
        email = self.db.query(Email).filter(Email.id == email_id).first()

        if not email:
            logger.error(f"Email {email_id} non trovata")
            return []

        if not email.interpretazione:
            logger.warning(f"Email {email_id} non ha interpretazione, skip azioni")
            return []

        # Usa RulesEngine per determinare le azioni da eseguire
        from app.services.rules_engine import RulesEngine
        rules_engine = RulesEngine(self.db)

        logger.info(f"📋 Valuto regole per email {email_id} (categoria: {email.get_categoria_value()})")
        azioni = rules_engine.evaluate_rules_for_email(email)

        # Salva azioni nel database
        for azione in azioni:
            if azione:
                self.db.add(azione)

        self.db.commit()

        logger.info(f"✅ Create {len([a for a in azioni if a])} azioni da regole per email {email_id}")
        return [a for a in azioni if a]

    def _create_draft_response(self, email: Email) -> Optional[Azione]:
        """
        Crea una bozza di risposta usando LLM.

        Args:
            email: Email da cui generare risposta

        Returns:
            Azione: Azione creata
        """
        try:
            interpretazione_data = email.interpretazione.dati_estratti if email.interpretazione else {}

            # Genera risposta con LLM
            prompt = self._build_response_prompt(email, interpretazione_data)
            risposta = self.llm_client.generate(prompt, model_type="generation")

            # Crea azione
            azione = Azione(
                email_id=email.id,
                tipo_azione=TipoAzione.BOZZA_RISPOSTA,
                stato=StatoAzione.PENDING,
                parametri={
                    'to': email.mittente,
                    'subject': f"Re: {email.oggetto}",
                    'body': risposta,
                    'reply_to': email.message_id
                },
                eseguita_at=None
            )

            logger.info(f"✅ Bozza risposta creata per email {email.id}")
            return azione

        except Exception as e:
            logger.error(f"❌ Errore creazione bozza risposta: {e}")
            return None

    def _create_calendar_event(self, email: Email) -> Optional[Azione]:
        """
        Crea un evento calendario dai dati interpretati.

        Args:
            email: Email con dati evento

        Returns:
            Azione: Azione creata
        """
        try:
            if not email.interpretazione:
                return None

            dati = email.interpretazione.dati_estratti

            # Estrai info evento
            data_evento = dati.get('data_evento') or dati.get('data_convocazione')
            ora_evento = dati.get('ora_evento') or dati.get('ora_convocazione')
            luogo = dati.get('luogo') or dati.get('sede')
            descrizione = dati.get('descrizione') or email.corpo_testo[:500]

            if not data_evento:
                logger.warning(f"Nessuna data evento trovata per email {email.id}")
                return None

            # Crea azione
            azione = Azione(
                email_id=email.id,
                tipo_azione=TipoAzione.CREA_EVENTO_CALENDARIO,
                stato=StatoAzione.PENDING,
                parametri={
                    'summary': email.oggetto,
                    'date': data_evento,
                    'time': ora_evento,
                    'location': luogo,
                    'description': descrizione,
                    'attendees': [email.mittente]
                },
                eseguita_at=None
            )

            logger.info(f"✅ Evento calendario creato per email {email.id}")
            return azione

        except Exception as e:
            logger.error(f"❌ Errore creazione evento calendario: {e}")
            return None

    # Google Drive upload rimosso - non disponibile con account Gmail personale
    # def _upload_attachments_to_drive(self, email: Email) -> Optional[Azione]:
    #     """
    #     Carica allegati su Google Drive.
    #
    #     Args:
    #         email: Email con allegati
    #
    #     Returns:
    #         Azione: Azione creata
    #     """
    #     try:
    #         if not email.allegati:
    #             return None
    #
    #         # Crea azione (verrà eseguita dal task)
    #         azione = Azione(
    #             email_id=email.id,
    #             tipo_azione=TipoAzione.CARICA_SU_DRIVE,
    #             stato=StatoAzione.PENDING,
    #             parametri={
    #                 'attachments_count': len(email.allegati),
    #                 'email_subject': email.oggetto,
    #                 'email_date': email.data_ricezione.isoformat()
    #             },
    #             eseguita_at=None
    #         )
    #
    #         logger.info(f"✅ Azione upload Drive creata per email {email.id}")
    #         return azione
    #
    #     except Exception as e:
    #         logger.error(f"❌ Errore creazione azione Drive: {e}")
    #         return None

    def execute_action(self, azione_id: int) -> bool:
        """
        Esegue una singola azione.

        Args:
            azione_id: ID dell'azione

        Returns:
            bool: True se eseguita con successo
        """
        azione = self.db.query(Azione).filter(Azione.id == azione_id).first()

        if not azione:
            logger.error(f"Azione {azione_id} non trovata")
            return False

        if azione.stato == StatoAzione.COMPLETATA:
            logger.info(f"Azione {azione_id} già completata")
            return True

        try:
            azione.stato = StatoAzione.IN_ESECUZIONE
            self.db.commit()

            success = False

            # Esegui azione in base al tipo
            if azione.tipo == TipoAzione.BOZZA_RISPOSTA:
                success = self._execute_draft_response(azione)

            elif azione.tipo == TipoAzione.BOZZA_APPUNTAMENTO:
                success = self._execute_draft_appuntamento(azione)

            elif azione.tipo == TipoAzione.BOZZA_TESSERAMENTO:
                success = self._execute_draft_tesseramento(azione)

            elif azione.tipo == TipoAzione.EVENTO_CALENDARIO:
                success = self._execute_calendar_event(azione)

            # Google Drive upload disabilitato - non disponibile con account Gmail personale
            # elif azione.tipo == TipoAzione.UPLOAD_DRIVE:
            #     success = self._execute_drive_upload(azione)

            elif azione.tipo == TipoAzione.SEGNA_IMPORTANTE:
                success = self._execute_mark_important(azione)

            elif azione.tipo == TipoAzione.SINTESI:
                success = self._execute_sintesi(azione)

            elif azione.tipo == TipoAzione.INDICIZZA_RAG:
                success = self._execute_indicizza_rag(azione)

            elif azione.tipo == TipoAzione.PARSE_INTERPELLO:
                success = self._execute_parse_interpello(azione)

            elif azione.tipo == TipoAzione.INOLTRA or azione.tipo == TipoAzione.INOLTRA_EMAIL:
                success = self._execute_forward(azione)

            elif azione.tipo == TipoAzione.INOLTRA_DELEGATI_ZONA:
                success = self._execute_forward_delegati_zona(azione)

            elif azione.tipo == TipoAzione.INVIA_NOTIFICA or azione.tipo == TipoAzione.NOTIFICA:
                success = self._execute_notify(azione)

            else:
                logger.warning(f"Tipo azione {azione.tipo.value} non implementato")
                success = False

            if success:
                azione.stato = StatoAzione.COMPLETATA
                azione.eseguita_at = datetime.now()
                azione.errore = None
            else:
                azione.stato = StatoAzione.FALLITA
                azione.errore = "Esecuzione fallita"

            self.db.commit()
            return success

        except Exception as e:
            logger.error(f"❌ Errore esecuzione azione {azione_id}: {e}")
            azione.stato = StatoAzione.FALLITA
            azione.errore = str(e)
            self.db.commit()
            return False

    def _execute_draft_response(self, azione: Azione) -> bool:
        """
        Schedula generazione bozza risposta intelligente in background.

        La bozza viene generata usando RAG per arricchire il contesto,
        con timeout lunghi tramite Celery worker.
        """
        try:
            email = self.db.query(Email).filter(Email.id == azione.email_id).first()
            if not email:
                logger.error(f"Email {azione.email_id} non trovata")
                return False

            logger.info(f"📝 Scheduling generazione draft intelligente per email {azione.email_id}")

            # Importa task Celery
            from app.tasks.draft_tasks import generate_smart_draft

            # Schedula generazione draft in background
            task = generate_smart_draft.delay(
                email_id=azione.email_id,
                azione_id=azione.id
            )

            # Mantieni azione in coda - verrà completata dal task
            azione.stato = StatoAzione.IN_CODA
            azione.risultato = {
                'status': 'scheduled',
                'task_id': task.id,
                'message': 'Generazione draft schedulata con RAG context (timeout 3 min)'
            }
            self.db.commit()

            logger.info(
                f"✅ Draft schedulata per email {azione.email_id} "
                f"(Task ID: {task.id}). Verrà generata dal worker."
            )

            return True

        except Exception as e:
            logger.error(f"Errore scheduling draft: {e}", exc_info=True)
            azione.risultato = {'error': f'Errore scheduling: {str(e)}'}
            return False

    def _execute_calendar_event(self, azione: Azione) -> bool:
        """Esegue creazione evento calendario."""
        try:
            email = self.db.query(Email).filter(Email.id == azione.email_id).first()
            if not email:
                return False

            params = azione.dettagli.get('parametri', {})
            logger.info(f"📅 Creazione evento calendario per email {azione.email_id}")

            # Verifica autenticazione Google Calendar (ma non blocca se fallisce)
            google_calendar_disponibile = self.calendar_client.authenticate()
            if not google_calendar_disponibile:
                logger.warning("⚠️ Google Calendar non configurato - evento verrà salvato solo localmente")

            # Estrai dati evento dall'email con UnifiedExtractor
            event_data = None
            if params.get('analizza_documento'):
                try:
                    # Usa UnifiedExtractor (pipeline: Regex → NLP → LLM → ChatGPT)
                    logger.info("📊 Estrazione dati convocazione con UnifiedExtractor")

                    # Prepara testo completo (OGGETTO + corpo + allegati se presenti)
                    # IMPORTANTE: Include oggetto perché spesso contiene data/ora (es: "Venerdì 28.11.2025")
                    testo_completo = f"OGGETTO: {email.oggetto}\n\n"
                    testo_completo += email.corpo_testo or ""
                    if email.allegati_testo:
                        try:
                            import json as json_lib
                            allegati = json_lib.loads(email.allegati_testo) if isinstance(email.allegati_testo, str) else email.allegati_testo
                            if allegati:
                                testi_allegati = [f"{nome}: {testo}" for nome, testo in allegati.items() if testo]
                                testo_completo += "\n\n" + "\n\n".join(testi_allegati)
                        except:
                            pass

                    # Estrai con UnifiedExtractor (tipo="calendario")
                    dati_estratti = self.unified_extractor.extract(
                        testo=testo_completo[:5000],  # Limita lunghezza
                        tipo="calendario"
                    )

                    if dati_estratti:
                        # Mappa campi estratti al formato event_data
                        # UnifiedExtractor usa: data_inizio, ora_inizio, luogo, scuola_nome, tipo_riunione, motivo
                        event_data = {
                            'titolo': email.oggetto,  # Usa oggetto email come titolo
                            'data_inizio': dati_estratti.get('data_inizio'),
                            'ora_inizio': dati_estratti.get('ora_inizio'),
                            'luogo': dati_estratti.get('luogo') or dati_estratti.get('scuola_nome'),
                            'sede': dati_estratti.get('scuola_nome'),
                            'descrizione': dati_estratti.get('motivo') or dati_estratti.get('tipo_riunione') or f"Convocazione da {email.mittente}",
                            'convocante': email.mittente,
                            'modalita': dati_estratti.get('modalita'),
                            'tipo_riunione': dati_estratti.get('tipo_riunione')
                        }

                        # INFERENZA SEDE PER CONVOCAZIONI SCUOLE
                        # Se convocazione da scuola senza sede esplicita → inferisci sede = scuola mittente
                        if email.categoria and 'convocazione' in str(email.categoria).lower():
                            # Controlla se mittente è una scuola (codice meccanografico @istruzione.it)
                            import re
                            if email.mittente and '@istruzione.it' in email.mittente.lower():
                                codice_mecc_match = re.search(r'([a-z]{4}\d{5,}[a-z]?)@istruzione\.it', email.mittente.lower())
                                if codice_mecc_match:
                                    codice_mecc = codice_mecc_match.group(1).upper()

                                    # Se sede non specificata o è solo indirizzo generico (senza nome scuola), inferisci
                                    sede_attuale = event_data.get('sede', '') or event_data.get('luogo', '')

                                    # Condizioni per inferire la scuola:
                                    # 1. Nessuna sede specificata
                                    # 2. Sede è "Ai Rappresentanti" o simile (destinatari)
                                    # 3. Sede troppo corta (< 10 caratteri)
                                    # 4. Sede è solo indirizzo generico (via/viale/piazza) senza nome istituto
                                    sede_e_solo_indirizzo = (
                                        sede_attuale and
                                        any(sede_attuale.lower().startswith(prefix) for prefix in ['via ', 'viale ', 'piazza ', 'corso ', 'vicolo ']) and
                                        not any(keyword in sede_attuale.lower() for keyword in ['istituto', 'scuola', 'liceo', 'i.c.', 'ic ', 'i.i.s', 'ips', 'itt'])
                                    )

                                    if not sede_attuale or 'Ai Rappresentanti' in str(sede_attuale) or len(sede_attuale) < 10 or sede_e_solo_indirizzo:
                                        # Usa SchoolIdentifier per ottenere informazioni scuola
                                        from app.services.school_identifier import get_school_identifier
                                        school_identifier = get_school_identifier()
                                        school_info = school_identifier.get_school_info(codice_mecc)

                                        if school_info:
                                            # Formatta nome scuola con comune
                                            label = school_identifier.format_school_label(school_info, include_comune=True)
                                            indirizzo = school_info.get('indirizzo', '')

                                            # Usa nome scuola + indirizzo completo
                                            event_data['scuola'] = label
                                            event_data['sede'] = f"{label} - {indirizzo}" if indirizzo else label
                                            event_data['luogo'] = indirizzo if indirizzo else label

                                            logger.info(f"📍 Sede inferita da SchoolIdentifier: {label}")
                                        else:
                                            # Fallback: usa codice meccanografico
                                            event_data['sede'] = f"Istituto {codice_mecc}"
                                            event_data['scuola'] = f"Istituto {codice_mecc}"
                                            logger.info(f"📍 Sede inferita (fallback): Istituto {codice_mecc}")

                        # Log metadata estrazione da UnifiedExtractor
                        if '_pipeline_steps' in dati_estratti:
                            steps = [s['step'] for s in dati_estratti['_pipeline_steps'] if s.get('success')]
                            completeness = dati_estratti.get('_completeness', 0)
                            confidence = dati_estratti.get('_overall_confidence', 0)
                            logger.info(
                                f"📊 Dati estratti con pipeline: {' → '.join(steps)} "
                                f"(completezza: {completeness:.0%}, confidence: {confidence:.2f})"
                            )

                        logger.info(f"✅ Dati convocazione estratti: {list(event_data.keys())}")

                        # ===== SOGLIA MINIMA CREAZIONE EVENTI =====
                        # Non creare evento se:
                        # 1. Sanity check fallito (date/ore garbage)
                        # 2. Completezza < 40% (dati insufficienti)
                        # 3. Data inizio mancante
                        sanity_passed = dati_estratti.get('_sanity_passed', True)
                        completeness = dati_estratti.get('_completeness', 0)
                        sanity_issues = dati_estratti.get('_sanity_issues', [])
                        MIN_COMPLETENESS_THRESHOLD = 0.40  # 40%

                        if not sanity_passed:
                            logger.warning(f"⚠️ Sanity check fallito: {sanity_issues}")
                            azione.risultato = {
                                'status': 'manual_intervention_required',
                                'error': f'Sanity check fallito: {", ".join(sanity_issues)}',
                                'email_subject': email.oggetto,
                                'message': f'⚠️ INTERVENTO UMANO RICHIESTO: Dati estratti non validi ({", ".join(sanity_issues)}). Verifica e crea evento manualmente.'
                            }
                            return False

                        if completeness < MIN_COMPLETENESS_THRESHOLD:
                            logger.warning(f"⚠️ Completezza sotto soglia: {completeness:.0%} < {MIN_COMPLETENESS_THRESHOLD:.0%}")
                            azione.risultato = {
                                'status': 'manual_intervention_required',
                                'error': f'Completezza dati insufficiente: {completeness:.0%}',
                                'email_subject': email.oggetto,
                                'extracted_data': {k: v for k, v in event_data.items() if v},
                                'message': f'⚠️ INTERVENTO UMANO RICHIESTO: Dati estratti incompleti ({completeness:.0%}). Verifica e completa manualmente.'
                            }
                            return False

                        if not event_data.get('data_inizio'):
                            logger.warning("⚠️ Data inizio mancante")
                            azione.risultato = {
                                'status': 'manual_intervention_required',
                                'error': 'Data evento mancante',
                                'email_subject': email.oggetto,
                                'extracted_data': {k: v for k, v in event_data.items() if v},
                                'message': '⚠️ INTERVENTO UMANO RICHIESTO: Data evento non trovata. Verifica email e inserisci manualmente.'
                            }
                            return False

                        logger.info(f"✅ Soglia minima superata (completezza: {completeness:.0%}, sanity: OK)")
                    else:
                        # UnifiedExtractor non ha estratto dati sufficienti
                        logger.warning("⚠️ UnifiedExtractor non ha estratto dati sufficienti")

                except Exception as e:
                    logger.error(f"❌ Errore estrazione dati con LLM: {e}")
                    azione.risultato = {
                        'status': 'manual_intervention_required',
                        'error': str(e),
                        'email_subject': email.oggetto,
                        'message': f'⚠️ INTERVENTO UMANO RICHIESTO: Errore analisi convocazione ({str(e)}). Crea l\'evento manualmente.'
                    }
                    return False

            # Se non c'è analisi LLM, devono esserci parametri manuali
            elif params.get('summary') and params.get('date') and params.get('time'):
                # Usa dati inseriti manualmente dall'utente
                event_data = {
                    'titolo': params.get('summary'),
                    'data_inizio': params.get('date'),
                    'ora_inizio': params.get('time'),
                    'descrizione': params.get('description', f"Convocazione da {email.mittente}"),
                    'luogo': params.get('location', '')
                }
                logger.info(f"📅 Usando dati inseriti manualmente")
            else:
                # Nessun dato disponibile - richiedi intervento manuale
                logger.error("❌ Nessun dato disponibile per creare evento")
                azione.risultato = {
                    'status': 'manual_intervention_required',
                    'error': 'Dati evento mancanti',
                    'email_subject': email.oggetto,
                    'message': '⚠️ INTERVENTO UMANO RICHIESTO: Specifica data, ora e titolo per creare l\'evento calendario.'
                }
                return False

            # ===== CHECK RINVIO/ANNULLAMENTO =====
            # Prima di creare un evento, verifica se è una modifica di uno esistente
            allegati_text = ""
            if email.allegati_testo:
                try:
                    import json as json_lib
                    allegati = json_lib.loads(email.allegati_testo) if isinstance(email.allegati_testo, str) else email.allegati_testo
                    if allegati and isinstance(allegati, dict):
                        allegati_text = " ".join([str(v) for v in allegati.values() if v])
                except:
                    allegati_text = str(email.allegati_testo) if email.allegati_testo else ""

            modification_info = self._detect_event_modification(
                oggetto=email.oggetto,
                corpo=email.corpo_testo,
                allegati_testo=allegati_text
            )

            if modification_info['is_modification']:
                logger.info(f"🔄 Email {email.id} contiene una MODIFICA evento ({modification_info['modification_type']})")

                # Prova a trovare l'evento esistente da modificare
                data_inizio_temp = None
                if event_data and event_data.get('data_inizio'):
                    try:
                        from datetime import datetime as dt
                        import re
                        data_str = event_data['data_inizio']
                        ora_str = event_data.get('ora_inizio') or '09:00'
                        # Normalizza ora
                        ora_str = ora_str.lower().strip()
                        ora_str = re.sub(r'^(ore|alle|h\.?|at)\s*', '', ora_str)
                        ora_str = ora_str.replace('.', ':').replace(',', ':')
                        match = re.search(r'(\d{1,2}):(\d{2})', ora_str)
                        if match:
                            ora_str = f"{int(match.group(1)):02d}:{match.group(2)}"
                        else:
                            match = re.search(r'(\d{1,2})', ora_str)
                            ora_str = f"{int(match.group(1)):02d}:00" if match else '09:00'
                        data_inizio_temp = dt.strptime(f"{data_str} {ora_str}", "%Y-%m-%d %H:%M")
                    except:
                        pass

                evento_esistente = self._find_existing_event(email, event_data or {}, data_inizio_temp)

                if evento_esistente:
                    # Aggiorna l'evento esistente invece di crearne uno nuovo
                    logger.info(f"📝 Aggiornamento evento esistente ID {evento_esistente.id}")

                    # Estrae eventuale nuova data dall'email
                    new_date_info = self._extract_new_date_from_email(
                        oggetto=email.oggetto,
                        corpo=email.corpo_testo
                    )
                    if new_date_info:
                        logger.info(f"📅 Trovata nuova data nell'email: {new_date_info['data']} ore {new_date_info['ora']}")

                    success = self._update_existing_event(
                        evento=evento_esistente,
                        modification_type=modification_info['modification_type'],
                        email=email,
                        new_sintesi=f"Riferimento email: {email.oggetto[:100]}",
                        new_date_info=new_date_info
                    )

                    if success:
                        result_msg = f"Evento esistente aggiornato come {modification_info['modification_type']}"
                        if new_date_info:
                            result_msg += f" - Nuova data: {new_date_info['data']}"

                        azione.risultato = {
                            'status': 'event_updated',
                            'evento_id': evento_esistente.id,
                            'modification_type': modification_info['modification_type'],
                            'keywords_found': modification_info['keywords_found'],
                            'new_date': new_date_info,
                            'message': result_msg
                        }
                        return True
                    else:
                        # Se l'aggiornamento fallisce, continua a creare nuovo evento ma con prefisso
                        logger.warning(f"⚠️ Aggiornamento evento fallito, creo nuovo evento con prefisso")
                        if event_data:
                            prefix = '[RINVIATO]' if modification_info['modification_type'] == 'rinvio' else '[ANNULLATO]'
                            event_data['titolo'] = f"{prefix} {event_data.get('titolo', email.oggetto)}"
                else:
                    # Nessun evento esistente trovato, crea nuovo con prefisso appropriato
                    logger.info(f"📝 Nessun evento esistente trovato, creo nuovo con prefisso")
                    if event_data:
                        prefix = '[RINVIATO]' if modification_info['modification_type'] == 'rinvio' else '[ANNULLATO]'
                        event_data['titolo'] = f"{prefix} {event_data.get('titolo', email.oggetto)}"

            # Crea evento nel database locale SEMPRE se abbiamo almeno la data
            if event_data and event_data.get('data_inizio'):
                # Combina data e ora in datetime
                from datetime import datetime as dt
                import re
                try:
                    # Parsing flessibile della data
                    data_str = str(event_data['data_inizio']).strip()

                    # Normalizza data (gestisce vari formati)
                    # 0. Formato italiano testuale: "04 dicembre 2025" -> YYYY-MM-DD
                    mesi_italiani = {
                        'gennaio': '01', 'febbraio': '02', 'marzo': '03', 'aprile': '04',
                        'maggio': '05', 'giugno': '06', 'luglio': '07', 'agosto': '08',
                        'settembre': '09', 'ottobre': '10', 'novembre': '11', 'dicembre': '12'
                    }
                    for mese, num in mesi_italiani.items():
                        if mese in data_str.lower():
                            # Trova giorno e anno
                            match_it = re.search(r'(\d{1,2})\s+' + mese + r'\s+(\d{4})', data_str.lower())
                            if match_it:
                                giorno = match_it.group(1).zfill(2)
                                anno = match_it.group(2)
                                data_str = f"{anno}-{num}-{giorno}"
                                break

                    # 1. ISO format con T: "2025-11-28T11:00:00Z" -> estrai solo data
                    if 'T' in data_str:
                        data_str = data_str.split('T')[0]
                    # 2. Formato italiano DD/MM/YYYY -> YYYY-MM-DD
                    if '/' in data_str:
                        parts = data_str.split('/')
                        if len(parts) == 3 and len(parts[2]) == 4:
                            data_str = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
                    # 2b. Formato DD.MM.YYYY -> YYYY-MM-DD (con punto come separatore)
                    elif '.' in data_str and not data_str.startswith('20'):
                        # Rimuovi eventuale ora: "26.11.2025 10:00" -> "26.11.2025"
                        data_only = data_str.split()[0] if ' ' in data_str else data_str
                        parts = data_only.split('.')
                        if len(parts) == 3 and len(parts[2]) == 4:
                            data_str = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
                    # 3. Formato DD-MM-YYYY -> YYYY-MM-DD (diverso da ISO YYYY-MM-DD)
                    elif '-' in data_str:
                        parts = data_str.split('-')
                        # Se primo elemento è 2 cifre e ultimo è 4 cifre -> DD-MM-YYYY
                        if len(parts) == 3 and len(parts[0]) <= 2 and len(parts[2]) == 4:
                            data_str = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"

                    ora_str = event_data.get('ora_inizio') or '09:00'  # Default 09:00 se manca

                    # Normalizza formato ora (gestisce vari formati italiani)
                    ora_str = str(ora_str).lower().strip()
                    # Rimuovi prefissi comuni
                    ora_str = re.sub(r'^(ore|alle|h\.?|at)\s*', '', ora_str)
                    # Sostituisci separatori non standard
                    ora_str = ora_str.replace('.', ':').replace(',', ':')
                    # Estrai solo HH:MM
                    match = re.search(r'(\d{1,2}):(\d{2})', ora_str)
                    if match:
                        ora_str = f"{int(match.group(1)):02d}:{match.group(2)}"
                    else:
                        # Prova solo ore (es: "9")
                        match = re.search(r'(\d{1,2})', ora_str)
                        if match:
                            ora_str = f"{int(match.group(1)):02d}:00"
                        else:
                            ora_str = '09:00'  # Fallback

                    data_inizio_dt = dt.strptime(f"{data_str} {ora_str}", "%Y-%m-%d %H:%M")
                    logger.info(f"📅 Data/ora evento: {data_inizio_dt} (ora={'estratta' if event_data.get('ora_inizio') else 'default 09:00'})")

                    # Calcola data fine (default: +1 ora se non specificata, altrimenti usa durata estratta)
                    durata_ore = event_data.get('durata_ore', 1)  # Default 1h instead of 2h
                    from datetime import timedelta
                    data_fine_dt = data_inizio_dt + timedelta(hours=durata_ore)

                except Exception as e:
                    logger.error(f"❌ Errore parsing data/ora: {e} (data={event_data.get('data_inizio')}, ora={event_data.get('ora_inizio')})")
                    azione.risultato = {
                        'status': 'manual_intervention_required',
                        'error': f'Formato data/ora non valido: {str(e)}',
                        'extracted_data': event_data,
                        'message': '⚠️ INTERVENTO UMANO RICHIESTO: Formato data/ora estratto non valido.'
                    }
                    return False

                # Genera sintesi motivo convocazione
                # PRIORITÀ: Usa dati già estratti, poi LLM come fallback
                sintesi_motivo = None

                # 1. Prima prova con dati già estratti (più affidabile)
                if event_data.get('oggetto_riunione'):
                    sintesi_motivo = event_data['oggetto_riunione']
                    logger.info(f"📝 Sintesi motivo da dati estratti: {sintesi_motivo[:100]}...")
                elif event_data.get('motivo'):
                    sintesi_motivo = event_data['motivo']
                    logger.info(f"📝 Sintesi motivo da campo motivo: {sintesi_motivo[:100]}...")
                else:
                    # 2. Fallback: genera con LLM (con validazione anti-allucinazione)
                    try:
                        testo_completo = ""
                        if email.corpo_testo:
                            testo_completo += email.corpo_testo[:2000]
                        if email.allegati_testo and isinstance(email.allegati_testo, dict):
                            for filename, testo in email.allegati_testo.items():
                                if testo:
                                    testo_completo += f"\n\n{testo[:1500]}"

                        if testo_completo:
                            prompt_sintesi = f"""Qual è l'argomento di questa convocazione? Rispondi con MAX 10 PAROLE.

ESEMPI:
- "Contrattazione integrativa d'istituto a.s. 2025/2026"
- "Riunione RSU per firma contratto integrativo"
- "Tavolo contrattuale relazioni sindacali"
- "Informativa risorse FIS e avvio trattative"

TESTO:
{testo_completo[:1500]}

ARGOMENTO (max 10 parole):"""

                            sintesi_motivo = self.llm_client.generate(prompt_sintesi, model_type="generation")

                            if sintesi_motivo:
                                # Pulisci e limita a 80 caratteri
                                sintesi_motivo = sintesi_motivo.strip().strip('"').strip()[:80]

                                # Validazione anti-allucinazione
                                frasi_sospette = [
                                    "non ho trovato", "non è chiaro", "sembra essere",
                                    "potrebbe essere", "non sono sicuro", "errore",
                                    "autografa omessa", "d.lgs", "ai sensi", "la convocazione"
                                ]
                                if any(frase in sintesi_motivo.lower() for frase in frasi_sospette):
                                    logger.warning(f"⚠️ Sintesi sospetta, uso fallback: {sintesi_motivo}")
                                    sintesi_motivo = None
                                else:
                                    logger.info(f"📝 Sintesi motivo: {sintesi_motivo}")
                    except Exception as e:
                        logger.warning(f"⚠️ Errore generazione sintesi motivo: {e}")

                # 3. Fallback finale: usa oggetto email
                if not sintesi_motivo:
                    sintesi_motivo = email.oggetto[:200] if email.oggetto else "Convocazione"
                    logger.info(f"📝 Sintesi motivo fallback (oggetto): {sintesi_motivo[:100]}...")

                # GARANTISCI SCUOLA E LUOGO CORRETTI
                # Estrae sempre codice scuola dal mittente e usa database per indirizzo
                event_data = self._ensure_scuola_and_luogo(event_data, email)

                # Crea evento nel database locale
                evento_locale = EventoCalendario(
                    email_id=azione.email_id,
                    titolo=event_data.get('titolo', email.oggetto),
                    descrizione=event_data.get('descrizione', email.corpo_testo[:500] if email.corpo_testo else None),
                    data_inizio=data_inizio_dt,
                    data_fine=data_fine_dt,
                    luogo=self._normalize_luogo(event_data.get('luogo') or event_data.get('sede')),
                    scuola=event_data.get('scuola'),
                    tipo_convocazione=event_data.get('tipo_convocazione'),
                    link_videocall=event_data.get('link_videocall'),
                    sintesi_motivo=sintesi_motivo,
                    sincronizzato=False
                )

                self.db.add(evento_locale)
                self.db.commit()
                self.db.refresh(evento_locale)

                logger.info(f"✅ Evento salvato nel database locale (ID: {evento_locale.id})")

                # Prova a sincronizzare con Google Calendar se disponibile
                # Usa il nuovo metodo sync_db_event_to_google che gestisce timezone correttamente
                google_event_id = None
                if google_calendar_disponibile:
                    try:
                        # Refresh l'oggetto per avere i dati più recenti
                        self.db.refresh(evento_locale)

                        # Usa sync_db_event_to_google che gestisce timezone Europe/Rome
                        google_event_id = self.calendar_client.sync_db_event_to_google(
                            evento_locale,
                            calendar_id=settings.GOOGLE_CALENDAR_ID
                        )

                        if google_event_id:
                            # Aggiorna evento locale con ID Google
                            evento_locale.google_event_id = google_event_id
                            evento_locale.sincronizzato = True
                            self.db.commit()
                            logger.info(f"✅ Evento sincronizzato con Google Calendar (ID: {google_event_id})")
                        else:
                            logger.warning("⚠️ Google Calendar non ha ritornato event_id")
                    except Exception as e:
                        import traceback
                        logger.warning(f"⚠️ Errore sincronizzazione Google Calendar: {e}")
                        logger.error(f"Traceback completo:\n{traceback.format_exc()}")

                # Risultato azione
                azione.risultato = {
                    'status': 'event_created',
                    'evento_id': evento_locale.id,
                    'google_event_id': google_event_id,
                    'sincronizzato_google': google_event_id is not None,
                    'event_data': event_data
                }
                logger.info(f"✅ Evento calendario creato (locale ID: {evento_locale.id}, Google ID: {google_event_id or 'N/A'})")
                return True

            logger.error("❌ Dati evento insufficienti")
            azione.risultato = {
                'status': 'manual_intervention_required',
                'error': 'Dati evento insufficienti',
                'message': '⚠️ INTERVENTO UMANO RICHIESTO: Impossibile creare evento senza data e ora.'
            }
            return False

        except Exception as e:
            logger.error(f"Errore creazione evento calendario: {e}")
            azione.risultato = {'error': str(e)}
            return False

    # Google Drive upload rimosso - non disponibile con account Gmail personale
    # def _execute_drive_upload(self, azione: Azione) -> bool:
    #     """Esegue upload allegati su Drive."""
    #     pass  # Metodo disabilitato

    def _build_response_prompt(self, email: Email, interpretazione: Dict) -> str:
        """Costruisce prompt per generare risposta."""

        prompt = f"""Sei un assistente di una sede sindacale SNALS.

Genera una risposta professionale e cortese per la seguente email:

**Da:** {email.mittente}
**Oggetto:** {email.oggetto}
**Corpo:**
{email.corpo_testo[:1000]}

**Categoria email:** {email.get_categoria_value()}

**Informazioni estratte:**
{interpretazione}

**Istruzioni:**
1. Rispondi in modo professionale e cortese
2. Fai riferimento alle informazioni specifiche nell'email
3. Se è una richiesta appuntamento, conferma disponibilità e chiedi eventuali preferenze
4. Se è richiesta tesseramento, fornisci info su documenti necessari e procedura
5. Firma come "Segreteria SNALS"
6. Usa formato HTML con paragrafi ben formattati

Genera solo la risposta, senza soggetto.
"""
        return prompt

    def _execute_draft_appuntamento(self, azione: Azione) -> bool:
        """Esegue creazione bozza per appuntamento con link prenotazione."""
        try:
            email = self.db.query(Email).filter(Email.id == azione.email_id).first()
            if not email:
                return False

            logger.info(f"Creazione bozza appuntamento per email {azione.email_id}")

            # Genera bozza con SmartResponseGenerator
            prompt = f"""Genera una risposta per una richiesta di appuntamento.

Email originale:
Da: {email.mittente}
Oggetto: {email.oggetto}
Corpo: {email.corpo_testo[:500]}

Rispondi in modo professionale ringraziando per la richiesta e fornendo:
1. Conferma ricezione della richiesta
2. Link alla piattaforma di prenotazione: https://calendario.snals-taranto.it/prenota
3. Istruzioni per prenotare l'appuntamento
4. Disponibilità orari (lunedì-venerdì 9:00-13:00, 15:00-18:00)

Firma come "Segreteria SNALS Taranto"
Formato HTML ben strutturato."""

            if self.smart_generator:
                result = self.smart_generator.generate(
                    prompt=prompt,
                    task_type=TaskType.RISPOSTA_STANDARD,
                    max_tokens=500,
                    use_cache=False
                )
                bozza_corpo = result.get('risposta')
                logger.info(f"📊 Bozza generata con: {result['metadata'].get('strategy_final')}")
            else:
                bozza_corpo = self.llm_client.generate(
                    prompt=prompt,
                    model_type="generation",
                    max_tokens=500
                )

            # Salva bozza su webmail
            webmail = WebmailClient(email.account_type.value)
            success = webmail.save_draft(
                to=email.mittente,
                subject=f"Re: {email.oggetto}",
                body=bozza_corpo,
                reply_to=email.message_id
            )

            if success:
                azione.risultato = {
                    'status': 'draft_created',
                    'location': 'webmail_drafts',
                    'preview': bozza_corpo[:200]
                }
                logger.info(f"✅ Bozza appuntamento creata per email {azione.email_id}")
                return True

            return False

        except Exception as e:
            logger.error(f"Errore bozza appuntamento: {e}")
            azione.risultato = {'error': str(e)}
            return False

    def _execute_draft_tesseramento(self, azione: Azione) -> bool:
        """Esegue creazione bozza tesseramento con allegati."""
        try:
            email = self.db.query(Email).filter(Email.id == azione.email_id).first()
            if not email:
                return False

            logger.info(f"Creazione bozza tesseramento per email {azione.email_id}")

            # Genera bozza con SmartResponseGenerator
            prompt = f"""Genera una risposta per una richiesta di tesseramento SNALS.

Email originale:
Da: {email.mittente}
Oggetto: {email.oggetto}
Corpo: {email.corpo_testo[:500]}

Rispondi in modo professionale fornendo:
1. Conferma ricezione della richiesta
2. Informazioni sui documenti necessari (fotocopia documento identità, codice fiscale)
3. Indica che i moduli sono allegati alla email
4. Modalità di invio documentazione (email o consegna cartacea)
5. Contatti per assistenza (tel. 099-1234567)

Firma come "Ufficio Tesseramenti SNALS Taranto"
Formato HTML ben strutturato."""

            if self.smart_generator:
                result = self.smart_generator.generate(
                    prompt=prompt,
                    task_type=TaskType.RISPOSTA_STANDARD,
                    max_tokens=600,
                    use_cache=False
                )
                bozza_corpo = result.get('risposta')
                logger.info(f"📊 Bozza tesseramento generata con: {result['metadata'].get('strategy_final')}")
            else:
                bozza_corpo = self.llm_client.generate(
                    prompt=prompt,
                    model_type="generation",
                    max_tokens=600
                )

            # Salva bozza su webmail con allegati moduli tesseramento
            webmail = WebmailClient(email.account_type.value)

            # Path allegati moduli (da configurare nel repository)
            allegati_paths = [
                "/app/storage/moduli_tesseramento/modulo_iscrizione.pdf",
                "/app/storage/moduli_tesseramento/informativa_privacy.pdf"
            ]

            success = webmail.save_draft(
                to=email.mittente,
                subject=f"Re: {email.oggetto}",
                body=bozza_corpo,
                reply_to=email.message_id,
                attachments=allegati_paths
            )

            if success:
                azione.risultato = {
                    'status': 'draft_created',
                    'location': 'webmail_drafts',
                    'attachments': len(allegati_paths),
                    'preview': bozza_corpo[:200]
                }
                logger.info(f"✅ Bozza tesseramento creata con {len(allegati_paths)} allegati")
                return True

            return False

        except Exception as e:
            logger.error(f"Errore bozza tesseramento: {e}")
            azione.risultato = {'error': str(e)}
            return False

    def _execute_mark_important(self, azione: Azione) -> bool:
        """Segna email come importante."""
        try:
            email = self.db.query(Email).filter(Email.id == azione.email_id).first()
            if not email:
                return False

            logger.info(f"Segna email {azione.email_id} come importante")
            # TODO: Implementare flag importante sul sistema email
            azione.risultato = {
                'status': 'marked_important',
                'email_id': email.id
            }
            return True
        except Exception as e:
            logger.error(f"Errore segna importante: {e}")
            return False

    def _execute_sintesi(self, azione: Azione) -> bool:
        """Genera sintesi email."""
        try:
            email = self.db.query(Email).filter(Email.id == azione.email_id).first()
            if not email:
                return False

            params = azione.dettagli.get('parametri', {})
            tipo_sintesi = params.get('tipo_sintesi', 'standard')
            logger.info(f"Generazione sintesi {tipo_sintesi} per email {azione.email_id}")

            # Estrai contenuto email (gestisce corpo_testo None)
            corpo = email.corpo_testo[:2000] if email.corpo_testo else ""

            # Se il corpo è vuoto, usa il testo degli allegati
            if not corpo and email.allegati_testo:
                try:
                    import json
                    allegati = json.loads(email.allegati_testo) if isinstance(email.allegati_testo, str) else email.allegati_testo
                    if allegati:
                        testi_allegati = [f"{nome}: {testo[:500]}" for nome, testo in allegati.items() if testo]
                        corpo = "\n\n".join(testi_allegati)[:2000]
                except:
                    corpo = str(email.allegati_testo)[:2000] if email.allegati_testo else ""

            # Se ancora vuoto, genera sintesi semplice senza LLM
            if not corpo:
                # Sintesi fallback basata solo su oggetto
                sintesi = f"Email da {email.mittente} ricevuta il {email.data_ricezione.strftime('%d/%m/%Y %H:%M') if email.data_ricezione else 'data sconosciuta'}. Oggetto: {email.oggetto}. L'email non contiene corpo testuale leggibile."
                logger.info(f"✅ Sintesi fallback generata per email {azione.email_id} (senza contenuto)")
            else:
                # Genera sintesi con SmartResponseGenerator (se disponibile)
                # Prompt telegrafico: stile essenziale, max 1-2 frasi
                prompt = f"""Scrivi una SINTESI TELEGRAFICA di max 15-20 parole.

Oggetto: {email.oggetto}

Testo:
{corpo}

REGOLE TASSATIVE:
- MAX 15-20 parole, stile telegrafico
- NON scrivere "L'email contiene/invia/comunica"
- NON usare preamboli o frasi introduttive
- Usa sostantivi e verbi essenziali: "Convocazione riunione X il Y", "Nomina supplente per Z"
- Date e scadenze sempre in formato GG/MM
- NO disclaimer, NO firme, NO formalità

SINTESI:"""

                if self.smart_generator:
                    # Usa SmartResponseGenerator (con cascata locale → OpenAI)
                    result = self.smart_generator.generate(
                        prompt=prompt,
                        task_type=TaskType.SINTESI,
                        max_tokens=200,  # Ridotto per risparmiare token
                        use_cache=True
                    )
                    sintesi = result.get('risposta')

                    if sintesi:
                        logger.info(
                            f"✅ Sintesi generata con strategia: {result['metadata'].get('strategy_final')} "
                            f"(tempo: {result['metadata'].get('total_time_ms', 0):.0f}ms)"
                        )
                    else:
                        # Fallback a LLM diretto
                        sintesi = self.llm_client.generate(
                            prompt=prompt,
                            model_type="generation",
                            max_tokens=200
                        )
                else:
                    # Fallback a LLM locale diretto
                    sintesi = self.llm_client.generate(
                        prompt=prompt,
                        model_type="generation",
                        max_tokens=200
                    )

                # Post-elaborazione: rimuovi testo indesiderato
                if sintesi:
                    sintesi = self._clean_sintesi(sintesi)
                    # Sostituisci codici meccanografici con nomi scuole
                    sintesi = self._replace_school_codes(sintesi)

            # Salva sintesi nel campo note dell'email
            email.note = sintesi
            self.db.commit()

            azione.risultato = {
                'status': 'sintesi_generata',
                'tipo_sintesi': tipo_sintesi,
                'sintesi': sintesi,
                'length': len(sintesi)
            }
            logger.info(f"✅ Sintesi generata per email {azione.email_id}")
            return True

        except Exception as e:
            logger.error(f"Errore generazione sintesi: {e}")
            azione.risultato = {'error': str(e)}
            return False

    def _execute_indicizza_rag(self, azione: Azione) -> bool:
        """Indicizza documenti email nel RAG."""
        try:
            email = self.db.query(Email).filter(Email.id == azione.email_id).first()
            if not email:
                return False

            logger.info(f"📚 Indicizzazione RAG per email {azione.email_id}")

            # Importa RAG service
            from app.services.rag_service import get_rag_service
            rag_service = get_rag_service()

            # Indicizza email
            result = rag_service.index_email(email, self.db)

            if result['indexed']:
                azione.risultato = {
                    'status': 'indexed',
                    'documents_indexed': result['documents_indexed'],
                    'total_documents': result['total_documents'],
                    'errors': result.get('errors', [])
                }
                logger.info(f"✅ RAG: {result['documents_indexed']} documenti indicizzati per email {azione.email_id}")
                return True
            else:
                azione.risultato = {
                    'status': 'skipped',
                    'reason': result.get('reason', 'Unknown')
                }
                logger.info(f"⏭️ RAG: Email {azione.email_id} saltata - {result.get('reason')}")
                return True  # Non è un errore, semplicemente non richiede indicizzazione

        except Exception as e:
            logger.error(f"Errore indicizzazione RAG: {e}", exc_info=True)
            azione.risultato = {'error': str(e)}
            return False

    def _execute_parse_interpello(self, azione: Azione) -> bool:
        """
        Schedula parsing interpello in background tramite Celery.

        Il parsing viene eseguito in un task separato con timeout lunghi,
        permettendo a Ollama di lavorare con calma senza bloccare il sistema.
        """
        try:
            email = self.db.query(Email).filter(Email.id == azione.email_id).first()
            if not email:
                logger.error(f"Email {azione.email_id} non trovata")
                return False

            logger.info(f"📋 Scheduling parsing interpello per email {azione.email_id} in background...")

            # Importa task Celery
            from app.tasks.interpello_tasks import parse_interpello

            # Schedula task in background
            task = parse_interpello.delay(
                email_id=azione.email_id,
                azione_id=azione.id
            )

            # Mantieni azione in coda - verrà completata dal task
            azione.stato = StatoAzione.IN_CODA
            azione.risultato = {
                'status': 'scheduled',
                'task_id': task.id,
                'message': 'Parsing schedulato in background con timeout lungo (5 min)'
            }
            self.db.commit()

            logger.info(
                f"✅ Parsing interpello schedulato per email {azione.email_id} "
                f"(Task ID: {task.id}). Verrà processato dal worker Celery."
            )

            # Ritorna True perché lo scheduling è andato a buon fine
            # L'azione verrà completata/fallita dal task in background
            return True

        except Exception as e:
            logger.error(f"Errore scheduling parsing interpello: {e}", exc_info=True)
            azione.risultato = {'error': f'Errore scheduling: {str(e)}'}
            return False

    def _execute_forward(self, azione: Azione) -> bool:
        """
        Inoltra email mantenendo il formato originale (HTML se presente).
        Aggiunge solo un piccolo header e modifica l'oggetto.
        """
        try:
            email = self.db.query(Email).filter(Email.id == azione.email_id).first()
            if not email:
                return False

            params = azione.dettagli.get('parametri', {})
            destinatari = params.get('destinatari', [])

            # Supporta anche parametro 'to' (usato dalle regole)
            if not destinatari:
                to_param = params.get('to')
                if to_param:
                    destinatari = [to_param] if isinstance(to_param, str) else to_param

            if not destinatari:
                logger.warning(f"Nessun destinatario per inoltro email {azione.email_id}")
                return False

            logger.info(f"Inoltra email {azione.email_id} a {len(destinatari)} destinatari")

            # Configura SMTP in base al tipo account
            import smtplib
            import os
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            from email.mime.base import MIMEBase
            from email import encoders

            # Per inoltro ai delegati, usa SEMPRE l'account normale
            # I delegati non necessitano di PEC, e l'account PEC potrebbe essere bloccato
            smtp_host = settings.EMAIL_NORMAL_SMTP_HOST
            smtp_port = settings.EMAIL_NORMAL_SMTP_PORT
            smtp_user = settings.EMAIL_NORMAL_SMTP_USER
            smtp_password = settings.EMAIL_NORMAL_SMTP_PASSWORD

            # Header minimo per l'inoltro
            header_inoltro_html = f"""<div style="background:#f5f5f5; padding:10px; margin-bottom:15px; border-left:4px solid #007bff; font-family:sans-serif; font-size:12px;">
<strong>Messaggio inoltrato</strong><br>
Da: {email.mittente}<br>
Data: {email.data_ricezione}<br>
Oggetto: {email.oggetto}
</div>
<hr style="border:none; border-top:1px solid #ddd; margin:15px 0;">
"""

            header_inoltro_text = f"""---------- Messaggio inoltrato ----------
Da: {email.mittente}
Data: {email.data_ricezione}
Oggetto: {email.oggetto}
-----------------------------------------

"""

            success_count = 0
            errors = []
            allegati_count = len(email.allegati) if email.allegati else 0

            # Rate limiter per evitare blocco IP
            rate_limiter = get_email_rate_limiter()

            for destinatario in destinatari:
                try:
                    # Applica rate limiting prima di ogni invio
                    wait_info = rate_limiter.wait_if_needed()
                    if wait_info['waited']:
                        logger.info(f"⏳ Rate limit applicato: atteso {wait_info['wait_seconds']:.1f}s")

                    # Se rate limited, non bloccare oltre - segna per retry
                    if wait_info.get('rate_limited'):
                        logger.warning(f"🚫 Invio a {destinatario} rate limited - verrà ritentato")
                        errors.append({'email': destinatario, 'error': 'Rate limited - riprovare più tardi'})
                        continue

                    # Crea messaggio multipart per supportare allegati
                    msg = MIMEMultipart('mixed')
                    msg['From'] = f"Segreteria Provinciale SNALS di Taranto <{smtp_user}>"
                    msg['To'] = destinatario
                    msg['Subject'] = f"Fwd: {email.oggetto}"

                    # Corpo: mantieni formato originale (HTML se presente)
                    if email.corpo_html:
                        # Usa HTML originale con header minimo
                        corpo_completo = f"{header_inoltro_html}{email.corpo_html}"
                        msg.attach(MIMEText(corpo_completo, 'html', 'utf-8'))
                    else:
                        # Fallback a testo plain
                        corpo_completo = f"{header_inoltro_text}{email.corpo_testo or ''}"
                        msg.attach(MIMEText(corpo_completo, 'plain', 'utf-8'))

                    # Allega i file originali
                    if email.allegati:
                        for allegato in email.allegati:
                            filepath = allegato.get('path') or ''
                            if not filepath:
                                logger.warning(f"⚠️ Allegato senza path: {allegato.get('filename', 'sconosciuto')}")
                                continue
                            filename = allegato.get('filename', 'allegato')
                            content_type = allegato.get('content_type', 'application/octet-stream')

                            full_path = os.path.join('/app', filepath)

                            if os.path.exists(full_path):
                                with open(full_path, 'rb') as f:
                                    maintype, subtype = content_type.split('/') if '/' in content_type else ('application', 'octet-stream')
                                    part = MIMEBase(maintype, subtype)
                                    part.set_payload(f.read())
                                    encoders.encode_base64(part)
                                    clean_filename = filename.replace('\n', ' ').replace('\r', '').strip()
                                    part.add_header('Content-Disposition', 'attachment', filename=clean_filename)
                                    msg.attach(part)
                            else:
                                logger.warning(f"⚠️ Allegato non trovato: {full_path}")

                    # Invia via SMTP
                    if smtp_port == 465:
                        server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=30)
                    else:
                        server = smtplib.SMTP(smtp_host, smtp_port, timeout=30)
                        server.starttls()

                    server.login(smtp_user, smtp_password)
                    server.sendmail(smtp_user, destinatario, msg.as_string())
                    server.quit()

                    success_count += 1
                    rate_limiter.record_send(success=True)
                    logger.info(f"✅ Email inoltrata a: {destinatario} ({allegati_count} allegati)")

                except Exception as smtp_error:
                    rate_limiter.record_send(success=False)
                    logger.error(f"❌ Errore invio a {destinatario}: {smtp_error}")
                    errors.append({'email': destinatario, 'error': str(smtp_error)})

            if success_count > 0:
                azione.risultato = {
                    'status': 'forwarded',
                    'destinatari_inviati': success_count,
                    'destinatari_totali': len(destinatari),
                    'allegati': allegati_count,
                    'errors': errors if errors else None
                }
                logger.info(f"✅ Email inoltrata a {success_count}/{len(destinatari)} destinatari ({allegati_count} allegati)")
                return True

            azione.risultato = {
                'status': 'failed',
                'errors': errors,
                'message': 'Nessuna email inviata con successo'
            }
            return False

        except Exception as e:
            logger.error(f"Errore inoltro: {e}")
            azione.risultato = {'error': str(e)}
            return False

    def _execute_forward_delegati_zona(self, azione: Azione) -> bool:
        """
        Inoltra email ai delegati della zona.
        Identifica automaticamente la zona della scuola mittente.
        """
        try:
            email = self.db.query(Email).filter(Email.id == azione.email_id).first()
            if not email:
                logger.error(f"Email {azione.email_id} non trovata")
                return False

            # Estrai codice scuola dal mittente
            import re
            from app.models.delegato import Zona, Delegato
            from app.services.school_identifier import get_school_identifier

            mittente = email.mittente

            # Prima prova a estrarre mittente reale da "Per conto di:" nelle PEC
            per_conto_match = re.search(r'per conto di:\s*([^\s<>"]+@[^\s<>"]+)', mittente.lower())
            if per_conto_match:
                mittente = per_conto_match.group(1)
                logger.info(f"📧 Estratto mittente reale da 'Per conto di:': {mittente}")

            # Pattern: 4 lettere + 6 caratteri alfanumerici (6 cifre o 5 cifre + 1 lettera)
            match = re.search(r'([a-z]{4}[a-z0-9]{6})@(pec\.)?istruzione\.it', mittente, re.IGNORECASE)

            if not match:
                logger.warning(f"Codice scuola non trovato nel mittente: {email.mittente}")
                azione.risultato = {
                    'status': 'manual_intervention_required',
                    'error': 'Impossibile identificare la scuola dal mittente',
                    'message': '⚠️ INTERVENTO UMANO RICHIESTO: Email non proviene da scuola riconosciuta'
                }
                return False

            school_code = match.group(1).upper()
            logger.info(f"📍 Codice scuola identificato: {school_code}")

            # Trova informazioni scuola
            school_identifier = get_school_identifier()
            school_info = school_identifier.get_school_info(school_code)

            if not school_info:
                logger.warning(f"Scuola {school_code} non trovata nel database")
                azione.risultato = {
                    'status': 'manual_intervention_required',
                    'error': f'Scuola {school_code} non trovata',
                    'message': f'⚠️ INTERVENTO UMANO RICHIESTO: Scuola {school_code} non censita nel database'
                }
                return False

            comune = school_info.get('comune', '').upper()
            if not comune:
                logger.warning(f"Comune non disponibile per scuola {school_code}")
                azione.risultato = {
                    'status': 'manual_intervention_required',
                    'error': 'Comune non disponibile',
                    'message': '⚠️ INTERVENTO UMANO RICHIESTO: Comune della scuola non disponibile'
                }
                return False

            logger.info(f"🏫 Scuola: {school_info.get('denominazione')} - Comune: {comune}")

            # Trova zona che include questo comune
            zone = self.db.query(Zona).filter(Zona.attiva == True).all()
            zona_trovata = None

            for zona in zone:
                if comune in [c.upper() for c in zona.get_comuni()]:
                    zona_trovata = zona
                    break

            if not zona_trovata:
                logger.warning(f"Nessuna zona trovata per comune {comune}")
                azione.risultato = {
                    'status': 'manual_intervention_required',
                    'error': f'Nessuna zona trovata per comune {comune}',
                    'message': f'⚠️ INTERVENTO UMANO RICHIESTO: Comune {comune} non assegnato a nessuna zona',
                    'school_info': school_info
                }
                return False

            logger.info(f"📍 Zona trovata: {zona_trovata.nome}")

            # Trova delegati attivi della zona
            delegati = [d for d in zona_trovata.delegati if d.attivo]

            if not delegati:
                logger.warning(f"Nessun delegato attivo per zona {zona_trovata.nome}")
                azione.risultato = {
                    'status': 'manual_intervention_required',
                    'error': f'Nessun delegato attivo per zona {zona_trovata.nome}',
                    'message': f'⚠️ INTERVENTO UMANO RICHIESTO: Zona {zona_trovata.nome} non ha delegati attivi',
                    'zona': zona_trovata.nome,
                    'school_info': school_info
                }
                return False

            logger.info(f"👥 Trovati {len(delegati)} delegati attivi")

            # Invia email ai delegati via SMTP (inoltro completo con allegati)
            dettagli = azione.dettagli or {}
            params = dettagli.get('parametri', {})

            # Configura SMTP in base al tipo account
            import smtplib
            import os
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            from email.mime.base import MIMEBase
            from email import encoders

            # Per inoltro agli iscritti, usa SEMPRE l'account normale
            # Gli iscritti non necessitano di PEC, e l'account PEC potrebbe essere bloccato
            smtp_host = settings.EMAIL_NORMAL_SMTP_HOST
            smtp_port = settings.EMAIL_NORMAL_SMTP_PORT
            smtp_user = settings.EMAIL_NORMAL_SMTP_USER
            smtp_password = settings.EMAIL_NORMAL_SMTP_PASSWORD

            success_count = 0
            errors = []
            allegati_count = len(email.allegati) if email.allegati else 0

            # Estrai data e ora convocazione dall'interpretazione
            data_convocazione = None
            ora_convocazione = None
            if email.interpretazione and email.interpretazione.interpretazione_json:
                interp = email.interpretazione.interpretazione_json
                data_convocazione = interp.get('data_convocazione') or interp.get('data')
                ora_convocazione = interp.get('ora')

            # Formatta data per visualizzazione
            data_formattata = ""
            if data_convocazione:
                try:
                    from datetime import datetime
                    if 'T' in str(data_convocazione):
                        dt = datetime.fromisoformat(str(data_convocazione).replace('Z', ''))
                        data_formattata = dt.strftime('%d/%m/%Y')
                    else:
                        data_formattata = str(data_convocazione)
                except:
                    data_formattata = str(data_convocazione)

            # Costruisci info convocazione per oggetto e header
            nome_scuola = school_info.get('nome', school_code)
            info_convocazione = f"{nome_scuola}"
            if data_formattata:
                info_convocazione += f" - {data_formattata}"
            if ora_convocazione:
                info_convocazione += f" ore {ora_convocazione}"

            # Header inoltro con info scuola
            header_inoltro = f"""📢 CONVOCAZIONE: {info_convocazione}

---------- Messaggio inoltrato ----------
Scuola: {nome_scuola} ({comune})
Da: {email.mittente}
Data email: {email.data_ricezione}
Oggetto: {email.oggetto}
"""
            if data_formattata or ora_convocazione:
                header_inoltro += f"Data convocazione: {data_formattata or 'N/D'} {('ore ' + ora_convocazione) if ora_convocazione else ''}\n"

            # Rate limiter per evitare blocco IP
            rate_limiter = get_email_rate_limiter()
            logger.info(f"📧 Inizio invio a {len(delegati)} delegati...")

            for i, delegato in enumerate(delegati):
                logger.info(f"📧 [{i+1}/{len(delegati)}] Preparazione invio a {delegato.email}")
                try:
                    # Applica rate limiting prima di ogni invio
                    logger.info(f"📧 Chiamata wait_if_needed()...")
                    wait_info = rate_limiter.wait_if_needed()
                    logger.info(f"📧 wait_if_needed() completato: waited={wait_info.get('waited')}, rate_limited={wait_info.get('rate_limited')}")
                    if wait_info['waited']:
                        logger.info(f"⏳ Rate limit applicato: atteso {wait_info['wait_seconds']:.1f}s")

                    # Se rate limited, non bloccare oltre - segna per retry
                    if wait_info.get('rate_limited'):
                        logger.warning(f"🚫 Invio a {delegato.email} rate limited - verrà ritentato")
                        errors.append({'email': delegato.email, 'error': 'Rate limited - riprovare più tardi'})
                        continue

                    # Crea messaggio multipart per allegati
                    msg = MIMEMultipart('mixed')
                    msg['From'] = f"Segreteria Provinciale SNALS di Taranto <{smtp_user}>"
                    msg['To'] = delegato.email
                    msg['Subject'] = f"[{nome_scuola}] {email.oggetto}"

                    # Corpo: header inoltro + corpo originale
                    if email.corpo_html:
                        corpo_completo = f"<pre>{header_inoltro}</pre><hr>{email.corpo_html}"
                        msg.attach(MIMEText(corpo_completo, 'html', 'utf-8'))
                    else:
                        corpo_completo = f"{header_inoltro}\n{email.corpo_testo or ''}"
                        msg.attach(MIMEText(corpo_completo, 'plain', 'utf-8'))

                    # Allega i file originali
                    if email.allegati:
                        for allegato in email.allegati:
                            filepath = allegato.get('path') or ''
                            if not filepath:
                                logger.warning(f"⚠️ Allegato senza path: {allegato.get('filename', 'sconosciuto')}")
                                continue
                            filename = allegato.get('filename', 'allegato')
                            content_type = allegato.get('content_type', 'application/octet-stream')

                            full_path = os.path.join('/app', filepath)

                            if os.path.exists(full_path):
                                with open(full_path, 'rb') as f:
                                    maintype, subtype = content_type.split('/') if '/' in content_type else ('application', 'octet-stream')
                                    part = MIMEBase(maintype, subtype)
                                    part.set_payload(f.read())
                                    encoders.encode_base64(part)
                                    clean_filename = filename.replace('\n', ' ').replace('\r', '').strip()
                                    part.add_header('Content-Disposition', 'attachment', filename=clean_filename)
                                    msg.attach(part)
                                    logger.info(f"📎 Allegato incluso: {clean_filename}")
                            else:
                                logger.warning(f"⚠️ Allegato non trovato: {full_path}")

                    # Invia via SMTP
                    if smtp_port == 465:
                        server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=30)
                    else:
                        server = smtplib.SMTP(smtp_host, smtp_port, timeout=30)
                        server.starttls()

                    server.login(smtp_user, smtp_password)
                    server.sendmail(smtp_user, delegato.email, msg.as_string())
                    server.quit()

                    success_count += 1
                    rate_limiter.record_send(success=True)
                    logger.info(f"✅ Email inoltrata a: {delegato.nome} {delegato.cognome} <{delegato.email}> ({allegati_count} allegati)")

                except Exception as smtp_error:
                    rate_limiter.record_send(success=False)
                    logger.error(f"❌ Errore invio a {delegato.email}: {smtp_error}")
                    errors.append({'email': delegato.email, 'error': str(smtp_error)})

            if success_count > 0:
                azione.risultato = {
                    'status': 'sent',
                    'delegati_notificati': success_count,
                    'delegati_totali': len(delegati),
                    'allegati': allegati_count,
                    'zona': zona_trovata.nome,
                    'comune': comune,
                    'scuola': school_info.get('nome', school_code),
                    'delegati_lista': [{'nome': f"{d.nome} {d.cognome}", 'email': d.email} for d in delegati[:success_count]],
                    'errors': errors if errors else None
                }
                logger.info(f"✅ Inviate {success_count}/{len(delegati)} email per delegati zona {zona_trovata.nome} ({allegati_count} allegati)")
                return True

            azione.risultato = {
                'status': 'failed',
                'errors': errors,
                'message': 'Nessuna email inviata con successo'
            }
            return False

        except Exception as e:
            logger.error(f"❌ Errore inoltro delegati zona: {e}", exc_info=True)
            azione.risultato = {
                'status': 'manual_intervention_required',
                'error': str(e),
                'message': f'⚠️ INTERVENTO UMANO RICHIESTO: Errore inoltro ai delegati ({str(e)})'
            }
            return False

    def _execute_notify(self, azione: Azione) -> bool:
        """Invia notifica."""
        try:
            email = self.db.query(Email).filter(Email.id == azione.email_id).first()
            if not email:
                return False

            params = azione.dettagli.get('parametri', {})
            destinatari = params.get('destinatari', [])
            urgente = params.get('urgente', False)

            if not destinatari:
                logger.warning(f"Nessun destinatario per notifica email {azione.email_id}")
                return False

            logger.info(f"Invia notifica per email {azione.email_id} a {len(destinatari)} destinatari (urgente: {urgente})")

            # Prepara notifica
            subject = f"{'[URGENTE] ' if urgente else ''}Nuova email: {email.oggetto[:50]}"
            body = f"""
{'🚨 NOTIFICA URGENTE 🚨' if urgente else 'Notifica'}

È arrivata una nuova email che richiede attenzione:

Da: {email.mittente}
Oggetto: {email.oggetto}
Data: {email.data_ricezione}
Categoria: {email.get_categoria_value() or 'N/A'}

Anteprima:
{email.corpo_testo[:300]}...

---
Accedi al sistema per visualizzare l'email completa.
"""

            # Invia notifica via email usando webmail client
            webmail = WebmailClient('normal')  # Usa account normale per notifiche
            success_count = 0

            for destinatario in destinatari:
                success = webmail.send_email(
                    to=destinatario,
                    subject=subject,
                    body=body
                )
                if success:
                    success_count += 1

            if success_count > 0:
                azione.risultato = {
                    'status': 'notified',
                    'destinatari_notificati': success_count,
                    'destinatari_totali': len(destinatari),
                    'urgente': urgente
                }
                logger.info(f"✅ Notifica inviata a {success_count}/{len(destinatari)} destinatari")
                return True

            return False

        except Exception as e:
            logger.error(f"Errore invio notifica: {e}")
            azione.risultato = {'error': str(e)}
            return False

    def _extract_school_name_from_text(self, testo: str, codice_mecc: str) -> Optional[str]:
        """
        Estrae nome scuola dal testo (firma/intestazione).

        Cerca pattern come:
        - "ISTITUTO COMPRENSIVO ... "
        - "I.C. ..."
        - "DIREZIONE DIDATTICA ..."
        - Intestazioni con nome scuola

        Args:
            testo: Testo completo email/allegati
            codice_mecc: Codice meccanografico scuola

        Returns:
            Nome scuola se trovato, None altrimenti
        """
        if not testo:
            return None

        import re

        # Pattern per nomi scuola
        patterns = [
            r'ISTITUTO\s+COMPRENSIVO\s+["\']?([A-Z][A-Za-zÀ-ÿ\s\.]+?)["\']?\s*(?:\n|$|Vicolo|Via|Piazza)',
            r'I\.C\.\s+["\']?([A-Z][A-Za-zÀ-ÿ\s\.]+?)["\']?\s*(?:\n|$|Vicolo|Via)',
            r'IC\s+["\']?([A-Z][A-Za-zÀ-ÿ\s\.]+?)["\']?\s*(?:\n|$|Vicolo|Via)',
            r'DIREZIONE\s+DIDATTICA\s+["\']?([A-Z][A-Za-zÀ-ÿ\s\.]+?)["\']?\s*(?:\n|$|Via)',
            r'LICEO\s+(?:SCIENTIFICO|CLASSICO|LINGUISTICO)?\s*["\']?([A-Z][A-Za-zÀ-ÿ\s\.]+?)["\']?\s*(?:\n|$|Via)',
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, testo, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                nome = match.group(1).strip()
                # Pulisci nome (rimuovi extra spaces, punteggiatura finale)
                nome = re.sub(r'\s+', ' ', nome).strip(' .')
                if len(nome) > 3:  # Nome valido
                    logger.info(f"📍 Nome scuola estratto dal testo: {nome}")
                    return nome

        return None

    def _replace_school_codes(self, text: str) -> str:
        """
        Sostituisce i codici meccanografici con nome scuola (comune).

        Cerca pattern come TAIC851009, TAEE123456 e li sostituisce
        con il nome della scuola e il comune dal database.

        Args:
            text: Testo contenente possibili codici meccanografici

        Returns:
            Testo con codici sostituiti
        """
        import re
        from app.services.school_identifier import get_school_identifier

        if not text:
            return text

        # Pattern codice meccanografico: 4 lettere + 6 caratteri alfanumerici
        pattern = r'\b([A-Z]{4}[A-Z0-9]{6})\b'

        def replace_code(match):
            code = match.group(1).upper()
            try:
                school_identifier = get_school_identifier()
                info = school_identifier.get_school_info(code)
                if info:
                    nome = info.get('nome', code)
                    comune = info.get('comune', '')
                    # Formato: "CODICE - Nome Scuola (Comune)"
                    if comune:
                        return f"{code} - {nome} ({comune})"
                    return f"{code} - {nome}"
            except Exception as e:
                logger.warning(f"Errore sostituzione codice {code}: {e}")
            return code

        return re.sub(pattern, replace_code, text, flags=re.IGNORECASE)

    def _clean_sintesi(self, sintesi: str) -> str:
        """
        Pulisce la sintesi rimuovendo testo indesiderato.

        Rimuove:
        - Preamboli ("Ecco la sintesi", "Ecco una sintesi concisa", etc.)
        - Disclaimer sulla riservatezza/confidenzialità
        - Ripetizioni di mittente, data, ora
        - Frasi inutili su allegati

        Args:
            sintesi: Testo sintesi generato da LLM

        Returns:
            Sintesi pulita
        """
        import re

        if not sintesi:
            return sintesi

        # Pattern da rimuovere (case insensitive)
        patterns_to_remove = [
            # Preamboli - cattura "Ecco la/una/il sintesi/contenuto" con varianti
            r"^ecco\s+(?:la|una|il)\s+(?:sintesi|contenuto\s+principale)\s*(?:concisa|breve)?\s*(?:dell[a']?\s*)?(?:email|mail)?(?:\s+in\s+\d[^\n:]*)?[:\.\s]*",
            r'^(?:la\s+)?sintesi\s+(?:dell[a\']?\s*)?(?:email|mail)\s*(?:è)?[:\.\s]*',
            r'^in\s+sintesi[:\.\s]*',
            r'^riassumendo[:\.\s]*',
            r'^ecco\s+(?:il|la)\s+[^\n:]+:\s*',  # Catch-all per "Ecco il/la ...:"

            # Disclaimer riservatezza/confidenzialità (multilinea)
            r'(?:questo\s+messaggio|questa\s+(?:email|comunicazione))\s+(?:è\s+)?(?:destinat[oa]\s+)?(?:esclusivamente|solo)\s+a[^\n]*(?:riservatezza|confidenzial)[^\n]*',
            r'(?:le?\s+informazioni\s+contenute|il\s+contenuto)[^\n]*(?:confidenzial[ei]|riservat[eo])[^\n]*',
            r'se\s+(?:non\s+siete|avete\s+ricevuto)[^\n]*(?:errore|destinatario)[^\n]*(?:distruggere|cancellare|eliminare)?[^\n]*',
            r'ai\s+sensi\s+(?:del|della)\s+(?:d\.?lgs|legge|normativa)[^\n]*(?:privacy|679\/2016|196\/2003)[^\n]*',
            r'(?:firma\s+)?autografa\s+omessa[^\n]*',
            r'disclaimer[:\s]*[^\n]*',

            # Frasi inutili su allegati
            r'nessun\s+allegato\s+(?:è\s+)?(?:richiesto|presente|necessario)[^\n]*',
            r'non\s+(?:ci\s+)?sono\s+allegati[^\n]*',

            # Ripetizioni mittente/data (inizio riga)
            r'^mittente[:\s]+[^\n]*\n',
            r'^da[:\s]+[^\n]*@[^\n]*\n',
            r'^data[:\s]+\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}[^\n]*\n',
            r'^(?:data\s+e\s+)?ora[:\s]+\d{1,2}[:\.\s]\d{2}[^\n]*\n',
            r'^ricevuta?\s+(?:il|in\s+data)[:\s]+[^\n]*\n',

            # Footer/firme generiche
            r'cordiali\s+saluti[,\.\s]*$',
            r'distinti\s+saluti[,\.\s]*$',
            r'il\s+dirigente\s+scolastico[^\n]*$',
        ]

        cleaned = sintesi

        for pattern in patterns_to_remove:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE | re.MULTILINE)

        # Rimuovi linee vuote multiple
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)

        # Rimuovi spazi multipli
        cleaned = re.sub(r'  +', ' ', cleaned)

        # Strip finale
        cleaned = cleaned.strip()

        # Rileva "prompt leakage" - quando l'LLM include istruzioni del prompt nell'output
        prompt_leak_indicators = [
            'le regole sono chiare',
            'scrivere solo il contenuto',
            'evitare di includere',
            'concentrati su',
            'non ripetere mittente',
            'non includere disclaimer',
            'senza preamboli',
            'frasi introduttive',
        ]

        for indicator in prompt_leak_indicators:
            if indicator in cleaned.lower():
                logger.warning(f"⚠️ Rilevato prompt leakage nella sintesi: '{indicator}'")
                # Tronca la sintesi prima del leak
                idx = cleaned.lower().find(indicator)
                if idx > 30:  # Se c'è abbastanza testo prima
                    cleaned = cleaned[:idx].rstrip(' .,;:-')
                    logger.info(f"Sintesi troncata a {len(cleaned)} caratteri")
                    break

        # Se il testo è diventato troppo corto, restituisci originale
        if len(cleaned) < 20 and len(sintesi) > 20:
            logger.warning(f"⚠️ Sintesi pulita troppo corta ({len(cleaned)} chars), uso originale")
            cleaned = sintesi.strip()

        # TRONCATURA OBBLIGATORIA a max 20 parole
        words = cleaned.split()
        if len(words) > 20:
            cleaned = ' '.join(words[:20])
            # Non terminare con articoli/preposizioni
            while cleaned.split()[-1].lower() in ['il', 'la', 'lo', 'i', 'le', 'gli', 'un', 'una', 'di', 'da', 'in', 'a', 'per', 'con', 'su', 'che', 'e']:
                words = cleaned.split()[:-1]
                cleaned = ' '.join(words)
            logger.info(f"📝 Sintesi troncata a {len(cleaned.split())} parole")

        return cleaned
