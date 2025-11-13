"""
Servizio interpretazione email con LLM
"""

from typing import Dict
import logging
import json

from app.integrations.llm_client import LLMClient
from app.models.email import EmailCategory

logger = logging.getLogger(__name__)


class EmailInterpreter:
    """Interprete email"""
    
    def __init__(self):
        self.llm_client = LLMClient()
    
    def interpret(self, categoria: EmailCategory, mittente: str, oggetto: str,
                  corpo: str, allegati: list, data_oggi: str) -> Dict:
        """Interpreta email e estrae informazioni strutturate"""
        
        prompt = f"""Analizza questa email di categoria "{categoria.value}" ed estrai informazioni in JSON.

EMAIL:
Mittente: {mittente}
Oggetto: {oggetto}
Corpo: {corpo[:3000]}
Allegati: {', '.join(allegati) if allegati else 'nessuno'}

Data oggi: {data_oggi}

Estrai tutte le informazioni rilevanti in formato JSON.
Per convocazioni estrai: data, ora, luogo, scuola, argomento.
Per richieste appuntamento: disponibilità, argomento, modalità.

Rispondi SOLO con JSON valido."""
        
        try:
            response = self.llm_client.generate(
                prompt=prompt,
                model_type="interpretation",
                format_json=True,
                temperature=0.3
            )
            
            result = self.llm_client.parse_json_response(response)
            
            if not result:
                return {"error": "parsing_failed"}
            
            logger.info(f"Interpretazione completata per categoria {categoria.value}")
            return result
        
        except Exception as e:
            logger.error(f"Errore interpretazione: {e}")
            return {"error": str(e)}
