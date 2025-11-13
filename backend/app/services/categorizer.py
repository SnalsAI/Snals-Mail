"""
Servizio categorizzazione email con LLM
"""

from typing import Tuple
import logging

from app.integrations.llm_client import LLMClient
from app.models.email import EmailCategory

logger = logging.getLogger(__name__)


class EmailCategorizer:
    """Categorizzatore email"""
    
    PROMPT_TEMPLATE = """Sei un assistente esperto nella categorizzazione di email per il sindacato scuola SNALS.

Analizza questa email e categorizzala in UNA delle seguenti categorie:

CATEGORIE:
1. info_generiche - Richieste di informazioni generiche
2. richiesta_appuntamento - Richieste di appuntamento
3. richiesta_tesseramento - Richieste di iscrizione
4. convocazione_scuola - Convocazioni da scuole
5. comunicazione_ust_usr - Comunicazioni UST/USR
6. comunicazione_scuola - Comunicazioni scuole
7. comunicazione_snals_centrale - Comunicazioni SNALS centrale
8. varie - Altro

EMAIL:
Mittente: {mittente}
Oggetto: {oggetto}
Corpo: {corpo}

Rispondi SOLO con JSON:
{{
  "categoria": "nome_categoria",
  "confidence": 0.95,
  "motivazione": "spiegazione"
}}
"""

    def __init__(self):
        self.llm_client = LLMClient()
    
    def categorize(self, mittente: str, oggetto: str, corpo: str) -> Tuple[EmailCategory, float]:
        """Categorizza email"""
        
        prompt = self.PROMPT_TEMPLATE.format(
            mittente=mittente,
            oggetto=oggetto,
            corpo=corpo[:2000]
        )
        
        try:
            response = self.llm_client.generate(
                prompt=prompt,
                model_type="categorization",
                format_json=True,
                temperature=0.2
            )
            
            result = self.llm_client.parse_json_response(response)
            
            if not result:
                return EmailCategory.VARIE, 0.5
            
            categoria_str = result.get("categoria", "varie")
            confidence = float(result.get("confidence", 0.5))
            
            try:
                categoria = EmailCategory[categoria_str.upper()]
            except KeyError:
                categoria = EmailCategory.VARIE
                confidence = 0.5
            
            logger.info(f"Categorizzata come {categoria.value} (conf: {confidence})")
            return categoria, confidence
        
        except Exception as e:
            logger.error(f"Errore categorizzazione: {e}")
            return EmailCategory.VARIE, 0.0
