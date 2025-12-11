"""
Client LLM - Supporto Ollama e OpenAI
Con tracking delle chiamate API e token utilizzati
"""

import httpx
from openai import OpenAI
from typing import Dict, Optional, List
import json
import logging
from datetime import datetime, timedelta
from collections import defaultdict
import threading

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class LLMStatsTracker:
    """Singleton per tracciare statistiche chiamate LLM con persistenza su file"""
    _instance = None
    _lock = threading.Lock()
    _stats_file = None

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        # Path per file statistiche
        from pathlib import Path
        self._stats_file = Path(__file__).parent.parent / "data" / "llm_stats.json"
        self._stats_file.parent.mkdir(parents=True, exist_ok=True)
        # Prova a caricare stats esistenti, altrimenti reset
        if not self._load_stats():
            self.reset_stats()

    def reset_stats(self, save: bool = True):
        """Reset tutte le statistiche"""
        self.total_calls = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.calls_by_provider = defaultdict(int)
        self.calls_by_model = defaultdict(int)
        self.calls_by_type = defaultdict(int)  # categorization, interpretation, etc.
        self.tokens_by_provider = defaultdict(lambda: {"input": 0, "output": 0})
        self.errors = 0
        self.last_reset = datetime.utcnow()
        self.recent_calls: List[Dict] = []  # Ultimi 100 chiamate
        self.daily_stats = defaultdict(lambda: {"calls": 0, "tokens": 0})
        if save:
            self._save_stats()

    def _load_stats(self) -> bool:
        """Carica statistiche da file. Ritorna True se caricato con successo."""
        try:
            if self._stats_file and self._stats_file.exists():
                with open(self._stats_file, 'r') as f:
                    data = json.load(f)
                self.total_calls = data.get("total_calls", 0)
                self.total_input_tokens = data.get("total_input_tokens", 0)
                self.total_output_tokens = data.get("total_output_tokens", 0)
                self.calls_by_provider = defaultdict(int, data.get("calls_by_provider", {}))
                self.calls_by_model = defaultdict(int, data.get("calls_by_model", {}))
                self.calls_by_type = defaultdict(int, data.get("calls_by_type", {}))
                # Ricostruisci tokens_by_provider con defaultdict
                self.tokens_by_provider = defaultdict(lambda: {"input": 0, "output": 0})
                for k, v in data.get("tokens_by_provider", {}).items():
                    self.tokens_by_provider[k] = v
                self.errors = data.get("errors", 0)
                self.last_reset = datetime.fromisoformat(data.get("last_reset", datetime.utcnow().isoformat()))
                self.recent_calls = data.get("recent_calls", [])[-100:]  # Max 100
                # Ricostruisci daily_stats con defaultdict
                self.daily_stats = defaultdict(lambda: {"calls": 0, "tokens": 0})
                for k, v in data.get("daily_stats", {}).items():
                    self.daily_stats[k] = v
                logger.info(f"📊 Stats LLM caricate: {self.total_calls} chiamate, {self.total_input_tokens + self.total_output_tokens} token totali")
                return True
        except Exception as e:
            logger.warning(f"⚠️ Impossibile caricare stats LLM: {e}")
        return False

    def _save_stats(self):
        """Salva statistiche su file."""
        try:
            if not self._stats_file:
                return
            data = {
                "total_calls": self.total_calls,
                "total_input_tokens": self.total_input_tokens,
                "total_output_tokens": self.total_output_tokens,
                "calls_by_provider": dict(self.calls_by_provider),
                "calls_by_model": dict(self.calls_by_model),
                "calls_by_type": dict(self.calls_by_type),
                "tokens_by_provider": dict(self.tokens_by_provider),
                "errors": self.errors,
                "last_reset": self.last_reset.isoformat(),
                "recent_calls": self.recent_calls[-100:],
                "daily_stats": dict(self.daily_stats)
            }
            with open(self._stats_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"⚠️ Impossibile salvare stats LLM: {e}")

    def record_call(self, provider: str, model: str, call_type: str,
                   input_tokens: int, output_tokens: int,
                   duration_ms: float, success: bool = True):
        """Registra una chiamata API"""
        with self._lock:
            self.total_calls += 1
            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens
            self.calls_by_provider[provider] += 1
            self.calls_by_model[model] += 1
            self.calls_by_type[call_type] += 1
            self.tokens_by_provider[provider]["input"] += input_tokens
            self.tokens_by_provider[provider]["output"] += output_tokens

            if not success:
                self.errors += 1

            # Daily stats
            today = datetime.utcnow().strftime("%Y-%m-%d")
            self.daily_stats[today]["calls"] += 1
            self.daily_stats[today]["tokens"] += input_tokens + output_tokens

            # Recent calls (max 100)
            call_record = {
                "timestamp": datetime.utcnow().isoformat(),
                "provider": provider,
                "model": model,
                "type": call_type,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "duration_ms": duration_ms,
                "success": success
            }
            self.recent_calls.append(call_record)
            if len(self.recent_calls) > 100:
                self.recent_calls.pop(0)

            # Salva stats su file
            self._save_stats()

    def get_stats(self) -> Dict:
        """Restituisce statistiche correnti"""
        with self._lock:
            # Calcola stats ultimi 7 giorni
            last_7_days = {}
            for i in range(7):
                day = (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
                last_7_days[day] = self.daily_stats.get(day, {"calls": 0, "tokens": 0})

            return {
                "total_calls": self.total_calls,
                "total_input_tokens": self.total_input_tokens,
                "total_output_tokens": self.total_output_tokens,
                "total_tokens": self.total_input_tokens + self.total_output_tokens,
                "calls_by_provider": dict(self.calls_by_provider),
                "calls_by_model": dict(self.calls_by_model),
                "calls_by_type": dict(self.calls_by_type),
                "tokens_by_provider": {k: dict(v) for k, v in self.tokens_by_provider.items()},
                "errors": self.errors,
                "error_rate": f"{(self.errors / self.total_calls * 100):.1f}%" if self.total_calls > 0 else "0%",
                "last_reset": self.last_reset.isoformat(),
                "uptime_hours": (datetime.utcnow() - self.last_reset).total_seconds() / 3600,
                "recent_calls": self.recent_calls[-20:],  # Ultime 20
                "daily_stats": last_7_days
            }


# Singleton instance
llm_stats = LLMStatsTracker()


class LLMClient:
    """Client LLM unificato con rate limiting e gestione coda"""

    # Semaforo globale per limitare chiamate concorrenti
    _concurrent_limit = threading.Semaphore(3)  # Max 3 chiamate simultanee
    _call_queue_lock = threading.Lock()
    _last_call_time = 0
    _min_interval = 0.5  # Minimo 500ms tra chiamate

    def __init__(self):
        self.provider = settings.LLM_PROVIDER

        if self.provider == "ollama":
            self.ollama_base_url = settings.OLLAMA_BASE_URL
            self.model_categorization = settings.OLLAMA_MODEL_CATEGORIZATION
            self.model_interpretation = settings.OLLAMA_MODEL_INTERPRETATION
            self.model_generation = settings.OLLAMA_MODEL_GENERATION

        elif self.provider == "openai":
            self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
            self.model = settings.OPENAI_MODEL

    def _wait_for_rate_limit(self):
        """Attende se necessario per rispettare rate limit"""
        import time
        with self._call_queue_lock:
            now = time.time()
            elapsed = now - LLMClient._last_call_time
            if elapsed < self._min_interval:
                sleep_time = self._min_interval - elapsed
                time.sleep(sleep_time)
            LLMClient._last_call_time = time.time()
    
    def generate(self, prompt: str, model_type: str = "categorization",
                 format_json: bool = False, max_tokens: int = 1000,
                 temperature: float = 0.3, timeout: float = 120.0) -> str:
        """
        Genera completion con rate limiting e gestione coda.

        Usa semaforo per limitare chiamate concorrenti e evitare sovraccarichi.
        """
        # Attendi slot disponibile (max 3 chiamate simultanee)
        acquired = self._concurrent_limit.acquire(timeout=timeout)
        if not acquired:
            logger.warning("⚠️ Timeout attesa slot LLM - troppo traffico")
            return None

        try:
            # Rate limiting tra chiamate
            self._wait_for_rate_limit()

            if self.provider == "ollama":
                return self._generate_ollama(prompt, model_type, format_json, temperature, timeout)
            else:
                return self._generate_openai(prompt, max_tokens, temperature)
        finally:
            self._concurrent_limit.release()
    
    def _generate_ollama(self, prompt: str, model_type: str,
                        format_json: bool, temperature: float, timeout: float = 120.0) -> str:
        """Genera con Ollama"""
        import time

        model_map = {
            "categorization": self.model_categorization,
            "interpretation": self.model_interpretation,
            "generation": self.model_generation,
            "validation": self.model_categorization  # Usa stesso modello per validazione
        }
        model = model_map.get(model_type, self.model_categorization)

        start_time = time.time()
        success = True

        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(
                    f"{self.ollama_base_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json" if format_json else None,
                        "options": {
                            "temperature": temperature
                        }
                    }
                )
                response.raise_for_status()
                result = response.json()

                # Estrai token counts da Ollama response
                input_tokens = result.get("prompt_eval_count", len(prompt) // 4)  # Stima se non disponibile
                output_tokens = result.get("eval_count", len(result.get("response", "")) // 4)

                duration_ms = (time.time() - start_time) * 1000

                # Registra stats
                llm_stats.record_call(
                    provider="ollama",
                    model=model,
                    call_type=model_type,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    duration_ms=duration_ms,
                    success=True
                )

                return result.get("response", "")

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            llm_stats.record_call(
                provider="ollama",
                model=model,
                call_type=model_type,
                input_tokens=len(prompt) // 4,
                output_tokens=0,
                duration_ms=duration_ms,
                success=False
            )
            logger.error(f"Errore Ollama: {e}")
            raise
    
    def _generate_openai(self, prompt: str, max_tokens: int, temperature: float,
                         model_type: str = "categorization") -> str:
        """Genera con OpenAI"""
        import time

        start_time = time.time()

        try:
            completion = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Sei un assistente esperto per il sindacato SNALS."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )

            duration_ms = (time.time() - start_time) * 1000

            # OpenAI fornisce token usage
            input_tokens = completion.usage.prompt_tokens if completion.usage else len(prompt) // 4
            output_tokens = completion.usage.completion_tokens if completion.usage else 0

            llm_stats.record_call(
                provider="openai",
                model=self.model,
                call_type=model_type,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                duration_ms=duration_ms,
                success=True
            )

            return completion.choices[0].message.content

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            llm_stats.record_call(
                provider="openai",
                model=self.model,
                call_type=model_type,
                input_tokens=len(prompt) // 4,
                output_tokens=0,
                duration_ms=duration_ms,
                success=False
            )
            logger.error(f"Errore OpenAI: {e}")
            raise
    
    def parse_json_response(self, response: str) -> Optional[Dict]:
        """Parse risposta JSON dal LLM"""
        try:
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            
            response = response.strip()
            return json.loads(response)
        
        except Exception as e:
            logger.error(f"Errore parse JSON: {e}")
            return None
