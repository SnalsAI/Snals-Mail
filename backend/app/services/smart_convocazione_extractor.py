"""
Smart Convocazione Extractor - Strategia ibrida per estrazione dati convocazioni
Strategia: Regex → Validazione LLM locale → LLM estrazione completa → OpenAI (se necessario)

Campi estratti per alimentare calendario:
- data_convocazione (QUANDO)
- ora_convocazione (QUANDO)
- luogo (DOVE)
- sede (DOVE - più specifico)
- convocante (CHI)
- motivo (PERCHÉ)
- oggetto_riunione (PERCHÉ - più dettagliato)
"""
import logging
import re
from typing import Dict, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class RegexConvocazioneExtractor:
    """Estrattore regex per convocazioni - veloce per dati strutturati"""

    # Mappa mesi testuali → numero
    MESI = {
        'gennaio': 1, 'febbraio': 2, 'marzo': 3, 'aprile': 4,
        'maggio': 5, 'giugno': 6, 'luglio': 7, 'agosto': 8,
        'settembre': 9, 'ottobre': 10, 'novembre': 11, 'dicembre': 12
    }

    # Pattern data TESTUALE (PRIORITÀ ALTA per convocazioni)
    # Cerca: "28 novembre 2025", "nel giorno 28 novembre 2025", "il 15 dicembre 2025"
    DATA_PATTERN_TEXTUAL = re.compile(
        r'(?:il|nel\s+giorno|giorno|data|convocazione\s+(?:per\s+)?il)?\s*(\d{1,2})\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+(\d{4})',
        re.IGNORECASE
    )

    # Pattern data convocazione NUMERICA (fallback)
    # Cerca: "il 28/11/2025", "data 28.11.2025", "Venerdì 28.11.2025", o standalone "28.11.2025"
    DATA_PATTERN = re.compile(
        r'(?:il|data|giorno|convocazione per il|lunedì|martedì|mercoledì|giovedì|venerdì|sabato|domenica)?\s*(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2,4})',
        re.IGNORECASE
    )

    # Pattern ora CON CONTESTO (più affidabile per convocazioni)
    # Cerca: "ore 09:00", "alle 14:30", "h. 15:00", "alle ore 11:00"
    # Richiede parole chiave di contesto per evitare timestamp casuali
    ORA_PATTERN_STRONG = re.compile(
        r'(?:alle\s+ore|ore|orario|h\.|alle)\s+(\d{1,2})[:\.](\d{2})',
        re.IGNORECASE
    )

    # Pattern ora standalone (fallback)
    # Trova tutti gli orari, poi filtra quelli nei contesti sbagliati
    ORA_PATTERN_WEAK = re.compile(
        r'\b(\d{1,2})[:\.](\d{2})\b',
        re.IGNORECASE
    )

    # Pattern per contesti da escludere (timestamp, protocolli, date)
    ORA_EXCLUDE_CONTEXTS = [
        r'del\s+\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}[:\.]\d{2}',  # "del 20/11/2025 10:26"
        r'Prot\.\s+\d+[A-Z/]*\s+del\s+\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}[:\.]\d{2}',  # "Prot. 123 del 20/11/2025 10:26"
    ]

    # Pattern per escludere date da riferimenti normativi (CCNL, leggi, decreti, articoli)
    # Questi pattern identificano date che NON sono date di convocazione ma riferimenti a normative
    DATA_EXCLUDE_CONTEXTS = [
        r'CCNL\s+\d{1,2}[/\.\-]\d{1,2}[/\.\-]\d{2,4}',  # "CCNL 18.01.2024", "CCNL 18/01/2024"
        r'art\.?\s*\d+[^,\n]*CCNL\s+\d{1,2}[/\.\-]\d{1,2}[/\.\-]\d{2,4}',  # "art. 57 CCNL 18.01.2024"
        r'd\.?\s*lgs\.?\s*n?\.?\s*\d+[^,\n]*\d{1,2}[/\.\-]\d{1,2}[/\.\-]\d{2,4}',  # "d.lgs. n. 165 del 18/01/2024"
        r'legge\s+n?\.?\s*\d+[^,\n]*\d{1,2}[/\.\-]\d{1,2}[/\.\-]\d{2,4}',  # "legge n. 104 del 18/01/2024"
        r'decreto\s+[^,\n]*\d{1,2}[/\.\-]\d{1,2}[/\.\-]\d{2,4}',  # "decreto del 18/01/2024"
        r'DPR\s+[^,\n]*\d{1,2}[/\.\-]\d{1,2}[/\.\-]\d{2,4}',  # "DPR 18/01/2024"
    ]

    # Pattern luogo/sede
    LUOGO_PATTERN = re.compile(
        r'(?:presso|luogo|sede|sala)\s+([A-Z][a-z\s,]+?)(?:\.|,|\n)',
        re.IGNORECASE
    )

    # Pattern via/indirizzo
    INDIRIZZO_PATTERN = re.compile(
        r'(?:via|viale|piazza|corso)\s+([A-Z][a-z\s,]+?)(?:\d+|,|\n)',
        re.IGNORECASE
    )

    # Pattern oggetto riunione
    OGGETTO_PATTERN = re.compile(
        r'(?:oggetto|riguardo|per|tema|argomento)[\s:]+([^\n]{10,100})',
        re.IGNORECASE
    )

    def extract(self, testo: str, mittente: str = None) -> Optional[Dict[str, Any]]:
        """Estrae dati convocazione con regex"""
        try:
            dati = {}

            # Estrai data - PRIMA prova formato testuale (priorità alta)
            data_match_textual = self.DATA_PATTERN_TEXTUAL.search(testo)
            if data_match_textual:
                giorno_str, mese_str, anno_str = data_match_textual.groups()
                mese_num = self.MESI.get(mese_str.lower())
                if mese_num:
                    try:
                        data = datetime(int(anno_str), mese_num, int(giorno_str))
                        dati['data_convocazione'] = data.date().isoformat()
                        logger.info(f"✅ Regex trovato data_convocazione (testuale): {dati['data_convocazione']} ({giorno_str} {mese_str} {anno_str})")
                    except ValueError:
                        pass

            # Se non trovata con formato testuale, prova formato numerico
            if 'data_convocazione' not in dati:
                # Cerca tutte le date e filtra quelle in contesti normativi
                for data_match in self.DATA_PATTERN.finditer(testo):
                    giorno, mese, anno = data_match.groups()
                    if len(anno) == 2:
                        anno = f"20{anno}"

                    # Controlla se la data è in un contesto normativo (CCNL, legge, decreto, ecc.)
                    data_str = data_match.group(0)
                    match_start = data_match.start()
                    # Prendi il contesto: 50 caratteri prima della data
                    context_start = max(0, match_start - 50)
                    context = testo[context_start:match_start + len(data_str)]

                    is_normative_ref = False
                    for exclude_pattern in self.DATA_EXCLUDE_CONTEXTS:
                        if re.search(exclude_pattern, context, re.IGNORECASE):
                            logger.debug(f"⏭️ Ignorata data {data_str} - riferimento normativo (contesto: ...{context[-30:]})")
                            is_normative_ref = True
                            break

                    if is_normative_ref:
                        continue  # Skip questa data e prova la prossima

                    try:
                        data = datetime(int(anno), int(mese), int(giorno))
                        dati['data_convocazione'] = data.date().isoformat()
                        logger.info(f"✅ Regex trovato data_convocazione (numerica): {dati['data_convocazione']}")
                        break  # Usa la prima data valida non-normativa
                    except ValueError:
                        pass

            # Estrai ora - Priorità a pattern con contesto forte
            ora_match = self.ORA_PATTERN_STRONG.search(testo)
            if ora_match:
                ora, minuti = ora_match.groups()
                # Valida che ora e minuti siano nel range corretto
                try:
                    ora_int = int(ora)
                    minuti_int = int(minuti)
                    if ora_int <= 23 and minuti_int <= 59:
                        dati['ora_convocazione'] = f"{ora_int:02d}:{minuti_int:02d}"
                        logger.info(f"✅ Regex trovato ora_convocazione (strong): {dati['ora_convocazione']}")
                    else:
                        logger.debug(f"⏭️ Ignorato orario strong {ora}:{minuti} - valori fuori range")
                        ora_match = None  # Forza fallback a weak pattern
                except ValueError:
                    ora_match = None
            else:
                # Fallback a pattern debole - trova tutti e filtra contesti da escludere
                for ora_match in self.ORA_PATTERN_WEAK.finditer(testo):
                    ora, minuti = ora_match.groups()
                    ora_str = ora_match.group(0)

                    # Valida che ora e minuti siano nel range corretto
                    try:
                        ora_int = int(ora)
                        minuti_int = int(minuti)
                        if ora_int > 23 or minuti_int > 59:
                            logger.debug(f"⏭️ Ignorato orario {ora_str} - valori fuori range (ora > 23 o minuti > 59)")
                            continue
                    except ValueError:
                        continue

                    # Verifica se l'ora è in un contesto da escludere
                    in_bad_context = False
                    for exclude_pattern in self.ORA_EXCLUDE_CONTEXTS:
                        if re.search(exclude_pattern, testo[max(0, ora_match.start()-50):ora_match.end()+10], re.IGNORECASE):
                            logger.debug(f"⏭️ Ignorato orario {ora_str} - contesto timestamp/protocollo")
                            in_bad_context = True
                            break

                    if not in_bad_context:
                        dati['ora_convocazione'] = f"{ora_int:02d}:{minuti_int:02d}"
                        logger.info(f"✅ Regex trovato ora_convocazione (weak, filtrato): {dati['ora_convocazione']}")
                        break  # Usa il primo orario valido trovato

            # Estrai luogo
            luogo_match = self.LUOGO_PATTERN.search(testo)
            if luogo_match:
                luogo = luogo_match.group(1).strip()
                dati['sede'] = luogo
                logger.info(f"✅ Regex trovato sede: {dati['sede']}")

            # Estrai indirizzo
            indirizzo_match = self.INDIRIZZO_PATTERN.search(testo)
            if indirizzo_match:
                via = indirizzo_match.group(0).strip()
                dati['luogo'] = via
                logger.info(f"✅ Regex trovato luogo: {dati['luogo']}")

            # Estrai oggetto
            oggetto_match = self.OGGETTO_PATTERN.search(testo)
            if oggetto_match:
                oggetto = oggetto_match.group(1).strip()
                dati['oggetto_riunione'] = oggetto
                logger.info(f"✅ Regex trovato oggetto_riunione: {dati['oggetto_riunione']}")

            # Convocante dal mittente
            if mittente:
                dati['convocante'] = mittente
                logger.info(f"✅ Convocante dal mittente: {dati['convocante']}")

            # Ritorna dati solo se abbiamo almeno data O ora
            if 'data_convocazione' in dati or 'ora_convocazione' in dati:
                logger.info(f"✅ Regex extraction completata: {len(dati)} campi estratti")
                return dati
            else:
                logger.warning("⚠️ Regex: nessuna data/ora trovata")
                return None

        except Exception as e:
            logger.error(f"❌ Errore Regex extraction convocazione: {e}")
            return None


class ConvocazioneValidator:
    """Validatore LLM locale per dati convocazione"""

    def __init__(self, llm_client=None):
        if llm_client:
            self.llm_client = llm_client
        else:
            try:
                from app.integrations.llm_client import LLMClient
                self.llm_client = LLMClient()
            except Exception as e:
                logger.warning(f"LLM locale non disponibile: {e}")
                self.llm_client = None

    def validate_extracted_data(
        self,
        dati_regex: Dict[str, Any],
        testo_originale: str,
        timeout: float = 45.0  # Usa modello veloce (1b) - 45s per safety
    ) -> Dict[str, Any]:
        """Valida dati convocazione estratti da regex"""
        if not self.llm_client:
            logger.warning("⚠️ LLM non disponibile, skip validazione")
            return {
                'is_valid': True,
                'confidence': 0.7,
                'skipped': True,
                'reason': 'llm_not_available'
            }

        if not dati_regex:
            return {
                'is_valid': False,
                'confidence': 0.0,
                'reason': 'no_data_to_validate'
            }

        start_time = datetime.now()

        # Formatta campi estratti
        campi_estratti = "\n".join([
            f"- {campo}: {valore}"
            for campo, valore in dati_regex.items()
        ])

        prompt = f"""Sei un esperto validatore di convocazioni scolastiche/sindacali italiane.

COMPITO: Valida l'accuratezza dei seguenti dati estratti da una convocazione.

DATI ESTRATTI DA VALIDARE:
{campi_estratti}

TESTO ORIGINALE COMPLETO:
{testo_originale[:2000]}

ISTRUZIONI DI VALIDAZIONE:
Per ogni campo, analizza attentamente:

1. **PRESENZA NEL TESTO**: Il dato è menzionato nel testo originale?
2. **CORRETTEZZA VALORE**: Il valore estratto corrisponde esattamente a quello nel testo?
3. **FORMATO VALIDO**: Il formato è corretto per quel tipo di dato?
4. **COERENZA SEMANTICA**: Il dato ha senso nel contesto di una convocazione?

CRITERI SPECIFICI:
- data_convocazione:
  * Formato YYYY-MM-DD
  * Data futura plausibile (tipicamente entro 30 giorni)
  * Deve essere esplicitamente menzionata nel testo

- ora_convocazione:
  * Formato HH:MM
  * Orario lavorativo plausibile (tipicamente 08:00-20:00)
  * Deve essere esplicitamente menzionata

- sede/luogo:
  * Nome completo o indirizzo
  * Deve essere menzionato nel testo
  * Non confondere con mittente o firmatario

- convocante:
  * Nome persona, ente o istituzione
  * Tipicamente dal mittente email o firma documento

- oggetto_riunione:
  * Descrizione chiara dello scopo
  * Deve riflettere il contenuto della convocazione

LIVELLI DI CONFIDENCE:
- 1.0: Certezza assoluta (dato trovato esattamente nel testo)
- 0.9: Molto sicuro (dato trovato con leggera variazione formato)
- 0.8: Sicuro (dato trovato ma richiede interpretazione)
- 0.7: Abbastanza sicuro (dato plausibile ma non esplicito)
- 0.5 o meno: Dubbioso o probabilmente errato

FORMATO RISPOSTA (solo JSON):
{{
  "field_validations": {{
    "data_convocazione": {{
      "valid": true/false,
      "confidence": 0.0-1.0,
      "reason": "spiegazione dettagliata"
    }},
    "ora_convocazione": {{
      "valid": true/false,
      "confidence": 0.0-1.0,
      "reason": "spiegazione dettagliata"
    }}
  }}
}}

IMPORTANTE: Sii rigoroso. È meglio segnalare un dato come incerto piuttosto che validare dati errati."""

        try:
            response = self.llm_client.generate(
                prompt=prompt,
                model_type="generation",  # llama3.2:1b - veloce per validazione
                format_json=True,
                max_tokens=300,  # Ridotto da 500
                temperature=0.1,
                timeout=timeout
            )

            validation_time = (datetime.now() - start_time).total_seconds() * 1000

            # Parse risposta JSON
            validation_result = self._parse_validation_response(response)

            if validation_result:
                # Calcola confidenza generale
                field_confidences = [
                    v.get('confidence', 0.5)
                    for v in validation_result.get('field_validations', {}).values()
                ]
                overall_confidence = sum(field_confidences) / len(field_confidences) if field_confidences else 0.5

                # Considera valido se tutti i campi critici sono validi
                all_valid = all(
                    v.get('valid', False)
                    for v in validation_result.get('field_validations', {}).values()
                )

                is_valid = all_valid and overall_confidence >= 0.75

                logger.info(
                    f"✅ Validazione completata: "
                    f"valid={is_valid}, confidence={overall_confidence:.2f}, "
                    f"time={validation_time:.0f}ms"
                )

                return {
                    'is_valid': is_valid,
                    'confidence': overall_confidence,
                    'field_validations': validation_result.get('field_validations', {}),
                    'validation_time_ms': validation_time,
                    'all_fields_valid': all_valid
                }
            else:
                logger.warning("⚠️ Impossibile parsare risposta validazione")
                return {
                    'is_valid': False,
                    'confidence': 0.3,
                    'validation_time_ms': validation_time,
                    'error': 'parse_failed'
                }

        except Exception as e:
            validation_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.error(f"❌ Errore validazione LLM: {e}")
            return {
                'is_valid': False,
                'confidence': 0.3,
                'validation_time_ms': validation_time,
                'error': str(e)
            }

    def _parse_validation_response(self, response: str) -> Optional[Dict]:
        """Parse risposta JSON da LLM"""
        try:
            import json
            # Prova parsing diretto
            return json.loads(response)
        except:
            # Prova a estrarre JSON da markdown
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
                try:
                    return json.loads(json_str)
                except:
                    pass

            # Prova a estrarre qualsiasi blocco JSON
            try:
                start = response.find('{')
                end = response.rfind('}') + 1
                if start >= 0 and end > start:
                    json_str = response[start:end]
                    return json.loads(json_str)
            except:
                pass

            logger.warning(f"Impossibile parsare validazione: {response[:200]}")
            return None


class SmartConvocazioneExtractor:
    """
    Estrattore intelligente per convocazioni con strategia a cascata:
    1. Regex (veloce, affidabile per dati strutturati)
    2. Validazione con LLM locale
    3. Estrazione completa LLM locale
    4. OpenAI come fallback finale

    Campi estratti:
    - data_convocazione (QUANDO)
    - ora_convocazione (QUANDO)
    - luogo (DOVE)
    - sede (DOVE)
    - convocante (CHI)
    - motivo (PERCHÉ)
    - oggetto_riunione (PERCHÉ)
    """

    # Campi richiesti per convocazioni (almeno uno per categoria)
    REQUIRED_CATEGORIES = {
        'QUANDO': ['data_convocazione', 'ora_convocazione'],
        'DOVE': ['luogo', 'sede'],
        'CHI': ['convocante'],
        'PERCHE': ['motivo', 'oggetto_riunione']
    }

    def __init__(self, openai_api_key: str = None, openai_model: str = "gpt-4o-mini"):
        """Inizializza estrattore smart convocazioni"""
        self.regex_extractor = RegexConvocazioneExtractor()
        self.validator = ConvocazioneValidator()

        # LLM locale per estrazione completa
        try:
            from app.integrations.llm_client import LLMClient
            self.llm_client = LLMClient()
        except Exception as e:
            logger.warning(f"LLM locale non disponibile: {e}")
            self.llm_client = None

        # OpenAI per fallback
        self.openai_client = None
        if openai_api_key:
            try:
                from openai import OpenAI
                self.openai_client = OpenAI(api_key=openai_api_key)
                self.openai_model = openai_model
            except Exception as e:
                logger.warning(f"OpenAI non disponibile: {e}")

        # Statistiche
        self.stats = {
            'regex_only': 0,
            'regex_validated': 0,
            'regex_local': 0,
            'openai_fallback': 0,
            'total': 0
        }

    def calculate_completeness(self, dati: Optional[Dict]) -> float:
        """
        Calcola completezza in base alle categorie.
        Ogni categoria vale 0.25 se ha almeno un campo.
        """
        if not dati:
            return 0.0

        score = 0.0
        for category, fields in self.REQUIRED_CATEGORIES.items():
            if any(dati.get(field) for field in fields):
                score += 0.25

        return score

    def validate_data_quality(self, dati: Dict) -> bool:
        """Valida qualità dati convocazione"""
        if not dati:
            return False

        # Deve avere almeno data O ora (categoria QUANDO)
        has_quando = any(dati.get(field) for field in self.REQUIRED_CATEGORIES['QUANDO'])
        if not has_quando:
            return False

        # Verifica formato data se presente
        if 'data_convocazione' in dati:
            try:
                datetime.fromisoformat(dati['data_convocazione'])
            except:
                return False

        # Verifica formato ora se presente
        if 'ora_convocazione' in dati:
            if not re.match(r'^\d{2}:\d{2}$', str(dati['ora_convocazione'])):
                return False

        return True

    def extract(self, testo: str, mittente: str = None) -> Optional[Dict[str, Any]]:
        """Estrae dati convocazione con strategia intelligente"""
        self.stats['total'] += 1
        start_time = datetime.now()

        metadata = {
            'timestamp': start_time.isoformat(),
            'strategies_used': [],
            'completeness_scores': {},
            'total_time_ms': 0
        }

        # ============================================================
        # STEP 1: REGEX (sempre, velocissimo)
        # ============================================================
        logger.info("📊 STEP 1: Estrazione convocazione con Regex")
        regex_start = datetime.now()

        dati_regex = self.regex_extractor.extract(testo, mittente)
        completeness_regex = self.calculate_completeness(dati_regex)

        regex_time = (datetime.now() - regex_start).total_seconds() * 1000
        metadata['strategies_used'].append('regex')
        metadata['completeness_scores']['regex'] = completeness_regex
        metadata['regex_time_ms'] = regex_time

        logger.info(f"✅ Regex completato: {completeness_regex:.0%} completo in {regex_time:.0f}ms")

        # IMPORTANTE: NON saltare validazione anche se completezza alta
        # Motivo: regex può estrarre date/ore sbagliate da testo (es. "VISTO il CCNL 18/01/2024" invece di data convocazione)
        # Validazione LLM verifica semanticamente che i dati estratti siano quelli corretti

        # Solo se completezza PERFETTA (100%) E qualità OK → usa regex senza validazione
        if completeness_regex >= 1.0 and self.validate_data_quality(dati_regex):
            metadata['strategy_final'] = 'regex_only'
            metadata['total_time_ms'] = regex_time
            self.stats['regex_only'] += 1

            logger.info(f"✅ Dati completi con regex ({completeness_regex:.0%})")

            if dati_regex:
                dati_regex['metadata_estrazione'] = metadata
            return dati_regex

        # ============================================================
        # STEP 2: VALIDAZIONE LLM LOCALE (se regex ha estratto qualcosa)
        # ============================================================
        if completeness_regex >= 0.25 and dati_regex:  # Almeno 1 categoria
            logger.info(f"📊 STEP 2: Validazione dati regex con LLM locale ({completeness_regex:.0%} completo)")
            validation_start = datetime.now()

            try:
                validation_result = self.validator.validate_extracted_data(
                    dati_regex=dati_regex,
                    testo_originale=testo,
                    timeout=45.0  # Usa llama3.2:1b (veloce) - 45s per safety
                )

                validation_time = (datetime.now() - validation_start).total_seconds() * 1000
                metadata['strategies_used'].append('regex_validation')
                metadata['validation_result'] = {
                    'is_valid': validation_result.get('is_valid', False),
                    'confidence': validation_result.get('confidence', 0),
                    'time_ms': validation_time
                }

                logger.info(
                    f"✅ Validazione completata: "
                    f"valid={validation_result.get('is_valid')}, "
                    f"confidence={validation_result.get('confidence', 0):.2f}, "
                    f"time={validation_time:.0f}ms"
                )

                # Se validazione OK → usa dati regex
                if validation_result.get('is_valid') and validation_result.get('confidence', 0) >= 0.85:
                    metadata['strategy_final'] = 'regex_validated'
                    metadata['total_time_ms'] = regex_time + validation_time
                    self.stats['regex_validated'] += 1

                    logger.info(f"✅ Dati regex validati da LLM (confidenza: {validation_result.get('confidence', 0):.2f})")

                    if dati_regex:
                        dati_regex['metadata_estrazione'] = metadata
                    return dati_regex

            except Exception as e:
                logger.warning(f"⚠️ Errore validazione: {e}")
                metadata['validation_error'] = str(e)

        # ============================================================
        # STEP 3: LLM LOCALE ESTRAZIONE COMPLETA
        # ============================================================
        if self.llm_client:
            logger.info(f"📊 STEP 3: Estrazione completa con LLM locale")
            local_start = datetime.now()

            try:
                dati_local = self._extract_with_local_llm(testo, mittente)

                # QUALITÀ: Mergi campi validati da regex
                if 'validation_result' in metadata and metadata['validation_result'].get('field_validations'):
                    valid_fields = metadata['validation_result'].get('field_validations', {})
                    for field, validation in valid_fields.items():
                        if validation.get('valid') and validation.get('confidence', 0) >= 0.85:
                            if field in dati_regex and (not dati_local or field not in dati_local or not dati_local[field]):
                                if not dati_local:
                                    dati_local = {}
                                dati_local[field] = dati_regex[field]
                                logger.info(f"📌 Mantenuto campo validato da regex: {field}={dati_regex[field]}")

                completeness_local = self.calculate_completeness(dati_local)

                local_time = (datetime.now() - local_start).total_seconds() * 1000
                metadata['strategies_used'].append('ollama_extraction')
                metadata['completeness_scores']['ollama'] = completeness_local
                metadata['ollama_time_ms'] = local_time

                logger.info(f"✅ LLM locale completato: {completeness_local:.0%} in {local_time:.0f}ms")

                # Se LLM locale ha estratto sufficientemente → usa locale
                if completeness_local >= 0.75 and self.validate_data_quality(dati_local):
                    metadata['strategy_final'] = 'ollama_extraction'
                    metadata['total_time_ms'] = regex_time + metadata.get('validation_result', {}).get('time_ms', 0) + local_time
                    self.stats['regex_local'] += 1

                    logger.info(f"✅ Dati completi con LLM locale ({completeness_local:.0%})")

                    if dati_local:
                        dati_local['metadata_estrazione'] = metadata
                    return dati_local

            except Exception as e:
                logger.warning(f"⚠️ LLM locale fallito: {e}")
                metadata['ollama_error'] = str(e)

        # ============================================================
        # STEP 4: OPENAI FALLBACK
        # ============================================================
        if self.openai_client:
            logger.info("📊 STEP 4: Fallback a OpenAI")
            openai_start = datetime.now()

            try:
                dati_openai = self._extract_with_openai(testo, mittente)
                completeness_openai = self.calculate_completeness(dati_openai)

                openai_time = (datetime.now() - openai_start).total_seconds() * 1000
                metadata['strategies_used'].append('openai')
                metadata['completeness_scores']['openai'] = completeness_openai
                metadata['openai_time_ms'] = openai_time
                metadata['strategy_final'] = 'openai_fallback'
                metadata['total_time_ms'] = regex_time + metadata.get('ollama_time_ms', 0) + openai_time
                self.stats['openai_fallback'] += 1

                logger.info(f"✅ OpenAI completato: {completeness_openai:.0%} in {openai_time:.0f}ms")

                if dati_openai:
                    dati_openai['metadata_estrazione'] = metadata
                return dati_openai

            except Exception as e:
                logger.error(f"❌ OpenAI fallito: {e}")
                metadata['openai_error'] = str(e)

        # ============================================================
        # FALLBACK FINALE: restituisci il migliore disponibile
        # ============================================================
        logger.warning("⚠️ Nessuna strategia ha prodotto risultati completi")

        best_data = dati_regex
        if self.llm_client and 'dati_local' in locals():
            if completeness_local > completeness_regex:
                best_data = dati_local
                metadata['strategy_final'] = 'best_effort_local'
            else:
                metadata['strategy_final'] = 'best_effort_regex'
        else:
            metadata['strategy_final'] = 'best_effort_regex'

        if best_data:
            best_data['metadata_estrazione'] = metadata

        return best_data

    def _extract_with_local_llm(self, testo: str, mittente: str = None) -> Optional[Dict[str, Any]]:
        """Estrae con LLM locale"""
        prompt = f"""Sei un esperto nell'estrarre dati da convocazioni scolastiche/sindacali italiane.

TESTO CONVOCAZIONE:
{testo[:3000]}

MITTENTE: {mittente or 'Non specificato'}

CAMPI DA ESTRARRE (solo se ESPLICITAMENTE presenti nel testo):

1. **data_convocazione**: formato "YYYY-MM-DD"
   - Cerca frasi come "fissata per...", "si terrà il...", "convocazione per il..."
   - NON usare la data dell'intestazione/protocollo (quella è la data di invio!)

2. **ora_convocazione**: formato "HH:MM"
   - Cerca "alle ore...", "h. ...", "orario: ..."
   - NON usare timestamp di protocolli/intestazioni

3. **luogo**: indirizzo completo SOLO se presente
   - Esempi VALIDI: "Via Roma 123", "Piazza Garibaldi 5, Taranto"
   - NON estrarre se trovi solo nomi di persone che sembrano indirizzi!
   - ATTENZIONE: "Lavia Grazia" è un NOME (cognome+nome), NON "via Grazia"!

4. **sede**: nome sede/sala/istituto (es: "Sala Conferenze", "Aula Magna", "I.C. Giovanni Cingolani")
   - NON confondere con liste di destinatari ("Ai Rappresentanti..." = destinatari, NON sede!)
   - Se non esplicita, lascia vuoto (NON inventare)

5. **convocante**: chi convoca (ente/dirigente/sindacato)

6. **oggetto_riunione**: scopo principale della convocazione

REGOLE CRITICHE:
- Se un campo NON è esplicitamente menzionato, NON inventarlo (ometti il campo)
- Distingui date di invio (nell'intestazione) da date di convocazione (nel corpo)
- NON confondere nomi propri con indirizzi
- NON usare liste di destinatari come sede

Rispondi SOLO con JSON valido (senza commenti):
{{"data_convocazione": "2025-11-26", "ora_convocazione": "09:00", ...}}"""

        try:
            response = self.llm_client.generate(
                prompt=prompt,
                model_type="interpretation",
                format_json=True,
                max_tokens=500,
                timeout=60.0
            )

            # Parse JSON
            import json
            dati = json.loads(response) if isinstance(response, str) else response

            return dati if dati else None

        except Exception as e:
            logger.error(f"Errore LLM locale: {e}")
            return None

    def _extract_with_openai(self, testo: str, mittente: str = None) -> Optional[Dict[str, Any]]:
        """Estrae con OpenAI"""
        import json

        prompt = f"""Estrai informazioni da questa convocazione scolastica/sindacale italiana per creare un evento calendario.

TESTO:
{testo[:3000]}

MITTENTE: {mittente or 'Non specificato'}

CAMPI DA ESTRARRE (solo se ESPLICITAMENTE presenti):

1. **data_convocazione**: formato "YYYY-MM-DD"
   - Cerca la data DELLA RIUNIONE, non quella dell'invio (es: "fissata per mercoledì 26 novembre 2025")
   - NON usare date nell'intestazione/protocollo

2. **ora_convocazione**: formato "HH:MM"
   - Cerca "alle ore...", "h. ...", "orario: ..."

3. **luogo**: indirizzo completo SOLO se presente esplicitamente
   - Esempi VALIDI: "Via Roma 123", "Piazza Garibaldi 5, Taranto"
   - ATTENZIONE: "Lavia Grazia" è un NOME DI PERSONA (cognome+nome), NON un indirizzo!
   - Se non c'è un indirizzo esplicito, ometti questo campo

4. **sede**: nome sede/sala/istituto
   - Esempi: "Sala Conferenze", "Aula Magna", "Istituto Comprensivo XYZ"
   - NON confondere con liste di destinatari ("Ai Rappresentanti..." sono destinatari, NON la sede!)

5. **convocante**: chi convoca (ente/dirigente)

6. **oggetto_riunione**: scopo della convocazione

REGOLE CRITICHE:
- Se un campo non è esplicitamente menzionato, omettilo dal JSON
- Distingui date di invio da date di convocazione
- NON confondere nomi propri con indirizzi
- NON usare liste di destinatari come sede

Rispondi SOLO con JSON valido."""

        try:
            response = self.openai_client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": "Sei un assistente che estrae dati da convocazioni italiane."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500,
                response_format={"type": "json_object"}
            )

            result_text = response.choices[0].message.content
            dati = json.loads(result_text)

            return dati if dati else None

        except Exception as e:
            logger.error(f"Errore OpenAI: {e}")
            return None

    def get_stats(self) -> Dict[str, Any]:
        """Ritorna statistiche di utilizzo"""
        if self.stats['total'] == 0:
            return self.stats

        return {
            **self.stats,
            'regex_only_pct': (self.stats['regex_only'] / self.stats['total']) * 100,
            'regex_local_pct': (self.stats['regex_local'] / self.stats['total']) * 100,
            'openai_fallback_pct': (self.stats['openai_fallback'] / self.stats['total']) * 100,
        }
