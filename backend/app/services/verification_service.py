"""
Servizio di Verifica Estrazione - Confronta risultati locali vs OpenAI

Scopo: Confrontare le estrazioni del LLM locale (Ollama) con OpenAI
per identificare discrepanze e migliorare gli algoritmi locali.
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

from app.config import get_settings
from app.services.interpello_extractors import OpenAIExtractor, OllamaExtractor, RegexExtractor, HybridExtractor, SpacyBertExtractor

logger = logging.getLogger(__name__)
settings = get_settings()


class VerificationService:
    """
    Servizio per verificare e confrontare estrazioni tra LLM locale e OpenAI.
    """

    def __init__(self, openai_api_key: str = None):
        """
        Inizializza il servizio di verifica.

        Args:
            openai_api_key: API key OpenAI (obbligatoria per le verifiche)
        """
        self.openai_api_key = openai_api_key or getattr(settings, 'OPENAI_API_KEY', None)

        # Inizializza estrattori
        self.regex_extractor = RegexExtractor()

        # LLM locale (Ollama)
        try:
            self.ollama_extractor = OllamaExtractor(
                base_url=settings.OLLAMA_BASE_URL,
                model=settings.OLLAMA_MODEL_INTERPRETATION,
                timeout=60.0
            )
        except Exception as e:
            logger.warning(f"Ollama non disponibile: {e}")
            self.ollama_extractor = None

        # OpenAI
        self.openai_extractor = None
        if self.openai_api_key:
            try:
                self.openai_extractor = OpenAIExtractor(
                    api_key=self.openai_api_key,
                    model=getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini')
                )
            except Exception as e:
                logger.warning(f"OpenAI non disponibile: {e}")

        # Hybrid extractor (regex + Ollama validation)
        try:
            self.hybrid_extractor = HybridExtractor(
                ollama_base_url=settings.OLLAMA_BASE_URL,
                ollama_model=settings.OLLAMA_MODEL_INTERPRETATION,
                timeout=120.0
            )
        except Exception as e:
            logger.warning(f"HybridExtractor non disponibile: {e}")
            self.hybrid_extractor = None

        # SpaCy + BERT extractor
        try:
            self.nlp_extractor = SpacyBertExtractor(
                ollama_base_url=settings.OLLAMA_BASE_URL,
                ollama_model=settings.OLLAMA_MODEL_INTERPRETATION,
                use_ollama_validation=True
            )
        except Exception as e:
            logger.warning(f"SpacyBertExtractor non disponibile: {e}")
            self.nlp_extractor = None

    def is_openai_available(self) -> bool:
        """Verifica se OpenAI è configurato."""
        return self.openai_extractor is not None

    def verify_interpello(self, testo: str, model: str = None) -> Dict[str, Any]:
        """
        Verifica estrazione interpello confrontando locale vs OpenAI.

        Args:
            testo: Testo dell'interpello da analizzare
            model: Modello OpenAI da usare (opzionale)

        Returns:
            Dict con risultati confronto
        """
        results = {
            'timestamp': datetime.now().isoformat(),
            'text_preview': testo[:200] + '...' if len(testo) > 200 else testo,
            'extractions': {},
            'comparison': {},
            'discrepancies': []
        }

        # 1. Estrazione Regex
        logger.info("📊 Estrazione Regex...")
        regex_start = datetime.now()
        regex_result = self.regex_extractor.extract(testo)
        regex_time = (datetime.now() - regex_start).total_seconds() * 1000
        results['extractions']['regex'] = {
            'data': regex_result,
            'time_ms': regex_time
        }

        # 2. Estrazione Ollama (se disponibile)
        if self.ollama_extractor:
            logger.info("📊 Estrazione Ollama...")
            ollama_start = datetime.now()
            try:
                ollama_result = self.ollama_extractor.extract(testo)
                ollama_time = (datetime.now() - ollama_start).total_seconds() * 1000
                results['extractions']['ollama'] = {
                    'data': ollama_result,
                    'time_ms': ollama_time
                }
            except Exception as e:
                results['extractions']['ollama'] = {'error': str(e)}
        else:
            results['extractions']['ollama'] = {'error': 'Non disponibile'}

        # 2b. Estrazione Hybrid (regex + validazione Ollama con contesto)
        if self.hybrid_extractor:
            logger.info("📊 Estrazione Hybrid (regex + validazione Ollama)...")
            hybrid_start = datetime.now()
            try:
                hybrid_result = self.hybrid_extractor.extract(testo)
                hybrid_time = (datetime.now() - hybrid_start).total_seconds() * 1000

                # Estrai confidence dal risultato
                confidence = hybrid_result.get('_overall_confidence', 0) if hybrid_result else 0

                # Rimuovi campi interni per visualizzazione pulita
                clean_hybrid = {}
                warnings = []
                if hybrid_result:
                    for k, v in hybrid_result.items():
                        if k.startswith('_warning_'):
                            warnings.append({k.replace('_warning_', ''): v})
                        elif not k.startswith('_'):
                            clean_hybrid[k] = v

                results['extractions']['hybrid'] = {
                    'data': clean_hybrid,
                    'time_ms': hybrid_time,
                    'confidence': confidence,
                    'warnings': warnings,
                    'validation_skipped': hybrid_result.get('_validation_skipped', False) if hybrid_result else True
                }
            except Exception as e:
                results['extractions']['hybrid'] = {'error': str(e)}
        else:
            results['extractions']['hybrid'] = {'error': 'Non disponibile'}

        # 2c. Estrazione NLP (spaCy + BERT)
        if self.nlp_extractor:
            logger.info("📊 Estrazione NLP (spaCy + BERT)...")
            nlp_start = datetime.now()
            try:
                nlp_result = self.nlp_extractor.extract(testo)
                nlp_time = (datetime.now() - nlp_start).total_seconds() * 1000

                # Estrai confidence dal risultato
                confidence = nlp_result.get('_overall_confidence', 0) if nlp_result else 0

                # Rimuovi campi interni per visualizzazione pulita
                clean_nlp = {}
                if nlp_result:
                    for k, v in nlp_result.items():
                        if not k.startswith('_') and k != 'confidence_scores':
                            clean_nlp[k] = v

                results['extractions']['nlp'] = {
                    'data': clean_nlp,
                    'time_ms': nlp_time,
                    'confidence': confidence,
                    'method': nlp_result.get('_extraction_method', 'spacy_bert') if nlp_result else None,
                    'confidence_scores': nlp_result.get('confidence_scores', {}) if nlp_result else {}
                }
            except Exception as e:
                results['extractions']['nlp'] = {'error': str(e)}
        else:
            results['extractions']['nlp'] = {'error': 'Non disponibile (spaCy/BERT non caricati)'}

        # 3. Estrazione OpenAI (se disponibile)
        if self.openai_extractor:
            logger.info(f"📊 Estrazione OpenAI (model={model or 'default'})...")
            openai_start = datetime.now()
            try:
                # Se specificato un modello diverso, usa quello
                if model:
                    original_model = self.openai_extractor.model
                    self.openai_extractor.model = model
                    openai_result = self.openai_extractor.extract(testo)
                    self.openai_extractor.model = original_model
                else:
                    openai_result = self.openai_extractor.extract(testo)
                openai_time = (datetime.now() - openai_start).total_seconds() * 1000
                results['extractions']['openai'] = {
                    'data': openai_result,
                    'time_ms': openai_time,
                    'model': model or getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini')
                }
            except Exception as e:
                results['extractions']['openai'] = {'error': str(e)}
        else:
            results['extractions']['openai'] = {'error': 'API key non configurata'}

        # 4. Confronta risultati
        results['comparison'] = self._compare_interpello_results(results['extractions'])
        results['discrepancies'] = self._find_discrepancies(results['comparison'])

        return results

    def verify_calendar_event(self, testo: str, model: str = None) -> Dict[str, Any]:
        """
        Verifica estrazione evento calendario confrontando locale vs OpenAI.

        Args:
            testo: Testo dell'email con convocazione
            model: Modello OpenAI da usare (opzionale)

        Returns:
            Dict con risultati confronto
        """
        results = {
            'timestamp': datetime.now().isoformat(),
            'text_preview': testo[:200] + '...' if len(testo) > 200 else testo,
            'extractions': {},
            'comparison': {},
            'discrepancies': []
        }

        prompt_template = """Estrai i dati della convocazione/riunione dal seguente testo.
Rispondi SOLO con un JSON valido con questi campi:
- data_inizio: data in formato YYYY-MM-DD
- ora_inizio: orario in formato HH:MM
- luogo: sede/indirizzo della riunione
- titolo: oggetto della riunione
- durata_ore: durata stimata in ore (default 1)

TESTO:
{testo}

JSON:"""

        prompt = prompt_template.format(testo=testo[:2000])

        # 1. Estrazione Ollama
        if self.ollama_extractor:
            logger.info("📊 Estrazione Ollama calendario...")
            try:
                from app.integrations.llm_client import LLMClient
                llm = LLMClient()
                ollama_start = datetime.now()
                response = llm.generate(prompt, model_type="interpretation")
                ollama_time = (datetime.now() - ollama_start).total_seconds() * 1000

                # Parse JSON response
                ollama_data = llm.parse_json_response(response)
                results['extractions']['ollama'] = {
                    'data': ollama_data,
                    'time_ms': ollama_time
                }
            except Exception as e:
                results['extractions']['ollama'] = {'error': str(e)}
        else:
            results['extractions']['ollama'] = {'error': 'Non disponibile'}

        # 2. Estrazione OpenAI
        if self.openai_extractor:
            use_model = model or getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini')
            logger.info(f"📊 Estrazione OpenAI calendario (model={use_model})...")
            try:
                import openai
                client = openai.OpenAI(api_key=self.openai_api_key)
                openai_start = datetime.now()

                response = client.chat.completions.create(
                    model=use_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=500
                )

                openai_time = (datetime.now() - openai_start).total_seconds() * 1000
                response_text = response.choices[0].message.content

                # Parse JSON
                import re
                json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
                if json_match:
                    openai_data = json.loads(json_match.group())
                else:
                    openai_data = {'raw_response': response_text}

                results['extractions']['openai'] = {
                    'data': openai_data,
                    'time_ms': openai_time,
                    'model': use_model
                }
            except Exception as e:
                results['extractions']['openai'] = {'error': str(e)}
        else:
            results['extractions']['openai'] = {'error': 'API key non configurata'}

        # Confronta risultati
        results['comparison'] = self._compare_calendar_results(results['extractions'])
        results['discrepancies'] = self._find_discrepancies(results['comparison'])

        return results

    def verify_categorization(self, oggetto: str, corpo: str, model: str = None) -> Dict[str, Any]:
        """
        Verifica categorizzazione email confrontando locale vs OpenAI.

        Args:
            oggetto: Oggetto dell'email
            corpo: Corpo dell'email
            model: Modello OpenAI da usare (opzionale)

        Returns:
            Dict con risultati confronto
        """
        results = {
            'timestamp': datetime.now().isoformat(),
            'oggetto': oggetto,
            'corpo_preview': corpo[:200] + '...' if len(corpo) > 200 else corpo,
            'extractions': {},
            'comparison': {},
            'discrepancies': []
        }

        prompt_template = """Categorizza questa email secondo le categorie SNALS.

CATEGORIE DISPONIBILI:
- interpello: Interpelli/supplenze scuola
- comunicazione_ust_usr: Comunicazioni UST/USR
- convocazione_riunione: Convocazioni a riunioni/tavoli
- richiesta_assistenza: Richieste di assistenza sindacale
- informativa_sindacale: Informative sindacali
- spam: Spam/pubblicità
- altro: Altro

EMAIL:
Oggetto: {oggetto}
Corpo: {corpo}

Rispondi SOLO con un JSON:
{{"categoria": "nome_categoria", "confidence": 0.0-1.0, "motivo": "breve spiegazione"}}

JSON:"""

        prompt = prompt_template.format(oggetto=oggetto, corpo=corpo[:1500])

        # 1. Ollama
        try:
            from app.integrations.llm_client import LLMClient
            llm = LLMClient()
            ollama_start = datetime.now()
            response = llm.generate(prompt, model_type="categorization")
            ollama_time = (datetime.now() - ollama_start).total_seconds() * 1000
            ollama_data = llm.parse_json_response(response)
            results['extractions']['ollama'] = {
                'data': ollama_data,
                'time_ms': ollama_time
            }
        except Exception as e:
            results['extractions']['ollama'] = {'error': str(e)}

        # 2. OpenAI
        if self.openai_extractor:
            use_model = model or getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini')
            logger.info(f"📊 Estrazione OpenAI categorizzazione (model={use_model})...")
            try:
                import openai
                client = openai.OpenAI(api_key=self.openai_api_key)
                openai_start = datetime.now()

                response = client.chat.completions.create(
                    model=use_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=200
                )

                openai_time = (datetime.now() - openai_start).total_seconds() * 1000
                response_text = response.choices[0].message.content

                import re
                json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
                if json_match:
                    openai_data = json.loads(json_match.group())
                else:
                    openai_data = {'raw_response': response_text}

                results['extractions']['openai'] = {
                    'data': openai_data,
                    'time_ms': openai_time,
                    'model': use_model
                }
            except Exception as e:
                results['extractions']['openai'] = {'error': str(e)}
        else:
            results['extractions']['openai'] = {'error': 'API key non configurata'}

        # Confronta
        results['comparison'] = self._compare_categorization_results(results['extractions'])
        results['discrepancies'] = self._find_discrepancies(results['comparison'])

        return results

    def _compare_interpello_results(self, extractions: Dict) -> Dict[str, Any]:
        """Confronta risultati estrazione interpello."""
        comparison = {}
        fields = ['classe_concorso', 'ore_settimanali', 'provincia', 'citta', 'istituto', 'meccanografico', 'indirizzo', 'data_fine_contratto', 'email_contatto', 'telefono_contatto']

        for field in fields:
            comparison[field] = {}
            for source in ['regex', 'ollama', 'hybrid', 'nlp', 'openai']:
                if source in extractions and 'data' in extractions[source]:
                    data = extractions[source]['data']
                    if data and isinstance(data, dict):
                        comparison[field][source] = data.get(field)

        return comparison

    def _compare_calendar_results(self, extractions: Dict) -> Dict[str, Any]:
        """Confronta risultati estrazione calendario."""
        comparison = {}
        fields = ['data_inizio', 'ora_inizio', 'luogo', 'titolo']

        for field in fields:
            comparison[field] = {}
            for source in ['ollama', 'openai']:
                if source in extractions and 'data' in extractions[source]:
                    data = extractions[source]['data']
                    if data and isinstance(data, dict):
                        comparison[field][source] = data.get(field)

        return comparison

    def _compare_categorization_results(self, extractions: Dict) -> Dict[str, Any]:
        """Confronta risultati categorizzazione."""
        comparison = {'categoria': {}, 'confidence': {}}

        for source in ['ollama', 'openai']:
            if source in extractions and 'data' in extractions[source]:
                data = extractions[source]['data']
                if data and isinstance(data, dict):
                    comparison['categoria'][source] = data.get('categoria')
                    comparison['confidence'][source] = data.get('confidence')

        return comparison

    def _normalize_value(self, value: str, field: str) -> str:
        """Normalizza un valore per confronto, gestendo formati diversi."""
        if not value:
            return ""

        import re
        normalized = str(value).lower().strip()

        # Normalizza date: DD-MM-YYYY, DD/MM/YYYY -> YYYY-MM-DD
        if field in ['data_inizio', 'data_fine', 'data_scadenza', 'data_fine_contratto']:
            # Pattern DD-MM-YYYY o DD/MM/YYYY
            date_match = re.match(r'(\d{2})[-/](\d{2})[-/](\d{4})', normalized)
            if date_match:
                normalized = f"{date_match.group(3)}-{date_match.group(2)}-{date_match.group(1)}"
            # Rimuovi T00:00:00Z e simili
            normalized = re.sub(r't\d{2}:\d{2}:\d{2}z?$', '', normalized)

        # Normalizza orari: 12.00 -> 12:00
        if field in ['ora_inizio', 'ora_fine']:
            normalized = normalized.replace('.', ':')

        # Normalizza caratteri simili (usando escape unicode per evitare problemi di encoding)
        normalized = normalized.replace('\u2013', '-')  # en-dash -> hyphen
        normalized = normalized.replace('\u2014', '-')  # em-dash -> hyphen
        normalized = normalized.replace('\u2019', "'")  # right single quote -> apostrophe
        normalized = normalized.replace('\u201c', '"').replace('\u201d', '"')  # smart double quotes
        normalized = normalized.replace('\u00b0', '')   # rimuovi simbolo grado
        normalized = normalized.replace('1 ', '1')  # "1 maggio" == "1maggio"

        # Per titoli: rimuovi date finali tipo "del 28-11-2025"
        if field == 'titolo':
            normalized = re.sub(r'\s+del\s+\d{2}[-/]\d{2}[-/]\d{4}$', '', normalized)
            normalized = re.sub(r'\s+\d{4}[-/]\d{4}$', '', normalized)  # rimuovi 2025-2026

        # Rimuovi spazi multipli
        normalized = re.sub(r'\s+', ' ', normalized)

        return normalized

    def _find_discrepancies(self, comparison: Dict) -> List[Dict]:
        """Trova discrepanze nei risultati."""
        discrepancies = []

        for field, values in comparison.items():
            if not values:
                continue

            unique_values = set()
            for source, value in values.items():
                if value is not None:
                    # Normalizza per confronto
                    normalized = self._normalize_value(str(value), field)
                    if normalized:
                        unique_values.add(normalized)

            if len(unique_values) > 1:
                discrepancies.append({
                    'field': field,
                    'values': values,
                    'message': f"Discrepanza trovata per '{field}': {list(unique_values)}"
                })

        return discrepancies


def get_verification_service(openai_api_key: str = None) -> VerificationService:
    """Factory per ottenere il servizio di verifica."""
    return VerificationService(openai_api_key=openai_api_key)
