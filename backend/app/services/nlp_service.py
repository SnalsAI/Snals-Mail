"""
Servizio NLP per estrazione entità con spaCy + BERT italiano.

Pipeline:
1. spaCy (it_core_news_lg) per NER di base
2. EntityRuler con pattern custom per classi concorso, meccanografici, scuole
3. BERT italiano per NER avanzato
4. Pattern matching per entità specifiche scuola
5. Integrazione con Ollama per validazione

Entità estratte:
- DATE: date (inizio, fine, scadenza)
- LOC: luoghi (città, province)
- ORG: organizzazioni (scuole, istituti, USP, USR)
- PER: persone
- CLASSE_CONCORSO: classi di concorso (custom)
- MECCANOGRAFICO: codici meccanografici scuole (custom)
- ISTITUTO: nomi scuole (custom)
- PROVINCIA: province italiane (custom)
- EMAIL: indirizzi email (custom)
- PHONE: numeri telefono (custom)
"""
import os
import re
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from functools import lru_cache

logger = logging.getLogger(__name__)

# Lazy loading per evitare import pesanti all'avvio
_spacy_nlp = None
_bert_ner = None
_entity_ruler_loaded = False


def get_spacy_nlp():
    """Carica il modello spaCy italiano con EntityRuler custom (lazy loading)."""
    global _spacy_nlp, _entity_ruler_loaded
    if _spacy_nlp is None:
        try:
            import spacy
            from spacy.language import Language

            logger.info("🔄 Caricamento modello spaCy it_core_news_lg...")
            _spacy_nlp = spacy.load("it_core_news_lg")
            logger.info("✅ Modello spaCy caricato")

        except Exception as e:
            logger.error(f"❌ Errore caricamento spaCy: {e}")
            # Fallback a modello piccolo se disponibile
            try:
                import spacy
                _spacy_nlp = spacy.load("it_core_news_sm")
                logger.warning("⚠️ Fallback a it_core_news_sm")
            except:
                _spacy_nlp = None

    # Aggiungi EntityRuler con pattern custom (solo una volta)
    if _spacy_nlp is not None and not _entity_ruler_loaded:
        try:
            _add_entity_ruler(_spacy_nlp)
            _entity_ruler_loaded = True
        except Exception as e:
            logger.warning(f"⚠️ Impossibile aggiungere EntityRuler: {e}")

    return _spacy_nlp


def _add_entity_ruler(nlp):
    """Aggiunge EntityRuler con pattern custom al pipeline spaCy."""
    try:
        from spacy.pipeline import EntityRuler

        # Rimuovi EntityRuler esistente se presente
        if "entity_ruler" in nlp.pipe_names:
            nlp.remove_pipe("entity_ruler")

        # Crea EntityRuler
        ruler = nlp.add_pipe("entity_ruler", before="ner")

        # Carica pattern custom
        try:
            from app.services.nlp_training_data import get_entity_patterns, get_custom_regexes
            patterns = get_entity_patterns()

            # Filtra pattern validi (solo quelli con string patterns, non token patterns per ora)
            valid_patterns = []
            for p in patterns:
                if isinstance(p.get("pattern"), str):
                    valid_patterns.append(p)
                # Salta token patterns complessi per ora

            ruler.add_patterns(valid_patterns)
            logger.info(f"✅ EntityRuler: aggiunti {len(valid_patterns)} pattern custom")

        except ImportError as e:
            logger.warning(f"⚠️ Training data non disponibili: {e}")

            # Pattern minimi di fallback
            fallback_patterns = _get_fallback_patterns()
            ruler.add_patterns(fallback_patterns)
            logger.info(f"✅ EntityRuler: aggiunti {len(fallback_patterns)} pattern fallback")

    except Exception as e:
        logger.error(f"❌ Errore EntityRuler: {e}")


def _get_fallback_patterns():
    """Pattern di fallback se training data non disponibili."""
    patterns = []

    # Classi concorso comuni
    classi = ["A-01", "A-12", "A-22", "A-28", "A-42", "A-46", "A-48", "AA24", "AB24", "B-16"]
    for c in classi:
        patterns.append({"label": "CLASSE_CONCORSO", "pattern": c})
        patterns.append({"label": "CLASSE_CONCORSO", "pattern": c.replace("-", "")})

    # Province principali
    province = ["TA", "BA", "BR", "LE", "FG", "MI", "RM", "NA", "TO", "PA"]
    for p in province:
        patterns.append({"label": "PROVINCIA", "pattern": p})

    return patterns


def get_bert_ner():
    """Carica il modello BERT italiano per NER (lazy loading)."""
    global _bert_ner
    if _bert_ner is None:
        try:
            from transformers import pipeline
            logger.info("🔄 Caricamento modello BERT italiano NER...")
            # Modello italiano per NER
            _bert_ner = pipeline(
                "ner",
                model="dbmdz/bert-base-italian-xxl-cased",
                aggregation_strategy="simple"
            )
            logger.info("✅ Modello BERT NER caricato")
        except Exception as e:
            logger.warning(f"⚠️ BERT NER non disponibile: {e}")
            _bert_ner = None
    return _bert_ner


class NLPExtractor:
    """
    Estrattore NLP che combina spaCy + BERT + pattern matching.

    Features:
    - EntityRuler con ~500+ pattern per classi concorso, scuole, province
    - Regex ottimizzato per codici meccanografici
    - BERT italiano per NER avanzato
    """

    # Pattern per entità specifiche scuola
    CLASSE_CONCORSO_PATTERN = re.compile(
        r'\b([A-E][A-Z]?)[- ]?(\d{2,3})\b',
        re.IGNORECASE
    )

    # Pattern avanzato per meccanografici (formato: XXYY123456Z)
    # XX = provincia, YY = tipo istituto, 123456 = numero, Z = carattere opzionale
    MECCANOGRAFICO_PATTERN = re.compile(
        r'\b([A-Z]{2})(IC|IS|PS|EE|MM|PC|SD|RI|VE|CT|VC|AA|VR|SS|TD|TF|TE|TH|TL|TA|TB|RC|RA|RH|SF)'
        r'(\d{5,6})([A-Z0-9])?\b',
        re.IGNORECASE
    )

    EMAIL_PATTERN = re.compile(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    )

    PHONE_PATTERN = re.compile(
        r'(?:tel\.?|telefono|cell\.?|cellulare)?[\s:]*'
        r'(\+39)?[\s.-]?(\d{2,4})[\s.-]?(\d{5,8})',
        re.IGNORECASE
    )

    ORE_PATTERN = re.compile(
        r'(\d{1,2})\s*(?:ore|h|ora)(?:\s*settimanali)?',
        re.IGNORECASE
    )

    # Province italiane
    PROVINCE_CODES = {
        'AG', 'AL', 'AN', 'AO', 'AP', 'AQ', 'AR', 'AT', 'AV', 'BA',
        'BG', 'BI', 'BL', 'BN', 'BO', 'BR', 'BS', 'BT', 'BZ', 'CA',
        'CB', 'CE', 'CH', 'CL', 'CN', 'CO', 'CR', 'CS', 'CT', 'CZ',
        'EN', 'FC', 'FE', 'FG', 'FI', 'FM', 'FR', 'GE', 'GO', 'GR',
        'IM', 'IS', 'KR', 'LC', 'LE', 'LI', 'LO', 'LT', 'LU', 'MB',
        'MC', 'ME', 'MI', 'MN', 'MO', 'MS', 'MT', 'NA', 'NO', 'NU',
        'OR', 'PA', 'PC', 'PD', 'PE', 'PG', 'PI', 'PN', 'PO', 'PR',
        'PT', 'PU', 'PV', 'PZ', 'RA', 'RC', 'RE', 'RG', 'RI', 'RM',
        'RN', 'RO', 'SA', 'SI', 'SO', 'SP', 'SR', 'SS', 'SU', 'SV',
        'TA', 'TE', 'TN', 'TO', 'TP', 'TR', 'TS', 'TV', 'UD', 'VA',
        'VB', 'VC', 'VE', 'VI', 'VR', 'VT', 'VV'
    }

    def __init__(self):
        """Inizializza l'estrattore NLP."""
        self.nlp = None
        self.bert_ner = None
        self._initialized = False
        self._known_schools = None  # Cache per scuole note

    def _ensure_initialized(self):
        """Inizializza i modelli al primo utilizzo."""
        if not self._initialized:
            self.nlp = get_spacy_nlp()
            self.bert_ner = get_bert_ner()
            self._load_known_schools()
            self._initialized = True

    def _load_known_schools(self):
        """Carica dizionario scuole note dal file JSON."""
        if self._known_schools is not None:
            return

        self._known_schools = {}
        try:
            import json
            from pathlib import Path
            data_dir = Path(__file__).parent.parent / "data"
            scuole_file = data_dir / "scuole_taranto.json"

            if scuole_file.exists():
                with open(scuole_file, 'r', encoding='utf-8') as f:
                    self._known_schools = json.load(f)
                logger.info(f"✅ Caricate {len(self._known_schools)} scuole note")
        except Exception as e:
            logger.warning(f"⚠️ Impossibile caricare scuole: {e}")

    def extract_entities(self, text: str) -> Dict[str, Any]:
        """
        Estrae entità dal testo usando spaCy + BERT + pattern.

        Args:
            text: Testo da analizzare

        Returns:
            Dict con entità estratte per tipo
        """
        self._ensure_initialized()

        if not text or len(text.strip()) < 10:
            return {'entities': [], 'error': 'Testo troppo corto'}

        result = {
            'entities': [],
            'dates': [],
            'locations': [],
            'organizations': [],
            'persons': [],
            'classe_concorso': [],
            'meccanografici': [],  # Codici scuole (TAIC824001, etc.)
            'istituti': [],        # Nomi scuole da EntityRuler
            'emails': [],
            'phones': [],
            'ore_settimanali': [],
            'province': [],
            'raw_spacy': [],
            'raw_bert': []
        }

        # 1. Estrazione spaCy (include EntityRuler con pattern custom)
        if self.nlp:
            try:
                spacy_entities = self._extract_with_spacy(text)
                result['raw_spacy'] = spacy_entities

                for ent in spacy_entities:
                    # Entità standard NER
                    if ent['label'] == 'DATE':
                        result['dates'].append(ent)
                    elif ent['label'] in ('LOC', 'GPE'):
                        result['locations'].append(ent)
                    elif ent['label'] == 'ORG':
                        result['organizations'].append(ent)
                    elif ent['label'] == 'PER':
                        result['persons'].append(ent)
                    # Entità custom da EntityRuler
                    elif ent['label'] == 'CLASSE_CONCORSO':
                        result['classe_concorso'].append(ent)
                    elif ent['label'] == 'MECCANOGRAFICO':
                        result['meccanografici'].append(ent)
                    elif ent['label'] == 'ISTITUTO':
                        result['istituti'].append(ent)
                    elif ent['label'] == 'PROVINCIA':
                        result['province'].append(ent)

                    result['entities'].append(ent)
            except Exception as e:
                logger.error(f"Errore spaCy: {e}")

        # 2. Estrazione BERT (se disponibile)
        if self.bert_ner:
            try:
                bert_entities = self._extract_with_bert(text)
                result['raw_bert'] = bert_entities

                # Merge con risultati spaCy (evita duplicati)
                existing_texts = {e['text'].lower() for e in result['entities']}
                for ent in bert_entities:
                    if ent['text'].lower() not in existing_texts:
                        result['entities'].append(ent)
                        existing_texts.add(ent['text'].lower())

                        # Categorizza
                        if ent['label'] == 'DATE':
                            result['dates'].append(ent)
                        elif ent['label'] in ('LOC', 'GPE'):
                            result['locations'].append(ent)
                        elif ent['label'] == 'ORG':
                            result['organizations'].append(ent)
                        elif ent['label'] == 'PER':
                            result['persons'].append(ent)

            except Exception as e:
                logger.warning(f"Errore BERT: {e}")

        # 3. Pattern matching per entità specifiche (complementa EntityRuler)
        # Classe concorso (se non trovata da EntityRuler)
        if not result['classe_concorso']:
            result['classe_concorso'] = self._extract_classe_concorso(text)

        # Meccanografici via regex (se non trovati da EntityRuler)
        if not result['meccanografici']:
            result['meccanografici'] = self._extract_meccanografici(text)

        # Email, telefoni, ore (sempre via pattern)
        result['emails'] = self._extract_emails(text)
        result['phones'] = self._extract_phones(text)
        result['ore_settimanali'] = self._extract_ore(text)

        # Province (se non trovate da EntityRuler)
        if not result['province']:
            result['province'] = self._extract_province(text)

        logger.info(f"📊 NLP: {len(result['entities'])} entità, "
                   f"{len(result['dates'])} date, "
                   f"{len(result['locations'])} luoghi, "
                   f"{len(result['organizations'])} organizzazioni")

        return result

    def _extract_with_spacy(self, text: str) -> List[Dict]:
        """Estrae entità con spaCy."""
        doc = self.nlp(text[:50000])  # Limita per performance

        entities = []
        for ent in doc.ents:
            entities.append({
                'text': ent.text,
                'label': ent.label_,
                'start': ent.start_char,
                'end': ent.end_char,
                'source': 'spacy',
                'confidence': 0.85  # spaCy non fornisce confidence
            })

        return entities

    def _extract_with_bert(self, text: str) -> List[Dict]:
        """Estrae entità con BERT italiano."""
        # Limita lunghezza per BERT
        max_len = 5000
        if len(text) > max_len:
            text = text[:max_len]

        results = self.bert_ner(text)

        entities = []
        for ent in results:
            # Mappa etichette BERT a standard
            label = ent['entity_group'].upper()
            if label in ('I-LOC', 'B-LOC', 'LOC'):
                label = 'LOC'
            elif label in ('I-ORG', 'B-ORG', 'ORG'):
                label = 'ORG'
            elif label in ('I-PER', 'B-PER', 'PER'):
                label = 'PER'
            elif 'DATE' in label or 'TIME' in label:
                label = 'DATE'

            entities.append({
                'text': ent['word'],
                'label': label,
                'start': ent.get('start', 0),
                'end': ent.get('end', 0),
                'source': 'bert',
                'confidence': float(ent.get('score', 0.5))
            })

        return entities

    def _extract_classe_concorso(self, text: str) -> List[Dict]:
        """Estrae classi di concorso."""
        results = []
        for match in self.CLASSE_CONCORSO_PATTERN.finditer(text):
            prefix = match.group(1).upper()
            number = match.group(2)
            full_class = f"{prefix}-{number}"

            # Evita falsi positivi (date, codici casuali)
            context_start = max(0, match.start() - 20)
            context = text[context_start:match.start()].lower()
            if any(x in context for x in ['il ', 'del ', 'n. ', 'n° ']):
                continue

            results.append({
                'text': full_class,
                'label': 'CLASSE_CONCORSO',
                'start': match.start(),
                'end': match.end(),
                'source': 'pattern',
                'confidence': 0.9
            })

        return results

    def _extract_meccanografici(self, text: str) -> List[Dict]:
        """
        Estrae codici meccanografici scuole.

        Formato: XXYY123456Z
        - XX = provincia (TA, BA, MI, etc.)
        - YY = tipo istituto (IC, IS, PS, etc.)
        - 123456 = numero identificativo
        - Z = carattere opzionale

        Esempi: TAIC824001, BAIS00123X, RMPS007001
        """
        results = []
        seen = set()

        for match in self.MECCANOGRAFICO_PATTERN.finditer(text):
            provincia = match.group(1).upper()
            tipo = match.group(2).upper()
            numero = match.group(3)
            extra = match.group(4) or ""

            # Verifica che la provincia sia valida
            if provincia not in self.PROVINCE_CODES:
                continue

            codice = f"{provincia}{tipo}{numero}{extra}".upper()

            # Evita duplicati
            if codice in seen:
                continue
            seen.add(codice)

            # Controlla se è una scuola nota
            school_info = None
            confidence = 0.85
            if self._known_schools and codice in self._known_schools:
                school_info = self._known_schools[codice]
                confidence = 0.98  # Alta confidence se scuola nota

            result_entry = {
                'text': codice,
                'label': 'MECCANOGRAFICO',
                'start': match.start(),
                'end': match.end(),
                'source': 'pattern',
                'confidence': confidence,
                'provincia': provincia,
                'tipo_istituto': tipo
            }

            # Aggiungi info scuola se nota
            if school_info:
                result_entry['nome_scuola'] = school_info.get('nome')
                result_entry['comune'] = school_info.get('comune')

            results.append(result_entry)

        return results

    def _extract_emails(self, text: str) -> List[Dict]:
        """Estrae indirizzi email."""
        results = []
        for match in self.EMAIL_PATTERN.finditer(text):
            results.append({
                'text': match.group(0),
                'label': 'EMAIL',
                'start': match.start(),
                'end': match.end(),
                'source': 'pattern',
                'confidence': 0.95
            })
        return results

    def _extract_phones(self, text: str) -> List[Dict]:
        """Estrae numeri di telefono."""
        results = []
        for match in self.PHONE_PATTERN.finditer(text):
            # Ricostruisci numero
            parts = [g for g in match.groups() if g]
            phone = ''.join(parts)
            if len(phone) >= 8:  # Minimo 8 cifre
                results.append({
                    'text': phone,
                    'label': 'PHONE',
                    'start': match.start(),
                    'end': match.end(),
                    'source': 'pattern',
                    'confidence': 0.9
                })
        return results

    def _extract_ore(self, text: str) -> List[Dict]:
        """Estrae ore settimanali."""
        results = []
        for match in self.ORE_PATTERN.finditer(text):
            ore = int(match.group(1))
            if 1 <= ore <= 40:  # Range ragionevole
                results.append({
                    'text': str(ore),
                    'label': 'ORE_SETTIMANALI',
                    'start': match.start(),
                    'end': match.end(),
                    'source': 'pattern',
                    'confidence': 0.85
                })
        return results

    def _extract_province(self, text: str) -> List[Dict]:
        """Estrae province italiane dal testo."""
        results = []

        # Pattern: città (XX) dove XX è codice provincia
        pattern = re.compile(r'([A-Z][a-zàèéìòù]+)\s*\(([A-Z]{2})\)')
        for match in pattern.finditer(text):
            code = match.group(2).upper()
            if code in self.PROVINCE_CODES:
                results.append({
                    'text': code,
                    'city': match.group(1),
                    'label': 'PROVINCIA',
                    'start': match.start(),
                    'end': match.end(),
                    'source': 'pattern',
                    'confidence': 0.95
                })

        return results

    def extract_for_interpello(self, text: str) -> Dict[str, Any]:
        """
        Estrazione specializzata per interpelli scolastici.

        Returns:
            Dict con campi specifici interpello incluso meccanografico
        """
        entities = self.extract_entities(text)

        interpello_data = {
            'classe_concorso': None,
            'ore_settimanali': None,
            'provincia': None,
            'citta': None,
            'istituto': None,
            'meccanografico': None,  # Codice scuola (TAIC824001, etc.)
            'email_contatto': None,
            'telefono_contatto': None,
            'data_scadenza': None,
            'confidence_scores': {},
            'all_entities': entities
        }

        # Classe di concorso
        if entities['classe_concorso']:
            best = max(entities['classe_concorso'], key=lambda x: x['confidence'])
            interpello_data['classe_concorso'] = best['text']
            interpello_data['confidence_scores']['classe_concorso'] = best['confidence']

        # Ore settimanali
        if entities['ore_settimanali']:
            best = max(entities['ore_settimanali'], key=lambda x: x['confidence'])
            interpello_data['ore_settimanali'] = int(best['text'])
            interpello_data['confidence_scores']['ore_settimanali'] = best['confidence']

        # Provincia e città
        if entities['province']:
            best = max(entities['province'], key=lambda x: x['confidence'])
            interpello_data['provincia'] = best['text']
            interpello_data['citta'] = best.get('city')
            interpello_data['confidence_scores']['provincia'] = best['confidence']

        # Meccanografico (codice scuola)
        if entities['meccanografici']:
            best = max(entities['meccanografici'], key=lambda x: x['confidence'])
            interpello_data['meccanografico'] = best['text']
            interpello_data['confidence_scores']['meccanografico'] = best['confidence']
            # Se abbiamo info scuola dal meccanografico, usale per istituto
            if best.get('nome_scuola') and not interpello_data['istituto']:
                interpello_data['istituto'] = best['nome_scuola']
                interpello_data['confidence_scores']['istituto'] = best['confidence']
            # Provincia dal meccanografico se non trovata
            if best.get('provincia') and not interpello_data['provincia']:
                interpello_data['provincia'] = best['provincia']
                interpello_data['confidence_scores']['provincia'] = best['confidence']

        # Email
        if entities['emails']:
            # Preferisci email istituzionali
            for email in entities['emails']:
                email_text = email['text'].lower()
                if any(x in email_text for x in ['istruzione', 'scuola', 'miur', 'gov']):
                    interpello_data['email_contatto'] = email['text']
                    interpello_data['confidence_scores']['email_contatto'] = email['confidence']
                    break
            if not interpello_data['email_contatto'] and entities['emails']:
                interpello_data['email_contatto'] = entities['emails'][0]['text']
                interpello_data['confidence_scores']['email_contatto'] = entities['emails'][0]['confidence']

        # Telefono
        if entities['phones']:
            interpello_data['telefono_contatto'] = entities['phones'][0]['text']
            interpello_data['confidence_scores']['telefono_contatto'] = entities['phones'][0]['confidence']

        # Istituto da EntityRuler (priorità) o da organizzazioni
        if not interpello_data['istituto']:
            # Prima prova con istituti riconosciuti da EntityRuler
            if entities.get('istituti'):
                best = max(entities['istituti'], key=lambda x: x['confidence'])
                interpello_data['istituto'] = best['text']
                interpello_data['confidence_scores']['istituto'] = best['confidence']
            else:
                # Fallback: cerca tra le organizzazioni
                for org in entities['organizations']:
                    org_text = org['text'].lower()
                    if any(x in org_text for x in ['istituto', 'scuola', 'liceo', 'tecnico', 'professionale', 'comprensivo', 'itis', 'ipsia']):
                        interpello_data['istituto'] = org['text']
                        interpello_data['confidence_scores']['istituto'] = org['confidence']
                        break

        # Data scadenza (cerca date future)
        for date_ent in entities['dates']:
            # Semplice euristica: cerca parole chiave vicine
            start = max(0, date_ent['start'] - 50)
            context = text[start:date_ent['start']].lower()
            if any(x in context for x in ['scadenza', 'entro', 'termine', 'presentare']):
                interpello_data['data_scadenza'] = date_ent['text']
                interpello_data['confidence_scores']['data_scadenza'] = date_ent['confidence']
                break

        return interpello_data

    def extract_calendar_event(self, text: str) -> Dict[str, Any]:
        """
        Estrazione specializzata per eventi calendario (convocazioni, riunioni).

        Returns:
            Dict con campi specifici per eventi calendario
        """
        import re
        entities = self.extract_entities(text)

        calendar_data = {
            'data_inizio': None,
            'ora_inizio': None,
            'data_fine': None,
            'ora_fine': None,
            'luogo': None,
            'scuola_nome': None,
            'scuola_codice': None,
            'modalita': None,  # 'presenza', 'online', 'mista'
            'tipo_riunione': None,  # 'collegio_docenti', 'consiglio_istituto', etc.
            'motivo': None,
            'ordine_del_giorno': [],
            'contatto_email': None,
            'contatto_telefono': None,
            'confidence_scores': {},
            'all_entities': entities
        }

        text_lower = text.lower()

        # Date - cerca con regex (spaCy italiano non riconosce bene le date)
        date_pattern = r'\b(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})\b'
        date_matches = re.findall(date_pattern, text)
        if date_matches:
            calendar_data['data_inizio'] = date_matches[0]
            calendar_data['confidence_scores']['data_inizio'] = 0.9
            if len(date_matches) > 1:
                calendar_data['data_fine'] = date_matches[1]
        elif entities['dates']:
            # Fallback su spaCy se regex non trova nulla
            sorted_dates = sorted(entities['dates'], key=lambda x: x.get('start', 0))
            if sorted_dates:
                calendar_data['data_inizio'] = sorted_dates[0]['text']
                calendar_data['confidence_scores']['data_inizio'] = sorted_dates[0]['confidence']
                if len(sorted_dates) > 1:
                    calendar_data['data_fine'] = sorted_dates[1]['text']

        # Ora - estrai pattern orario
        time_pattern = r'\b(\d{1,2}[:\.,]\d{2})\b|\b(ore\s+\d{1,2}[:\.,]?\d{0,2})\b'
        time_matches = re.findall(time_pattern, text, re.IGNORECASE)
        if time_matches:
            # Prendi il primo orario trovato
            first_time = time_matches[0][0] or time_matches[0][1]
            first_time = re.sub(r'ore\s*', '', first_time, flags=re.IGNORECASE)
            first_time = first_time.replace(',', ':').replace('.', ':')
            calendar_data['ora_inizio'] = first_time.strip()
            calendar_data['confidence_scores']['ora_inizio'] = 0.85

        # Luogo - cerca location entities o pattern comuni
        if entities['locations']:
            best_loc = max(entities['locations'], key=lambda x: x['confidence'])
            calendar_data['luogo'] = best_loc['text']
            calendar_data['confidence_scores']['luogo'] = best_loc['confidence']
        else:
            # Pattern per luoghi comuni
            luogo_patterns = [
                r'presso\s+(.+?)(?:\.|,|$)',
                r'in\s+(.+?)(?:\.|,|$)',
                r'aula\s+(\w+)',
                r'sala\s+(\w+)'
            ]
            for pattern in luogo_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    calendar_data['luogo'] = match.group(1).strip()[:50]
                    calendar_data['confidence_scores']['luogo'] = 0.7
                    break

        # Scuola - dal meccanografico o istituti
        if entities['meccanografici']:
            best = max(entities['meccanografici'], key=lambda x: x['confidence'])
            calendar_data['scuola_codice'] = best['text']
            if best.get('nome_scuola'):
                calendar_data['scuola_nome'] = best['nome_scuola']
            calendar_data['confidence_scores']['scuola_codice'] = best['confidence']

        if not calendar_data['scuola_nome'] and entities.get('istituti'):
            best = max(entities['istituti'], key=lambda x: x['confidence'])
            calendar_data['scuola_nome'] = best['text']
            calendar_data['confidence_scores']['scuola_nome'] = best['confidence']

        if not calendar_data['scuola_nome']:
            # Cerca tra organizzazioni
            for org in entities['organizations']:
                org_text = org['text'].lower()
                if any(x in org_text for x in ['istituto', 'scuola', 'liceo', 'comprensivo']):
                    calendar_data['scuola_nome'] = org['text']
                    calendar_data['confidence_scores']['scuola_nome'] = org['confidence']
                    break

        # Modalità
        if any(x in text_lower for x in ['presenza', 'di persona', 'in sede']):
            calendar_data['modalita'] = 'presenza'
        elif any(x in text_lower for x in ['online', 'videoconferenza', 'teams', 'meet', 'zoom', 'da remoto']):
            calendar_data['modalita'] = 'online'
        elif any(x in text_lower for x in ['mista', 'ibrida', 'presenza e online']):
            calendar_data['modalita'] = 'mista'

        # Tipo riunione
        tipo_patterns = {
            'collegio_docenti': ['collegio dei docenti', 'collegio docenti'],
            'consiglio_istituto': ['consiglio di istituto', 'consiglio d\'istituto'],
            'consiglio_classe': ['consiglio di classe'],
            'assemblea_sindacale': ['assemblea sindacale'],
            'rsu': ['rsu', 'r.s.u.'],
            'convocazione': ['convocazione', 'convocato'],
            'riunione': ['riunione']
        }
        for tipo, keywords in tipo_patterns.items():
            if any(k in text_lower for k in keywords):
                calendar_data['tipo_riunione'] = tipo
                calendar_data['confidence_scores']['tipo_riunione'] = 0.9
                break

        # Motivo - cerca pattern "oggetto:" o "per discutere"
        motivo_patterns = [
            r'oggetto:\s*(.+?)(?:\n|$)',
            r'per\s+discutere\s+(.+?)(?:\.|,|$)',
            r'all\'ordine del giorno:\s*(.+?)(?:\n|$)'
        ]
        for pattern in motivo_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                calendar_data['motivo'] = match.group(1).strip()[:200]
                calendar_data['confidence_scores']['motivo'] = 0.75
                break

        # Email
        if entities['emails']:
            calendar_data['contatto_email'] = entities['emails'][0]['text']
            calendar_data['confidence_scores']['contatto_email'] = entities['emails'][0]['confidence']

        # Telefono
        if entities['phones']:
            calendar_data['contatto_telefono'] = entities['phones'][0]['text']
            calendar_data['confidence_scores']['contatto_telefono'] = entities['phones'][0]['confidence']

        return calendar_data


# Singleton
_nlp_extractor: Optional[NLPExtractor] = None


def get_nlp_extractor() -> NLPExtractor:
    """Ottiene istanza singleton dell'estrattore NLP."""
    global _nlp_extractor
    if _nlp_extractor is None:
        _nlp_extractor = NLPExtractor()
    return _nlp_extractor


def reload_nlp_model():
    """
    Ricarica il modello NLP con i nuovi pattern da training.

    Chiamare dopo apply_training() per rendere effettivi i nuovi pattern
    senza riavviare il container.
    """
    global _spacy_nlp, _entity_ruler_loaded, _nlp_extractor

    logger.info("🔄 Ricaricamento modello NLP con nuovi pattern...")

    # Reset stato
    _entity_ruler_loaded = False

    # Ricarica EntityRuler se spaCy è già caricato
    if _spacy_nlp is not None:
        try:
            # Carica anche pattern da trained_patterns.json
            from pathlib import Path
            import json

            trained_file = Path(__file__).parent.parent / "data" / "training" / "trained_patterns.json"

            if trained_file.exists():
                with open(trained_file, 'r', encoding='utf-8') as f:
                    trained_patterns = json.load(f)
                logger.info(f"📚 Trovati {len(trained_patterns)} pattern da training")
            else:
                trained_patterns = []

            # Rimuovi e ricrea EntityRuler
            if "entity_ruler" in _spacy_nlp.pipe_names:
                _spacy_nlp.remove_pipe("entity_ruler")

            ruler = _spacy_nlp.add_pipe("entity_ruler", before="ner")

            # Carica pattern base
            from app.services.nlp_training_data import get_entity_patterns
            base_patterns = get_entity_patterns()

            # Merge pattern base + trained
            all_patterns = []
            for p in base_patterns:
                if isinstance(p.get("pattern"), str):
                    all_patterns.append(p)

            for p in trained_patterns:
                if isinstance(p.get("pattern"), str):
                    all_patterns.append(p)

            ruler.add_patterns(all_patterns)
            _entity_ruler_loaded = True

            logger.info(f"✅ EntityRuler ricaricato: {len(all_patterns)} pattern totali")

        except Exception as e:
            logger.error(f"❌ Errore ricaricamento pattern: {e}")
            raise

    # Reset anche l'estrattore per forzare nuovo init
    _nlp_extractor = None

    logger.info("✅ Modello NLP ricaricato con successo")
