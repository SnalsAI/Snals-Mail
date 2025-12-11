"""
Smart Generator - Strategia ibrida intelligente per generazione risposte
Strategia: LLM locale (semplici) → OpenAI (complesse) con validazione qualità
"""
import logging
import hashlib
import json
from typing import Dict, Optional, Any, Tuple
from datetime import datetime
from enum import Enum

from app.services.openai_rate_limiter import get_rate_limiter

logger = logging.getLogger(__name__)


class ResponseComplexity(Enum):
    """Livelli di complessità risposta"""
    SIMPLE = "simple"      # Conferme, saluti, sintesi brevi
    MODERATE = "moderate"  # Risposte standard, FAQ
    COMPLEX = "complex"    # Consulenza, analisi, multi-punto


class TaskType(Enum):
    """Tipi di task per classificazione"""
    SINTESI = "sintesi"                    # Sintesi email/documenti
    CONFERMA = "conferma"                  # Conferma ricezione
    RISPOSTA_STANDARD = "risposta_standard"  # Risposta template
    FAQ = "faq"                            # Domanda frequente
    CONSULENZA = "consulenza"              # Consulenza specifica
    ANALISI = "analisi"                    # Analisi documento
    GENERAZIONE_EMAIL = "generazione_email"  # Genera email completa


class SmartResponseGenerator:
    """
    Generatore intelligente con strategia a cascata:
    1. Classifica complessità (tipo task + analisi prompt)
    2. Tenta LLM locale per task semplici/moderati
    3. Valida qualità risposta locale
    4. OpenAI come fallback o per task complessi
    """

    # Mapping tipo task → complessità default
    TASK_COMPLEXITY_MAP = {
        TaskType.SINTESI: ResponseComplexity.SIMPLE,
        TaskType.CONFERMA: ResponseComplexity.SIMPLE,
        TaskType.RISPOSTA_STANDARD: ResponseComplexity.MODERATE,
        TaskType.FAQ: ResponseComplexity.MODERATE,
        TaskType.CONSULENZA: ResponseComplexity.COMPLEX,
        TaskType.ANALISI: ResponseComplexity.COMPLEX,
        TaskType.GENERAZIONE_EMAIL: ResponseComplexity.MODERATE,
    }

    # Parole chiave per rilevamento complessità
    COMPLEX_KEYWORDS = [
        'normativa', 'contratto', 'legge', 'articolo', 'ccnl',
        'diritti', 'doveri', 'giuridico', 'legale', 'specifica',
        'dettagliato', 'approfondito', 'analisi', 'spiegazione'
    ]

    def __init__(self, openai_api_key: str = None, openai_model: str = "gpt-4o-mini", daily_limit_eur: float = 1.0):
        """
        Inizializza generatore smart.

        Args:
            openai_api_key: API key OpenAI (opzionale)
            openai_model: Modello OpenAI da usare
            daily_limit_eur: Limite spesa giornaliera OpenAI
        """
        # LLM locale
        try:
            from app.integrations.llm_client import LLMClient
            self.llm_local = LLMClient()
        except Exception as e:
            logger.warning(f"LLM locale non disponibile: {e}")
            self.llm_local = None

        # OpenAI
        self.openai_client = None
        if openai_api_key:
            try:
                from openai import OpenAI
                self.openai_client = OpenAI(api_key=openai_api_key)
                self.openai_model = openai_model
                # Rate limiter
                self.rate_limiter = get_rate_limiter(daily_limit_eur=daily_limit_eur)
            except Exception as e:
                logger.warning(f"OpenAI non disponibile: {e}")

        # Cache risposte
        self.response_cache = {}

        # Statistiche
        self.stats = {
            'local_only': 0,
            'local_validated': 0,
            'local_fallback_openai': 0,
            'openai_direct': 0,
            'openai_blocked_budget': 0,
            'cache_hits': 0,
            'total': 0
        }

    def classify_complexity(
        self,
        prompt: str,
        task_type: Optional[TaskType] = None,
        max_tokens: int = 300
    ) -> ResponseComplexity:
        """
        Classifica complessità della risposta richiesta.

        Args:
            prompt: Prompt della richiesta
            task_type: Tipo di task (se noto)
            max_tokens: Token massimi richiesti

        Returns:
            ResponseComplexity
        """
        # Se tipo task specificato, usa mapping
        if task_type and task_type in self.TASK_COMPLEXITY_MAP:
            base_complexity = self.TASK_COMPLEXITY_MAP[task_type]
        else:
            base_complexity = ResponseComplexity.MODERATE

        # Analisi lunghezza richiesta
        if max_tokens > 400:
            return ResponseComplexity.COMPLEX

        # Analisi parole chiave complesse
        prompt_lower = prompt.lower()
        complex_count = sum(1 for keyword in self.COMPLEX_KEYWORDS if keyword in prompt_lower)

        if complex_count >= 3:
            return ResponseComplexity.COMPLEX

        # Analisi lunghezza prompt (richieste complesse = prompt dettagliati)
        if len(prompt) > 500:
            # Upgrade complexity
            if base_complexity == ResponseComplexity.SIMPLE:
                return ResponseComplexity.MODERATE
            elif base_complexity == ResponseComplexity.MODERATE:
                return ResponseComplexity.COMPLEX

        return base_complexity

    def validate_response_quality(
        self,
        risposta: str,
        prompt: str,
        min_length: int = 50
    ) -> Tuple[bool, str]:
        """
        Valida qualità risposta LLM locale.

        Args:
            risposta: Risposta generata
            prompt: Prompt originale
            min_length: Lunghezza minima caratteri

        Returns:
            Tuple[bool, str]: (is_valid, reason)
        """
        if not risposta:
            return False, "risposta_vuota"

        # Check lunghezza minima
        if len(risposta) < min_length:
            return False, f"troppo_corta_{len(risposta)}_chars"

        # Check risposta off-topic
        # Estrai parole chiave dal prompt
        prompt_words = set(prompt.lower().split())
        risposta_words = set(risposta.lower().split())

        # Almeno 2 parole in comune (escludendo stopwords)
        stopwords = {'il', 'la', 'di', 'da', 'in', 'con', 'per', 'a', 'un', 'una', 'e', 'o'}
        prompt_keywords = prompt_words - stopwords
        risposta_keywords = risposta_words - stopwords

        common_words = prompt_keywords & risposta_keywords
        if len(common_words) < 2:
            return False, "off_topic"

        # Check errori evidenti
        error_phrases = [
            'non posso',
            'non sono in grado',
            'non ho informazioni',
            'come modello di linguaggio',
            'come ai',
        ]

        risposta_lower = risposta.lower()
        for phrase in error_phrases:
            if phrase in risposta_lower:
                return False, f"error_phrase_{phrase.replace(' ', '_')}"

        return True, "ok"

    def get_cache_key(self, prompt: str, max_tokens: int) -> str:
        """Genera chiave cache per prompt."""
        cache_str = f"{prompt}_{max_tokens}"
        return hashlib.md5(cache_str.encode()).hexdigest()

    def generate(
        self,
        prompt: str,
        task_type: Optional[TaskType] = None,
        max_tokens: int = 300,
        use_cache: bool = True,
        force_openai: bool = False
    ) -> Dict[str, Any]:
        """
        Genera risposta con strategia intelligente.

        Args:
            prompt: Prompt della richiesta
            task_type: Tipo di task (opzionale)
            max_tokens: Token massimi
            use_cache: Usa cache se disponibile
            force_openai: Forza uso OpenAI

        Returns:
            Dict con risposta + metadata
        """
        self.stats['total'] += 1
        start_time = datetime.now()

        metadata = {
            'timestamp': start_time.isoformat(),
            'strategies_attempted': [],
            'total_time_ms': 0
        }

        # Check cache
        if use_cache:
            cache_key = self.get_cache_key(prompt, max_tokens)
            if cache_key in self.response_cache:
                self.stats['cache_hits'] += 1
                cached = self.response_cache[cache_key]
                logger.info(f"💾 Cache hit per prompt (age: {cached['age_minutes']:.1f}min)")
                return {
                    'risposta': cached['risposta'],
                    'metadata': {
                        **metadata,
                        'strategy_final': 'cache',
                        'cache_age_minutes': cached['age_minutes']
                    }
                }

        # Classifica complessità
        complexity = self.classify_complexity(prompt, task_type, max_tokens)
        metadata['complexity'] = complexity.value

        logger.info(f"📊 Complessità rilevata: {complexity.value} (task={task_type.value if task_type else 'auto'})")

        # ============================================================
        # STRATEGIA 1: OpenAI diretto per task complessi
        # ============================================================
        if force_openai or complexity == ResponseComplexity.COMPLEX:
            if self.openai_client:
                return self._generate_openai(prompt, max_tokens, metadata, 'direct_complex')
            else:
                logger.warning("⚠️ OpenAI non disponibile per task complesso")

        # ============================================================
        # STRATEGIA 2: LLM locale con validazione
        # ============================================================
        if self.llm_local and complexity in [ResponseComplexity.SIMPLE, ResponseComplexity.MODERATE]:
            logger.info("🤖 Tentativo con LLM locale")
            local_start = datetime.now()
            metadata['strategies_attempted'].append('ollama_local')

            try:
                # Timeout più breve per task semplici
                timeout = 30 if complexity == ResponseComplexity.SIMPLE else 60

                risposta_local = self.llm_local.generate(
                    prompt=prompt,
                    model_type="generation",
                    max_tokens=max_tokens,
                    timeout=timeout
                )

                local_time = (datetime.now() - local_start).total_seconds() * 1000
                metadata['local_time_ms'] = local_time

                # Valida qualità
                is_valid, reason = self.validate_response_quality(risposta_local, prompt)

                if is_valid:
                    metadata['strategy_final'] = 'local_validated'
                    metadata['total_time_ms'] = local_time
                    metadata['validation'] = 'passed'
                    self.stats['local_validated'] += 1

                    logger.info(f"✅ Risposta locale validata in {local_time:.0f}ms")

                    # Cache risposta
                    if use_cache:
                        self.response_cache[cache_key] = {
                            'risposta': risposta_local,
                            'timestamp': datetime.now(),
                            'age_minutes': 0
                        }

                    return {
                        'risposta': risposta_local,
                        'metadata': metadata
                    }
                else:
                    logger.warning(f"⚠️ Risposta locale non valida: {reason}")
                    metadata['validation'] = f'failed_{reason}'
                    metadata['strategies_attempted'].append('validation_failed')

            except Exception as e:
                logger.warning(f"⚠️ LLM locale fallito: {e}")
                metadata['local_error'] = str(e)

        # ============================================================
        # STRATEGIA 3: OpenAI fallback
        # ============================================================
        if self.openai_client:
            logger.info("📊 Fallback a OpenAI")
            return self._generate_openai(prompt, max_tokens, metadata, 'fallback')

        # ============================================================
        # FALLBACK FINALE: risposta locale senza validazione
        # ============================================================
        logger.error("❌ Nessuna strategia disponibile")
        return {
            'risposta': None,
            'metadata': {
                **metadata,
                'strategy_final': 'failed',
                'error': 'no_strategy_available'
            }
        }

    def _generate_openai(
        self,
        prompt: str,
        max_tokens: int,
        metadata: Dict,
        reason: str
    ) -> Dict[str, Any]:
        """
        Genera risposta con OpenAI.

        Args:
            prompt: Prompt
            max_tokens: Token massimi
            metadata: Metadata da aggiornare
            reason: Motivo uso OpenAI (direct_complex, fallback)

        Returns:
            Dict con risposta + metadata
        """
        # Check budget
        if not self.rate_limiter.can_make_request(estimated_cost_eur=0.0005):
            remaining = self.rate_limiter.get_remaining_budget()
            logger.warning(f"🚫 Budget OpenAI esaurito (rimanente: €{remaining:.4f})")
            self.stats['openai_blocked_budget'] += 1

            metadata['strategy_final'] = 'blocked_budget'
            metadata['budget_remaining_eur'] = remaining

            return {
                'risposta': None,
                'metadata': metadata,
                'error': 'budget_exceeded'
            }

        openai_start = datetime.now()
        metadata['strategies_attempted'].append('openai')

        try:
            response = self.openai_client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {'role': 'system', 'content': 'Sei un esperto del sistema scolastico italiano e assistente del sindacato SNALS.'},
                    {'role': 'user', 'content': prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.3
            )

            risposta = response.choices[0].message.content
            openai_time = (datetime.now() - openai_start).total_seconds() * 1000

            # Calcola costo
            costo_input = (response.usage.prompt_tokens / 1_000_000) * 0.15
            costo_output = (response.usage.completion_tokens / 1_000_000) * 0.60
            costo_totale_usd = costo_input + costo_output
            costo_totale_eur = costo_totale_usd * 0.95

            # Registra nel rate limiter
            usage_info = self.rate_limiter.record_request(
                cost_eur=costo_totale_eur,
                tokens_prompt=response.usage.prompt_tokens,
                tokens_completion=response.usage.completion_tokens,
                model=self.openai_model
            )

            metadata['openai_time_ms'] = openai_time
            metadata['openai_tokens'] = {
                'prompt': response.usage.prompt_tokens,
                'completion': response.usage.completion_tokens,
                'total': response.usage.total_tokens
            }
            metadata['openai_cost_eur'] = costo_totale_eur
            metadata['openai_budget'] = {
                'today_total_eur': usage_info['today_total_eur'],
                'remaining_eur': usage_info['remaining_budget_eur'],
                'used_pct': usage_info['budget_used_pct']
            }
            metadata['strategy_final'] = f'openai_{reason}'
            metadata['total_time_ms'] = metadata.get('local_time_ms', 0) + openai_time

            if reason == 'direct_complex':
                self.stats['openai_direct'] += 1
            else:
                self.stats['local_fallback_openai'] += 1

            logger.info(f"✅ OpenAI completato in {openai_time:.0f}ms (€{metadata['openai_cost_eur']:.6f})")

            return {
                'risposta': risposta,
                'metadata': metadata
            }

        except Exception as e:
            logger.error(f"❌ OpenAI fallito: {e}")
            metadata['openai_error'] = str(e)
            return {
                'risposta': None,
                'metadata': metadata
            }

    def get_stats(self) -> Dict[str, Any]:
        """Ritorna statistiche di utilizzo."""
        if self.stats['total'] == 0:
            return self.stats

        return {
            **self.stats,
            'local_validated_pct': (self.stats['local_validated'] / self.stats['total']) * 100,
            'openai_usage_pct': ((self.stats['openai_direct'] + self.stats['local_fallback_openai']) / self.stats['total']) * 100,
            'cache_hit_rate': (self.stats['cache_hits'] / (self.stats['total'] + self.stats['cache_hits'])) * 100,
        }

    def clear_cache(self):
        """Pulisce cache risposte."""
        self.response_cache = {}
        logger.info("🗑️ Cache risposte pulita")
