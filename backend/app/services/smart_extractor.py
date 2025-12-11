"""
Smart Extractor - Strategia ibrida intelligente per estrazione interpelli
Strategia: Regex → Validazione LLM locale → LLM estrazione completa → OpenAI (se necessario)
"""
import logging
from typing import Dict, Optional, Any
from datetime import datetime

from app.services.interpello_extractors import (
    RegexExtractor,
    OllamaExtractor,
    OpenAIExtractor
)
from app.services.regex_validator import RegexValidator
from app.services.semantic_validator import SemanticValidator

logger = logging.getLogger(__name__)


class SmartInterpelloExtractor:
    """
    Estrattore intelligente con strategia a cascata:
    1. Regex (veloce, affidabile per dati strutturati)
    2. Verifica/completamento con LLM locale
    3. OpenAI come fallback finale
    """

    # Campi richiesti per interpelli
    REQUIRED_FIELDS = ['classe_concorso', 'ore_settimanali', 'provincia', 'data_fine_contratto']

    def __init__(self, openai_api_key: str = None, openai_model: str = "gpt-4o-mini", db_session = None):
        """
        Inizializza estrattore smart.

        Args:
            openai_api_key: API key OpenAI (opzionale)
            openai_model: Modello OpenAI da usare
            db_session: Sessione DB per validazione semantica
        """
        self.regex_extractor = RegexExtractor()

        # Validatore regex con LLM locale
        self.regex_validator = RegexValidator()

        # Validatore semantico (controlla classe concorso, date, etc)
        self.semantic_validator = SemanticValidator(db=db_session)

        # LLM locale per estrazione completa (se validazione fallisce)
        try:
            from app.config import get_settings
            settings = get_settings()
            self.local_extractor = OllamaExtractor(
                base_url=settings.OLLAMA_BASE_URL,
                model=settings.OLLAMA_MODEL_INTERPRETATION,
                timeout=60.0
            )
        except Exception as e:
            logger.warning(f"LLM locale non disponibile: {e}")
            self.local_extractor = None

        # OpenAI per fallback
        self.openai_extractor = None
        if openai_api_key:
            try:
                self.openai_extractor = OpenAIExtractor(
                    api_key=openai_api_key,
                    model=openai_model
                )
            except Exception as e:
                logger.warning(f"OpenAI non disponibile: {e}")

        # Statistiche per logging
        self.stats = {
            'regex_only': 0,
            'regex_validated': 0,
            'regex_corrected': 0,
            'regex_local': 0,
            'openai_fallback': 0,
            'total': 0
        }

    def calculate_completeness(self, dati: Optional[Dict]) -> float:
        """
        Calcola percentuale di completezza dei dati estratti.

        Args:
            dati: Dizionario con dati estratti

        Returns:
            float: Percentuale 0.0-1.0
        """
        if not dati:
            return 0.0

        fields_found = sum(1 for field in self.REQUIRED_FIELDS if dati.get(field))
        return fields_found / len(self.REQUIRED_FIELDS)

    def validate_data_quality(self, dati: Dict) -> bool:
        """
        Valida qualità dei dati estratti.

        Args:
            dati: Dati da validare

        Returns:
            bool: True se dati validi
        """
        if not dati:
            return False

        # Verifica presenza classe_concorso (campo critico)
        if not dati.get('classe_concorso'):
            return False

        # Verifica formato classe_concorso (es: A-42, AB24)
        classe = dati['classe_concorso']
        if not (len(classe) >= 3 and classe[0].isalpha()):
            return False

        # Verifica ore_settimanali se presente
        if 'ore_settimanali' in dati and dati['ore_settimanali']:
            ore = dati['ore_settimanali']
            if not isinstance(ore, (int, float)) or ore < 1 or ore > 40:
                return False

        return True

    def extract(self, testo: str, strategy_override: str = None) -> Optional[Dict[str, Any]]:
        """
        Estrae dati interpello con strategia intelligente.

        Args:
            testo: Testo da cui estrarre dati
            strategy_override: Forza una strategia specifica

        Returns:
            Dict con dati estratti + metadata sulla strategia usata
        """
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
        logger.info("📊 STEP 1: Estrazione con Regex")
        regex_start = datetime.now()

        dati_regex = self.regex_extractor.extract(testo)
        completeness_regex = self.calculate_completeness(dati_regex)

        regex_time = (datetime.now() - regex_start).total_seconds() * 1000
        metadata['strategies_used'].append('regex')
        metadata['completeness_scores']['regex'] = completeness_regex
        metadata['regex_time_ms'] = regex_time

        logger.info(f"✅ Regex completato: {completeness_regex:.0%} completo in {regex_time:.0f}ms")

        # ============================================================
        # STEP 2: VALIDAZIONE SEMANTICA (SEMPRE, anche se regex 100%)
        # ============================================================
        semantic_validation = None
        if dati_regex:
            logger.info("📊 STEP 2: Validazione semantica dati regex CON ANALISI CONTESTUALE")
            semantic_start = datetime.now()

            semantic_validation = self.semantic_validator.validate_all(dati_regex, testo_originale=testo)
            semantic_time = (datetime.now() - semantic_start).total_seconds() * 1000

            metadata['strategies_used'].append('semantic_validation')
            metadata['semantic_validation'] = {
                'valid': semantic_validation['valid'],
                'errors': semantic_validation['errors'],
                'warnings': semantic_validation['warnings'],
                'time_ms': semantic_time
            }

            logger.info(
                f"✅ Validazione semantica: "
                f"valid={semantic_validation['valid']}, "
                f"errors={len(semantic_validation['errors'])}, "
                f"warnings={len(semantic_validation['warnings'])}"
            )

            if semantic_validation['errors']:
                for error in semantic_validation['errors']:
                    logger.warning(f"  ❌ {error}")

            if semantic_validation['warnings']:
                for warning in semantic_validation['warnings']:
                    logger.warning(f"  ⚠️ {warning}")

            # Se validazione semantica OK e completezza >= 85% → usa regex
            if semantic_validation['valid'] and completeness_regex >= 0.85:
                metadata['strategy_final'] = 'regex_only'
                metadata['total_time_ms'] = regex_time + semantic_time
                self.stats['regex_only'] += 1

                logger.info(f"✅ Dati regex validati semanticamente ({completeness_regex:.0%})")

                # Usa dati corretti (normalizzati)
                corrected = semantic_validation.get('corrected_data', dati_regex)
                corrected['metadata_estrazione'] = metadata
                return corrected

        # ============================================================
        # STEP 3: VALIDAZIONE LLM LOCALE (SEMPRE se regex ha estratto qualcosa)
        # ============================================================
        if dati_regex:  # SEMPRE valida con LLM, non solo 50-85%
            logger.info(f"📊 STEP 3: Validazione LLM dati regex ({completeness_regex:.0%} completo)")
            validation_start = datetime.now()

            # Costruisci prompt con info semantic validation
            context_info = ""
            if semantic_validation and not semantic_validation['valid']:
                context_info = "\n\nERRORI RILEVATI:\n" + "\n".join(f"- {err}" for err in semantic_validation['errors'])
                if semantic_validation['warnings']:
                    context_info += "\n\nAVVISI:\n" + "\n".join(f"- {warn}" for warn in semantic_validation['warnings'])
                context_info += "\n\nCorreggi questi errori nel JSON di output."

            try:
                validation_result = self.regex_validator.validate_extracted_data(
                    dati_regex=dati_regex,
                    testo_originale=testo + context_info,
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

                # Se validazione OK → usa dati regex validati/corretti
                if validation_result.get('is_valid') and validation_result.get('confidence', 0) >= 0.75:
                    # Se LLM ha corretto dati, usali
                    dati_finali = validation_result.get('corrected_data', dati_regex) if validation_result.get('corrected_data') else dati_regex

                    # Ri-valida semanticamente i dati corretti (con testo)
                    final_semantic = self.semantic_validator.validate_all(dati_finali, testo_originale=testo)

                    if final_semantic['valid']:
                        metadata['strategy_final'] = 'regex_llm_corrected' if validation_result.get('corrected_data') else 'regex_validated'
                        metadata['total_time_ms'] = regex_time + metadata.get('semantic_validation', {}).get('time_ms', 0) + validation_time
                        self.stats['regex_corrected' if validation_result.get('corrected_data') else 'regex_validated'] += 1

                        logger.info(f"✅ Dati validati da LLM (confidenza: {validation_result.get('confidence', 0):.2f})")

                        if dati_finali:
                            dati_finali['metadata_estrazione'] = metadata
                        return dati_finali
                    else:
                        logger.warning(f"⚠️ Dati corretti da LLM ma validazione semantica ancora fallisce")

                else:
                    logger.warning(
                        f"⚠️ Validazione fallita: "
                        f"valid={validation_result.get('is_valid')}, "
                        f"confidence={validation_result.get('confidence', 0):.2f}"
                    )

            except Exception as e:
                logger.warning(f"⚠️ Errore validazione: {e}")
                metadata['validation_error'] = str(e)

        # ============================================================
        # STEP 3: LLM LOCALE ESTRAZIONE COMPLETA (se validazione fallita)
        # ============================================================
        if self.local_extractor:
            logger.info(f"📊 STEP 3: Estrazione completa con LLM locale")
            local_start = datetime.now()

            try:
                # Usa LLM locale per estrazione completa
                dati_local = self.local_extractor.extract(testo)

                # QUALITÀ: Se validazione ha confermato alcuni campi regex, uniscili con LLM
                if 'validation_result' in metadata and metadata['validation_result'].get('field_validations'):
                    valid_fields = metadata['validation_result'].get('field_validations', {})
                    for field, validation in valid_fields.items():
                        # Se campo era valido ma LLM locale non l'ha trovato, usa quello di regex
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

                # Se LLM locale ha estratto completamente → usa locale
                if completeness_local >= 0.85 and self.validate_data_quality(dati_local):
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
        # STEP 4: OPENAI FALLBACK (ultimo resort)
        # ============================================================
        if self.openai_extractor:
            logger.info("📊 STEP 3: Fallback a OpenAI")
            openai_start = datetime.now()

            try:
                dati_openai = self.openai_extractor.extract(testo)
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

        # Scegli il migliore tra regex e locale
        best_data = dati_regex
        if self.local_extractor and 'dati_local' in locals():
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

    def get_stats(self) -> Dict[str, Any]:
        """Ritorna statistiche di utilizzo."""
        if self.stats['total'] == 0:
            return self.stats

        return {
            **self.stats,
            'regex_only_pct': (self.stats['regex_only'] / self.stats['total']) * 100,
            'regex_local_pct': (self.stats['regex_local'] / self.stats['total']) * 100,
            'openai_fallback_pct': (self.stats['openai_fallback'] / self.stats['total']) * 100,
        }
