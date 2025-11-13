"""
Client LLM - Supporto Ollama e OpenAI
"""

import httpx
from openai import OpenAI
from typing import Dict, Optional
import json
import logging

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class LLMClient:
    """Client LLM unificato"""
    
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
    
    def generate(self, prompt: str, model_type: str = "categorization",
                 format_json: bool = False, max_tokens: int = 1000,
                 temperature: float = 0.3) -> str:
        """Genera completion"""
        if self.provider == "ollama":
            return self._generate_ollama(prompt, model_type, format_json, temperature)
        else:
            return self._generate_openai(prompt, max_tokens, temperature)
    
    def _generate_ollama(self, prompt: str, model_type: str,
                        format_json: bool, temperature: float) -> str:
        """Genera con Ollama"""
        
        model_map = {
            "categorization": self.model_categorization,
            "interpretation": self.model_interpretation,
            "generation": self.model_generation
        }
        model = model_map.get(model_type, self.model_categorization)
        
        try:
            with httpx.Client(timeout=60.0) as client:
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
                return result.get("response", "")
        
        except Exception as e:
            logger.error(f"Errore Ollama: {e}")
            raise
    
    def _generate_openai(self, prompt: str, max_tokens: int, temperature: float) -> str:
        """Genera con OpenAI"""
        
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
            return completion.choices[0].message.content
        
        except Exception as e:
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
