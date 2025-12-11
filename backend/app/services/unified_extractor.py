"""
Servizio di Estrazione Unificato per Email SNALS.

Pipeline standard:
1. Regex - pattern strutturati (veloce, affidabile)
2. NLP locale (spaCy + BERT) - entità e contesto
3. LLM locale (Ollama) - comprensione semantica
4. ChatGPT (opzionale) - fallback se autorizzato dall'utente

Supporta tipi:
- interpello: classi concorso, scuole, province, ore
- calendario: date, orari, luoghi, tipo riunione
"""

import re
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

# Import preprocessor per troncamento intelligente
from app.utils.text_preprocessor import preprocess_for_llm, smart_truncate

logger = logging.getLogger(__name__)


class UnifiedExtractor:
    """
    Estrattore unificato per email SNALS.

    Combina Regex + NLP + LLM in una pipeline intelligente.
    Usa la coda LLM per evitare sovraccarichi e timeout.
    """

    @staticmethod
    def _normalize_classe_concorso(classe: str) -> str:
        """
        Normalizza il formato della classe di concorso.

        Formati supportati:
        - Standard: A-26, B-17, C-01
        - Speciali: ADSS, ADMM, AL01, EH01
        - Input vari: A034 → A-34, A 26 → A-26, a-26 → A-26

        Args:
            classe: Classe di concorso grezza

        Returns:
            Classe normalizzata (es: "A-34", "ADSS", "AL01")
        """
        if not classe:
            return classe

        # Uppercase e rimuovi spazi
        classe = classe.upper().strip().replace(' ', '')

        # Classi speciali che NON hanno il trattino (codici a 4+ lettere)
        special_classes = ['ADSS', 'ADMM', 'ADEE', 'PPPP', 'EEEE', 'AAAA']
        if classe in special_classes:
            return classe

        # Classi con prefisso lettere + numeri (es: AL01, EH01)
        # Queste NON hanno trattino nel formato standard
        # Prima rimuovi eventuale trattino per matchare il pattern
        classe_no_hyphen = classe.replace('-', '')
        al_pattern = re.match(r'^(A[DELMNR]|B[ACEGISTU]|E[HI]|P[AEPS])(\d{2})$', classe_no_hyphen)
        if al_pattern:
            return f"{al_pattern.group(1)}{al_pattern.group(2)}"

        # Se ha già il trattino nel posto giusto, normalizza solo
        if '-' in classe:
            parts = classe.split('-')
            if len(parts) == 2:
                letters = parts[0]
                numbers = parts[1].lstrip('0') or '0'
                # Pad a 2 cifre se necessario
                if len(numbers) == 1:
                    numbers = numbers.zfill(2)
                return f"{letters}-{numbers}"

        # Se NON ha trattino: cerca pattern lettere+numeri
        match = re.match(r'^([A-Z]{1,2})(\d{2,3})$', classe)
        if match:
            letters = match.group(1)
            numbers = match.group(2).lstrip('0') or '0'
            # Pad a 2 cifre
            if len(numbers) == 1:
                numbers = numbers.zfill(2)
            return f"{letters}-{numbers}"

        # Fallback: ritorna com'è
        return classe

    def __init__(self, use_queue: bool = True):
        """
        Args:
            use_queue: Se True, usa llm_queue_service per chiamate LLM (raccomandato).
                      Se False, usa LLMClient diretto (solo per test).
        """
        self._nlp_extractor = None
        self._llm_client = None
        self._llm_queue = None
        self._openai_enabled = False
        self._ollama_enabled = True
        self._use_queue = use_queue

    def _get_nlp_extractor(self):
        """Lazy load NLP extractor."""
        if self._nlp_extractor is None:
            from app.services.nlp_service import get_nlp_extractor
            self._nlp_extractor = get_nlp_extractor()
        return self._nlp_extractor

    def _get_llm_client(self):
        """Lazy load LLM client (per chiamate dirette, non raccomandato)."""
        if self._llm_client is None:
            from app.integrations.llm_client import LLMClient
            self._llm_client = LLMClient()
        return self._llm_client

    def _get_llm_queue(self):
        """Lazy load LLM queue service."""
        if self._llm_queue is None:
            from app.services.llm_queue_service import get_llm_queue
            self._llm_queue = get_llm_queue()
        return self._llm_queue

    def _call_llm(
        self,
        prompt: str,
        model_type: str = "interpretation",
        format_json: bool = True,
        timeout: int = 90,
        request_tipo: str = "extraction"
    ) -> Optional[Dict]:
        """
        Chiama LLM usando la coda se abilitata, altrimenti diretto.

        Args:
            prompt: Il prompt da inviare
            model_type: Tipo di modello (categorization, interpretation, generation)
            format_json: Se True, richiede risposta JSON
            timeout: Timeout in secondi
            request_tipo: Tipo richiesta per logging (extraction, validation)

        Returns:
            Dict con risposta parsata, o None se errore
        """
        if self._use_queue:
            # Usa la coda LLM per evitare sovraccarichi
            queue = self._get_llm_queue()
            try:
                request_id = queue.enqueue(
                    tipo=request_tipo,
                    prompt=prompt,
                    model_type=model_type,
                    format_json=format_json,
                    priorita=3  # Priorità media-alta
                )
                logger.debug(f"📤 Richiesta LLM {request_id} in coda (tipo: {request_tipo})")

                # Attendi risultato
                result = queue.wait_for_result(request_id, timeout=timeout)

                if result and result.get('stato') == 'completata':
                    # Risposta già parsata
                    if result.get('risposta_parsed'):
                        return result['risposta_parsed']
                    # Prova a parsare la risposta raw
                    elif result.get('risposta'):
                        try:
                            return json.loads(result['risposta'])
                        except json.JSONDecodeError:
                            # Prova a estrarre JSON dal testo
                            response_text = result['risposta']
                            if '```json' in response_text:
                                response_text = response_text.split('```json')[1].split('```')[0]
                            elif '```' in response_text:
                                response_text = response_text.split('```')[1].split('```')[0]
                            return json.loads(response_text.strip())
                elif result and result.get('stato') == 'fallita':
                    logger.warning(f"⚠️ Richiesta LLM {request_id} fallita: {result.get('errore')}")
                else:
                    logger.warning(f"⚠️ Timeout richiesta LLM {request_id}")

            except Exception as e:
                logger.error(f"❌ Errore coda LLM: {e}")

            return None
        else:
            # Chiamata diretta (non raccomandata per produzione)
            llm = self._get_llm_client()
            try:
                response = llm.generate(
                    prompt=prompt,
                    model_type=model_type,
                    format_json=format_json,
                    temperature=0.1,
                    timeout=timeout
                )

                if response and isinstance(response, dict):
                    return response
                elif response and isinstance(response, str):
                    return json.loads(response)
            except Exception as e:
                logger.warning(f"LLM direct call failed: {e}")

            return None

    def extract(
        self,
        testo: str,
        tipo: str = "interpello",
        use_ollama: bool = True,
        use_chatgpt: bool = None,
        chatgpt_as_fallback: bool = None
    ) -> Dict[str, Any]:
        """
        Estrae dati strutturati dal testo usando la pipeline completa.

        Args:
            testo: Testo da analizzare (corpo email + allegati)
            tipo: "interpello" o "calendario"
            use_ollama: Usa LLM locale (Ollama) per migliorare estrazione
            use_chatgpt: Usa ChatGPT (None=leggi da impostazioni sistema)
            chatgpt_as_fallback: ChatGPT solo come fallback (None=leggi da impostazioni)

        Returns:
            Dict con dati estratti e metadati pipeline
        """
        if not testo or len(testo.strip()) < 10:
            return self._empty_result(tipo, "Testo troppo corto")

        # Leggi impostazioni ChatGPT da sistema se non specificate
        if use_chatgpt is None or chatgpt_as_fallback is None:
            try:
                from app.services.system_settings_service import get_chatgpt_settings
                chatgpt_settings = get_chatgpt_settings()
                if use_chatgpt is None:
                    use_chatgpt = chatgpt_settings['enabled']
                if chatgpt_as_fallback is None:
                    chatgpt_as_fallback = chatgpt_settings['as_fallback']
                self._chatgpt_threshold = chatgpt_settings['fallback_threshold']
            except Exception as e:
                logger.warning(f"Impossibile leggere impostazioni ChatGPT: {e}")
                use_chatgpt = use_chatgpt if use_chatgpt is not None else False
                chatgpt_as_fallback = chatgpt_as_fallback if chatgpt_as_fallback is not None else True
                self._chatgpt_threshold = 0.5

        logger.info(f"🔄 UnifiedExtractor: avvio pipeline per tipo={tipo} (ChatGPT: enabled={use_chatgpt}, fallback={chatgpt_as_fallback})")

        # Risultato finale
        result = self._empty_result(tipo)
        result['_pipeline_steps'] = []

        # STEP 1: Regex
        logger.info("📝 Step 1: Estrazione Regex...")
        regex_result = self._extract_with_regex(testo, tipo)
        result = self._merge_results(result, regex_result, source="regex")
        result['_pipeline_steps'].append({
            'step': 'regex',
            'fields_found': self._count_fields(regex_result),
            'success': self._count_fields(regex_result) > 0
        })

        # STEP 2: NLP (spaCy + BERT)
        logger.info("🧠 Step 2: Estrazione NLP (spaCy + BERT)...")
        try:
            nlp_result = self._extract_with_nlp(testo, tipo)
            result = self._merge_results(result, nlp_result, source="nlp")
            result['_pipeline_steps'].append({
                'step': 'nlp',
                'fields_found': self._count_fields(nlp_result),
                'success': self._count_fields(nlp_result) > 0
            })
        except Exception as e:
            logger.warning(f"⚠️ NLP fallito: {e}")
            result['_pipeline_steps'].append({
                'step': 'nlp',
                'fields_found': 0,
                'success': False,
                'error': str(e)
            })

        # Valuta completezza
        completeness = self._calculate_completeness(result, tipo)
        result['_completeness'] = completeness

        # STEP 3: LLM locale (Ollama) - se abilitato e serve
        if use_ollama and completeness < 0.7:
            logger.info(f"🤖 Step 3: LLM locale (Ollama) - completezza={completeness:.1%}")
            try:
                ollama_result = self._extract_with_ollama(testo, tipo, result)
                result = self._merge_results(result, ollama_result, source="ollama")
                result['_pipeline_steps'].append({
                    'step': 'ollama',
                    'fields_found': self._count_fields(ollama_result),
                    'success': self._count_fields(ollama_result) > 0
                })
                completeness = self._calculate_completeness(result, tipo)
                result['_completeness'] = completeness
            except Exception as e:
                logger.warning(f"⚠️ Ollama fallito: {e}")
                result['_pipeline_steps'].append({
                    'step': 'ollama',
                    'fields_found': 0,
                    'success': False,
                    'error': str(e)
                })

        # STEP 4: ChatGPT - se autorizzato e serve
        # Usa soglia dinamica dalle impostazioni (default 0.5)
        chatgpt_threshold = getattr(self, '_chatgpt_threshold', 0.5)
        should_use_chatgpt = (
            use_chatgpt and (
                not chatgpt_as_fallback or  # Uso diretto
                completeness < chatgpt_threshold  # Fallback sotto soglia
            )
        )

        if should_use_chatgpt:
            logger.info(f"🌐 Step 4: ChatGPT - completezza={completeness:.1%}")
            try:
                chatgpt_result = self._extract_with_chatgpt(testo, tipo, result)
                result = self._merge_results(result, chatgpt_result, source="chatgpt")
                result['_pipeline_steps'].append({
                    'step': 'chatgpt',
                    'fields_found': self._count_fields(chatgpt_result),
                    'success': self._count_fields(chatgpt_result) > 0
                })
                completeness = self._calculate_completeness(result, tipo)
                result['_completeness'] = completeness
            except Exception as e:
                logger.warning(f"⚠️ ChatGPT fallito: {e}")
                result['_pipeline_steps'].append({
                    'step': 'chatgpt',
                    'fields_found': 0,
                    'success': False,
                    'error': str(e)
                })

        # STEP 5: Validazione semantica e di contesto con LLM
        if use_ollama and self._count_fields(result) > 0:
            logger.info("🔍 Step 5: Validazione semantica con LLM...")
            try:
                validated_result = self._validate_with_llm(testo, tipo, result)
                if validated_result:
                    result = validated_result
                    result['_pipeline_steps'].append({
                        'step': 'validation',
                        'success': True,
                        'corrections': validated_result.get('_validation_corrections', 0)
                    })
            except Exception as e:
                logger.warning(f"⚠️ Validazione LLM fallita: {e}")
                result['_pipeline_steps'].append({
                    'step': 'validation',
                    'success': False,
                    'error': str(e)
                })

        # STEP 6: Sanity check per calendario (data/ora/luogo ragionevoli)
        if tipo == "calendario":
            logger.info("🔍 Step 6: Sanity check dati calendario...")
            result = self._sanity_check_calendario(result)
            sanity_passed = result.get('_sanity_passed', True)
            sanity_issues = result.get('_sanity_issues', [])
            result['_pipeline_steps'].append({
                'step': 'sanity_check',
                'success': sanity_passed,
                'issues': sanity_issues
            })
            if not sanity_passed:
                logger.warning(f"⚠️ Sanity check fallito: {sanity_issues}")

        # Calcola confidence finale
        result['_overall_confidence'] = self._calculate_confidence(result)
        result['_extraction_method'] = 'unified_pipeline'
        result['_timestamp'] = datetime.now().isoformat()
        result['_settings'] = {
            'chatgpt_enabled': use_chatgpt,
            'chatgpt_as_fallback': chatgpt_as_fallback,
            'chatgpt_threshold': chatgpt_threshold,
            'use_queue': self._use_queue
        }

        logger.info(f"✅ UnifiedExtractor completato: completezza={completeness:.1%}, confidence={result['_overall_confidence']:.2f}")

        return result

    def _empty_result(self, tipo: str, error: str = None) -> Dict[str, Any]:
        """Crea risultato vuoto per il tipo specificato."""
        if tipo == "calendario":
            result = {
                'data_inizio': None,
                'ora_inizio': None,
                'data_fine': None,
                'ora_fine': None,
                'luogo': None,
                'scuola_nome': None,
                'scuola_codice': None,
                'modalita': None,
                'tipo_riunione': None,
                'motivo': None,
                'contatto_email': None,
                'contatto_telefono': None,
            }
        else:  # interpello
            result = {
                'classe_concorso': None,
                'ore_settimanali': None,
                'provincia': None,
                'citta': None,
                'istituto': None,
                'meccanografico': None,
                'email_contatto': None,
                'telefono_contatto': None,
                'data_scadenza': None,
            }

        result['_sources'] = {}
        result['_confidence_scores'] = {}

        if error:
            result['_error'] = error

        return result

    def _extract_with_regex(self, testo: str, tipo: str) -> Dict[str, Any]:
        """Estrazione con pattern regex."""
        result = {}
        text_lower = testo.lower()

        if tipo == "calendario":
            # Date (DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY) - con gestione PEC headers
            # PRIORITÀ 1: Date testuali con anno (es: "4 dicembre 2025")
            MESI_MAP = {'gennaio': '01', 'febbraio': '02', 'marzo': '03', 'aprile': '04',
                        'maggio': '05', 'giugno': '06', 'luglio': '07', 'agosto': '08',
                        'settembre': '09', 'ottobre': '10', 'novembre': '11', 'dicembre': '12'}

            # Pattern per date testuali con anno esplicito
            textual_date_with_year_patterns = [
                # Priorità alta: Date con contesto convocazione esplicito
                r'(?:convocati?e?|invitati?e?|si\s+terrà|fissata?|prevista?)\s+(?:per\s+)?(?:il\s+giorno\s+|il\s+|mercoledì|giovedì|venerdì|lunedì|martedì|sabato|domenica)?\s*(\d{1,2})\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+(\d{4})',
                # "in data 4 dicembre 2025" (NO "del" da solo - troppo generico, cattura norme)
                r'(?:in\s+data|giorno)\s+(\d{1,2})\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+(\d{4})',
                # Data in oggetto email "Convocazione ... 4 dicembre 2025"
                r'(?:convocazione)[^.]{0,80}?(\d{1,2})\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+(\d{4})',
            ]

            # Pattern per date testuali SENZA anno (es: "3 dicembre ore 10")
            textual_date_no_year_patterns = [
                r'(?:convocati?e?|invitati?e?|incontro|riunione)\s+[^.]{0,30}?(\d{1,2})\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)(?:\s+ore|\s*$|[^0-9a-z])',
                r'(?:convocazione)[^.]{0,50}?(\d{1,2})\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)(?:\s+ore|\s*$|[^0-9a-z])',
            ]

            # Pattern per date numeriche con contesto
            convocation_date_patterns = [
                r'(?:convocato|convocazione|convocati|invitati?)\s+(?:per\s+)?il\s+(?:giorno\s+)?(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})',
                r'(?:si\s+terrà|fissata?|prevista?)\s+(?:per\s+)?il\s+(?:giorno\s+)?(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})',
                r'(?:il\s+giorno|in\s+data)\s+(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})\s+(?:alle\s+ore)',
                r'(?:giorno|data)\s+(?:giovedì|venerdì|lunedì|martedì|mercoledì|sabato|domenica)?\s*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})',
            ]

            # Anno corrente per date senza anno
            from datetime import datetime
            current_year = datetime.now().year

            best_date = None

            # PRIORITÀ 1: Date testuali con anno esplicito (es: "4 dicembre 2025")
            for pattern in textual_date_with_year_patterns:
                match = re.search(pattern, testo, re.IGNORECASE)
                if match:
                    day = match.group(1).zfill(2)
                    month = MESI_MAP.get(match.group(2).lower(), match.group(2))
                    year = match.group(3)
                    best_date = f"{day}/{month}/{year}"
                    logger.debug(f"📅 Data testuale con anno: {best_date}")
                    break

            # PRIORITÀ 2: Date testuali SENZA anno (assume anno corrente)
            if not best_date:
                for pattern in textual_date_no_year_patterns:
                    match = re.search(pattern, testo, re.IGNORECASE)
                    if match:
                        day = match.group(1).zfill(2)
                        month = MESI_MAP.get(match.group(2).lower(), match.group(2))
                        best_date = f"{day}/{month}/{current_year}"
                        logger.debug(f"📅 Data testuale senza anno, assumo {current_year}: {best_date}")
                        break

            # PRIORITÀ 3: Date numeriche con contesto convocazione
            if not best_date:
                for pattern in convocation_date_patterns:
                    match = re.search(pattern, testo, re.IGNORECASE)
                    if match:
                        best_date = match.group(1)
                        logger.debug(f"📅 Data numerica con contesto: {best_date}")
                        break

            # PRIORITÀ 4: Date numeriche generiche (escludendo PEC headers)
            if not best_date:
                # Pattern per escludere: "Il giorno DD/MM/YYYY alle ore HH:MM:SS" (formato PEC)
                pec_header_pattern = r'Il\s+giorno\s+\d{1,2}/\d{1,2}/\d{4}\s+alle\s+ore\s+\d{1,2}:\d{2}:\d{2}'
                # Rimuovi temporaneamente gli header PEC
                testo_clean = re.sub(pec_header_pattern, '[PEC_TIMESTAMP]', testo, flags=re.IGNORECASE)

                date_pattern = r'\b(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})\b'
                dates = re.findall(date_pattern, testo_clean)
                if dates:
                    best_date = dates[0]
                    logger.debug(f"📅 Data numerica generica: {best_date}")

            if best_date:
                result['data_inizio'] = best_date

            # Orari - con gestione PEC headers
            # PRIORITÀ 1: Orari con contesto convocazione
            time_context_patterns = [
                r'alle\s+ore\s+(\d{1,2})[:\.](\d{2})(?:[^:0-9]|$)',  # "alle ore 10:00" ma non "10:00:58"
                r'ore\s+(\d{1,2})[:\.](\d{2})(?:[^:0-9]|$)',          # "ore 15:00" ma non "15:00:58"
                r'orario[:\s]+(\d{1,2})[:\.](\d{2})',                  # "orario: 09:30"
            ]

            best_time = None
            for pattern in time_context_patterns:
                match = re.search(pattern, testo, re.IGNORECASE)
                if match:
                    h, m = match.groups()
                    h_int = int(h)
                    m_int = int(m)
                    # Valida orario
                    if 0 <= h_int <= 23 and 0 <= m_int <= 59:
                        best_time = f"{h_int:02d}:{m_int:02d}"
                        break

            # PRIORITÀ 2: Fallback a pattern generico (ma esclude PEC timestamps con secondi)
            if not best_time:
                time_pattern = r'\bore\s+(\d{1,2})[:\.]?(\d{0,2})\b'
                for match in re.finditer(time_pattern, testo, re.IGNORECASE):
                    h = match.group(1)
                    m = match.group(2) or '00'
                    h_int = int(h)
                    m_int = int(m) if m else 0
                    if 6 <= h_int <= 22 and 0 <= m_int <= 59:  # Orari plausibili
                        best_time = f"{h_int:02d}:{m_int:02d}"
                        break

            if best_time:
                result['ora_inizio'] = best_time

            # Luogo
            luogo_patterns = [
                r'presso\s+(.+?)(?:\.|,|\n|$)',
                r'aula\s+(\w+(?:\s+\w+)?)',
                r'sala\s+(\w+(?:\s+\w+)?)'
            ]
            for pattern in luogo_patterns:
                match = re.search(pattern, testo, re.IGNORECASE)
                if match:
                    result['luogo'] = match.group(1).strip()[:100]
                    break

            # Modalità
            if any(x in text_lower for x in ['online', 'videoconferenza', 'teams', 'meet', 'zoom', 'da remoto']):
                result['modalita'] = 'online'
            elif any(x in text_lower for x in ['presenza', 'di persona', 'in sede']):
                result['modalita'] = 'presenza'
            elif any(x in text_lower for x in ['mista', 'ibrida']):
                result['modalita'] = 'mista'

            # Tipo riunione
            if 'collegio' in text_lower and 'docenti' in text_lower:
                result['tipo_riunione'] = 'collegio_docenti'
            elif 'consiglio' in text_lower and 'istituto' in text_lower:
                result['tipo_riunione'] = 'consiglio_istituto'
            elif 'consiglio' in text_lower and 'classe' in text_lower:
                result['tipo_riunione'] = 'consiglio_classe'
            elif 'assemblea' in text_lower and 'sindacale' in text_lower:
                result['tipo_riunione'] = 'assemblea_sindacale'
            elif 'rsu' in text_lower:
                result['tipo_riunione'] = 'rsu'
            elif 'convocazione' in text_lower:
                result['tipo_riunione'] = 'convocazione'

        else:  # interpello
            # Classe di concorso
            cc_pattern = r'\b([A-Z]{1,4}[-\s]?\d{1,3})\b'
            cc_matches = re.findall(cc_pattern, testo)
            # Filtra solo classi concorso valide
            valid_cc = [c for c in cc_matches if re.match(r'^[A-Z]{1,2}[-\s]?\d{2,3}$', c)]
            if valid_cc:
                result['classe_concorso'] = self._normalize_classe_concorso(valid_cc[0])

            # Ore settimanali
            ore_pattern = r'\b(\d{1,2})\s*(?:ore|h|ore\s*settimanali)\b'
            ore_match = re.search(ore_pattern, testo, re.IGNORECASE)
            if ore_match:
                ore = int(ore_match.group(1))
                if 1 <= ore <= 36:
                    result['ore_settimanali'] = ore

            # Meccanografico
            mecca_pattern = r'\b([A-Z]{2}[A-Z]{2}\d{5,6}[A-Z]?)\b'
            mecca_matches = re.findall(mecca_pattern, testo)
            if mecca_matches:
                result['meccanografico'] = mecca_matches[0]
                # Estrai provincia dal codice
                result['provincia'] = mecca_matches[0][:2]

            # Data scadenza
            scadenza_context = r'(?:scadenza|entro|termine)[:\s]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})'
            scadenza_match = re.search(scadenza_context, testo, re.IGNORECASE)
            if scadenza_match:
                result['data_scadenza'] = scadenza_match.group(1)

        # Comuni a entrambi
        # Email
        email_pattern = r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b'
        emails = re.findall(email_pattern, testo)
        if emails:
            # Preferisci email istituzionali
            for e in emails:
                if any(x in e.lower() for x in ['istruzione', 'scuola', 'gov']):
                    result['email_contatto' if tipo == 'interpello' else 'contatto_email'] = e
                    break
            if not result.get('email_contatto') and not result.get('contatto_email'):
                result['email_contatto' if tipo == 'interpello' else 'contatto_email'] = emails[0]

        # Telefono
        phone_pattern = r'\b((?:\+39\s?)?(?:0\d{1,4}[\s\-]?\d{5,8}|\d{3}[\s\-]?\d{6,7}))\b'
        phones = re.findall(phone_pattern, testo)
        if phones:
            result['telefono_contatto' if tipo == 'interpello' else 'contatto_telefono'] = phones[0]

        return result

    def _extract_with_nlp(self, testo: str, tipo: str) -> Dict[str, Any]:
        """Estrazione con NLP (spaCy + BERT)."""
        nlp = self._get_nlp_extractor()

        if tipo == "calendario":
            return nlp.extract_calendar_event(testo)
        else:
            return nlp.extract_for_interpello(testo)

    def _extract_with_ollama(self, testo: str, tipo: str, current_result: Dict) -> Dict[str, Any]:
        """Estrazione con LLM locale (Ollama) usando la coda."""
        # Costruisci prompt con campi mancanti
        missing_fields = [k for k, v in current_result.items()
                        if v is None and not k.startswith('_')]

        if not missing_fields:
            return {}

        # TRONCAMENTO INTELLIGENTE - usa preprocessor
        # Limita a ~2500 chars per lasciare spazio al prompt template
        processed_text = preprocess_for_llm(testo, tipo=tipo, provider="ollama")
        # Ulteriore troncamento per sicurezza
        if len(processed_text) > 2500:
            processed_text, _ = smart_truncate(processed_text, max_chars=2500, tipo=tipo)

        if tipo == "calendario":
            prompt = f"""Analizza questo testo di una convocazione/riunione ed estrai SOLO i seguenti campi mancanti:
{', '.join(missing_fields)}

TESTO:
{processed_text}

Rispondi SOLO in JSON valido con i campi trovati. Esempio:
{{"data_inizio": "04/12/2025", "ora_inizio": "10:00"}}

Se non trovi un campo, non includerlo nel JSON."""
        else:
            prompt = f"""Analizza questo testo di un interpello scolastico ed estrai SOLO i seguenti campi mancanti:
{', '.join(missing_fields)}

TESTO:
{processed_text}

Rispondi SOLO in JSON valido con i campi trovati. Esempio:
{{"classe_concorso": "A-26", "ore_settimanali": 18}}

Se non trovi un campo, non includerlo nel JSON."""

        result = self._call_llm(
            prompt=prompt,
            model_type="interpretation",
            format_json=True,
            timeout=120,  # Timeout ridotto grazie al testo più corto
            request_tipo=f"extraction_{tipo}"
        )

        return result if result else {}

    def _extract_with_chatgpt(self, testo: str, tipo: str, current_result: Dict) -> Dict[str, Any]:
        """Estrazione con ChatGPT (OpenAI)."""
        try:
            from app.integrations.openai_client import OpenAIClient
            client = OpenAIClient()

            # TRONCAMENTO INTELLIGENTE per ChatGPT (più generoso, ha context window maggiore)
            processed_text = preprocess_for_llm(testo, tipo=tipo, provider="openai")
            if len(processed_text) > 6000:
                processed_text, _ = smart_truncate(processed_text, max_chars=6000, tipo=tipo)

            if tipo == "calendario":
                prompt = f"""Analizza questo testo di una convocazione/riunione scolastica ed estrai le seguenti informazioni in formato JSON:
- data_inizio: data dell'evento (formato DD/MM/YYYY)
- ora_inizio: orario inizio (formato HH:MM)
- luogo: dove si svolge
- scuola_nome: nome della scuola
- scuola_codice: codice meccanografico (es. TAIC824001)
- modalita: "presenza", "online" o "mista"
- tipo_riunione: tipo di riunione (es. "collegio_docenti", "consiglio_istituto")
- motivo: argomento/ordine del giorno

TESTO:
{processed_text}

Rispondi SOLO con JSON valido."""
            else:
                prompt = f"""Analizza questo testo di un interpello scolastico ed estrai le seguenti informazioni in formato JSON:
- classe_concorso: classe di concorso (es. "A-26", "ADSS")
- ore_settimanali: numero ore settimanali
- provincia: sigla provincia (es. "TA")
- citta: città
- istituto: nome scuola
- meccanografico: codice meccanografico (es. TAIC824001)
- email_contatto: email per candidatura
- telefono_contatto: telefono
- data_scadenza: data scadenza candidatura

TESTO:
{processed_text}

Rispondi SOLO con JSON valido."""

            response = client.extract_structured_data(prompt)
            if response and isinstance(response, dict):
                return response

        except Exception as e:
            logger.warning(f"ChatGPT extraction failed: {e}")

        return {}

    def _validate_with_llm(self, testo: str, tipo: str, result: Dict) -> Dict:
        """
        Validazione semantica e di contesto con LLM usando la coda.

        Verifica:
        - Coerenza dei dati estratti con il contesto
        - Plausibilità dei valori
        - Correzione errori evidenti
        """
        # Prepara dati estratti per validazione
        # Escludi campi interni/metadata che non servono per validazione
        excluded_fields = {'confidence_scores', 'all_entities', 'raw_entities', 'nlp_data', 'ner_results'}
        extracted_data = {k: v for k, v in result.items()
                         if v is not None and not k.startswith('_') and k not in excluded_fields}

        if not extracted_data:
            return result

        # TRONCAMENTO INTELLIGENTE per validazione
        # Per validazione serve meno testo perché confrontiamo solo con dati già estratti
        processed_text, _ = smart_truncate(testo, max_chars=1500, tipo=tipo)

        if tipo == "calendario":
            prompt = f"""Sei un validatore di dati estratti da email di convocazioni scolastiche.

DATI ESTRATTI:
{extracted_data}

TESTO ORIGINALE:
{processed_text}

VERIFICA:
1. I dati estratti sono coerenti con il testo?
2. Le date e orari sono plausibili?
3. Il luogo corrisponde a quanto scritto?
4. Il tipo riunione è corretto?

Rispondi in JSON con:
- "valid": true/false (i dati sono corretti)
- "corrections": {{}} (campi da correggere con valori giusti)
- "confidence_adjustments": {{}} (aggiustamenti confidence per campo)
- "notes": "eventuali note"

Esempio: {{"valid": true, "corrections": {{}}, "confidence_adjustments": {{"data_inizio": 0.95}}, "notes": ""}}
Se un dato è sbagliato: {{"valid": false, "corrections": {{"luogo": "Aula Magna"}}, "confidence_adjustments": {{}}, "notes": "luogo corretto"}}"""
        else:
            prompt = f"""Sei un validatore di dati estratti da interpelli scolastici.

DATI ESTRATTI:
{extracted_data}

TESTO ORIGINALE:
{processed_text}

VERIFICA:
1. La classe di concorso è valida (formato corretto, es. A-26)?
2. Il codice meccanografico è valido (formato: 2 lettere provincia + 2 lettere tipo + 5-6 cifre + eventuale lettera)?
3. Le ore settimanali sono plausibili (1-36)?
4. La provincia corrisponde al meccanografico?

Rispondi in JSON con:
- "valid": true/false
- "corrections": {{}}
- "confidence_adjustments": {{}}
- "notes": ""

Esempio correzione classe concorso errata: {{"valid": false, "corrections": {{"classe_concorso": "A-26"}}, "confidence_adjustments": {{}}, "notes": "formato corretto"}}"""

        # Usa la coda LLM per la validazione
        response = self._call_llm(
            prompt=prompt,
            model_type="validation",
            format_json=True,
            timeout=120,  # Timeout aumentato per server lenti
            request_tipo=f"validation_{tipo}"
        )

        if response and isinstance(response, dict):
            corrections_count = 0

            # Applica correzioni
            if response.get('corrections'):
                for field, correct_value in response['corrections'].items():
                    if field in result and correct_value:
                        old_value = result[field]
                        result[field] = correct_value
                        result['_sources'][field] = 'llm_validation'
                        logger.info(f"🔧 Corretto {field}: '{old_value}' -> '{correct_value}'")
                        corrections_count += 1

            # Applica aggiustamenti confidence
            if response.get('confidence_adjustments'):
                for field, adj in response['confidence_adjustments'].items():
                    if field in result:
                        result['_confidence_scores'][field] = adj

            result['_validation_corrections'] = corrections_count
            result['_validation_notes'] = response.get('notes', '')
            result['_validated'] = True

        return result

    def _merge_results(self, base: Dict, new: Dict, source: str = None) -> Dict:
        """Merge risultati, nuovi valori sovrascrivono solo se base è None."""
        for key, value in new.items():
            if key.startswith('_'):
                continue
            if value is not None and base.get(key) is None:
                # Normalizza classe_concorso da qualsiasi fonte
                if key == 'classe_concorso' and value:
                    value = self._normalize_classe_concorso(value)
                base[key] = value
                if source:
                    base['_sources'][key] = source
                # Copia confidence se disponibile
                if 'confidence_scores' in new and key in new.get('confidence_scores', {}):
                    base['_confidence_scores'][key] = new['confidence_scores'][key]
                elif '_confidence_scores' in new and key in new.get('_confidence_scores', {}):
                    base['_confidence_scores'][key] = new['_confidence_scores'][key]
        return base

    def _count_fields(self, result: Dict) -> int:
        """Conta campi non nulli."""
        return sum(1 for k, v in result.items() if v is not None and not k.startswith('_'))

    def _calculate_completeness(self, result: Dict, tipo: str) -> float:
        """Calcola completezza (0-1) basata sui campi essenziali."""
        if tipo == "calendario":
            essential = ['data_inizio', 'ora_inizio', 'luogo']
            important = ['scuola_nome', 'modalita', 'tipo_riunione']
        else:
            essential = ['classe_concorso', 'provincia']
            important = ['istituto', 'meccanografico', 'ore_settimanali']

        essential_found = sum(1 for f in essential if result.get(f))
        important_found = sum(1 for f in important if result.get(f))

        # Essential pesano di più
        essential_score = essential_found / len(essential) if essential else 0
        important_score = important_found / len(important) if important else 0

        return essential_score * 0.7 + important_score * 0.3

    def _calculate_confidence(self, result: Dict) -> float:
        """Calcola confidence complessiva."""
        scores = result.get('_confidence_scores', {})
        if scores:
            return sum(scores.values()) / len(scores)

        # Fallback: basato su source
        sources = result.get('_sources', {})
        source_weights = {'regex': 0.7, 'nlp': 0.8, 'ollama': 0.75, 'chatgpt': 0.9}

        if sources:
            weights = [source_weights.get(s, 0.5) for s in sources.values()]
            return sum(weights) / len(weights)

        return 0.5

    def _sanity_check_calendario(self, result: Dict) -> Dict:
        """
        Sanity check per dati calendario estratti.

        Verifica:
        1. Data nel futuro o max 7 giorni nel passato
        2. Ora in range ragionevole (6:00-22:00)
        3. Luogo non troppo lungo o con pattern assurdi
        4. Invalida campi con dati garbage

        Args:
            result: Risultato estrazione calendario

        Returns:
            Dict con campi invalidati se garbage
        """
        issues = []
        now = datetime.now()

        # 1. Valida data_inizio
        data_inizio = result.get('data_inizio')
        if data_inizio:
            try:
                # Prova a parsare la data
                parsed_date = None
                for fmt in ['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d', '%d %B %Y', '%d %b %Y']:
                    try:
                        parsed_date = datetime.strptime(data_inizio.strip(), fmt)
                        break
                    except ValueError:
                        continue

                if parsed_date:
                    # Data troppo nel passato (>30 giorni) → garbage
                    if parsed_date < now - timedelta(days=30):
                        logger.warning(f"⚠️ Sanity check: data_inizio troppo vecchia ({data_inizio})")
                        result['data_inizio'] = None
                        result['_sanity_issues'] = result.get('_sanity_issues', []) + ['data_vecchia']
                        issues.append('data_vecchia')
                    # Data troppo nel futuro (>2 anni) → sospetta
                    elif parsed_date > now + timedelta(days=730):
                        logger.warning(f"⚠️ Sanity check: data_inizio troppo futura ({data_inizio})")
                        result['data_inizio'] = None
                        result['_sanity_issues'] = result.get('_sanity_issues', []) + ['data_futura']
                        issues.append('data_futura')
            except Exception as e:
                logger.warning(f"⚠️ Sanity check: errore parsing data_inizio: {e}")

        # 2. Valida ora_inizio
        ora_inizio = result.get('ora_inizio')
        if ora_inizio:
            try:
                # Estrai ore:minuti
                time_match = re.search(r'(\d{1,2})[:\.](\d{2})', str(ora_inizio))
                if time_match:
                    hour = int(time_match.group(1))
                    # Ora fuori range lavorativo (6-22) → sospetta
                    if hour < 6 or hour > 22:
                        logger.warning(f"⚠️ Sanity check: ora_inizio fuori range ({ora_inizio})")
                        result['ora_inizio'] = None
                        result['_sanity_issues'] = result.get('_sanity_issues', []) + ['ora_invalida']
                        issues.append('ora_invalida')
            except Exception as e:
                logger.warning(f"⚠️ Sanity check: errore parsing ora_inizio: {e}")

        # 3. Valida luogo
        luogo = result.get('luogo')
        if luogo:
            # Luogo troppo lungo (>200 caratteri) → probabilmente garbage
            if len(luogo) > 200:
                logger.warning(f"⚠️ Sanity check: luogo troppo lungo ({len(luogo)} chars)")
                result['luogo'] = None
                result['_sanity_issues'] = result.get('_sanity_issues', []) + ['luogo_lungo']
                issues.append('luogo_lungo')
            # Luogo senza spazi (parole concatenate) → garbage
            elif len(luogo) > 30 and ' ' not in luogo:
                logger.warning(f"⚠️ Sanity check: luogo senza spazi ({luogo[:50]}...)")
                result['luogo'] = None
                result['_sanity_issues'] = result.get('_sanity_issues', []) + ['luogo_concatenato']
                issues.append('luogo_concatenato')

        # 4. Valida scuola_nome
        scuola = result.get('scuola_nome')
        if scuola:
            # Nome scuola senza spazi e >20 caratteri → garbage
            if len(scuola) > 20 and ' ' not in scuola:
                logger.warning(f"⚠️ Sanity check: scuola_nome senza spazi ({scuola[:50]}...)")
                result['scuola_nome'] = None
                result['_sanity_issues'] = result.get('_sanity_issues', []) + ['scuola_concatenata']
                issues.append('scuola_concatenata')

        # Log risultato sanity check
        if issues:
            logger.info(f"🔍 Sanity check completato: {len(issues)} problemi trovati: {issues}")
            result['_sanity_passed'] = False
        else:
            result['_sanity_passed'] = True

        return result


# Singleton
_unified_extractor: Optional[UnifiedExtractor] = None


def get_unified_extractor() -> UnifiedExtractor:
    """Ottiene istanza singleton dell'estrattore unificato."""
    global _unified_extractor
    if _unified_extractor is None:
        _unified_extractor = UnifiedExtractor()
    return _unified_extractor
