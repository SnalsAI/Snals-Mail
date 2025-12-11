"""
Regex Validator - LLM locale valida dati estratti da regex
"""
import logging
import json
from typing import Dict, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class RegexValidator:
    """
    Usa LLM locale per validare dati estratti da regex.
    Più veloce ed economico che riestrarre tutto.
    """

    def __init__(self, llm_client=None):
        """
        Inizializza validatore.

        Args:
            llm_client: Client LLM locale (opzionale)
        """
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
        timeout: float = 45.0  # Usa modello veloce (1b) - 45s per safety margin
    ) -> Dict[str, Any]:
        """
        Valida dati estratti da regex usando LLM locale.

        Args:
            dati_regex: Dati estratti da regex
            testo_originale: Testo originale da cui sono stati estratti
            timeout: Timeout per LLM

        Returns:
            Dict con:
            - is_valid: bool (validazione superata)
            - confidence: float 0-1 (confidenza generale)
            - field_validations: dict con validazione per campo
            - validation_time_ms: tempo validazione
        """
        if not self.llm_client:
            logger.warning("⚠️ LLM non disponibile, skip validazione")
            return {
                'is_valid': True,  # Assume valido se non può validare
                'confidence': 0.7,  # Confidenza media
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

        # Costruisci prompt di validazione
        prompt = self._build_validation_prompt(dati_regex, testo_originale)

        logger.info(f"🔍 Validazione LLM per {len(dati_regex)} campi estratti da regex")

        try:
            # Chiama LLM con modello VELOCE (generation = llama3.2:1b)
            # Validazione è task semplice (yes/no), non serve modello grande
            response = self.llm_client.generate(
                prompt=prompt,
                model_type="generation",  # llama3.2:1b - molto più veloce!
                format_json=True,
                max_tokens=300,  # Ridotto da 500 - validazione breve
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

                # Considera valido se:
                # 1. Tutti i campi critici sono validi
                # 2. Confidenza generale >= 0.75
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

    def _extract_context_around_match(self, testo: str, pattern: str, window: int = 400) -> str:
        """
        Estrae il contesto intorno a un pattern trovato nel testo.

        Args:
            testo: Testo completo
            pattern: Pattern da cercare (es: codice scuola, email)
            window: Caratteri da prendere prima e dopo

        Returns:
            str: Contesto estratto o testo troncato se pattern non trovato
        """
        import re

        # Cerca il pattern nel testo
        match = re.search(re.escape(pattern), testo, re.IGNORECASE)
        if match:
            start = max(0, match.start() - window)
            end = min(len(testo), match.end() + window)
            context = testo[start:end]
            return f"...{context}..."

        return testo[:1500]

    def _build_validation_prompt(self, dati_regex: Dict, testo: str) -> str:
        """
        Costruisce prompt di validazione per LLM.

        Args:
            dati_regex: Dati da validare
            testo: Testo originale

        Returns:
            str: Prompt formattato
        """
        import re

        # Formatta campi estratti
        campi_estratti = "\n".join([
            f"- {campo}: {valore}"
            for campo, valore in dati_regex.items()
        ])

        # Estrai contesto focalizzato intorno ai dati chiave
        contesto_focalizzato = ""

        # 1. Cerca contesto intorno al codice scuola (se presente nell'istituto o provincia)
        # Pattern per trovare codice meccanografico nel testo
        codice_pattern = re.search(r'([A-Z]{4}\d{5}[A-Z0-9]?)@', testo, re.IGNORECASE)
        if codice_pattern:
            codice = codice_pattern.group(1)
            contesto_focalizzato += f"\n--- CONTESTO CODICE SCUOLA {codice.upper()} ---\n"
            contesto_focalizzato += self._extract_context_around_match(testo, codice, 500)

        # 2. Cerca contesto intorno a "Sede di servizio" (indica la scuola reale)
        if "sede di servizio" in testo.lower():
            contesto_focalizzato += f"\n--- CONTESTO SEDE DI SERVIZIO ---\n"
            contesto_focalizzato += self._extract_context_around_match(testo, "Sede di servizio", 300)

        # 3. Se trovato istituto, cerca contesto intorno
        if dati_regex.get('istituto'):
            contesto_focalizzato += f"\n--- CONTESTO ISTITUTO ---\n"
            contesto_focalizzato += self._extract_context_around_match(testo, dati_regex['istituto'], 300)

        # Fallback: se non trovato niente, usa inizio testo
        if not contesto_focalizzato:
            contesto_focalizzato = f"TESTO (primi 1500 caratteri):\n{testo[:1500]}"

        prompt = f"""Valida questi dati estratti da un interpello scolastico.

DATI ESTRATTI:
{campi_estratti}

CONTESTO RILEVANTE (estratto intorno ai punti chiave):
{contesto_focalizzato}

DOMANDA CHIAVE: La provincia "{dati_regex.get('provincia', 'N/A')}" è quella della SCUOLA o dell'USP che inoltra?
- Se vedi "Sede di servizio: ... [città]" → quella è la città giusta
- Se vedi codice tipo "PSRI..." → PS = Pesaro, TA = Taranto, FI = Firenze
- USP che inoltra ≠ scuola del posto!

RISPOSTA JSON:
{{
  "field_validations": {{
    "provincia": {{"valid": true/false, "confidence": 0.0-1.0, "correct_value": "nome provincia se diversa"}},
    "classe_concorso": {{"valid": true/false, "confidence": 0.0-1.0}},
    "ore_settimanali": {{"valid": true/false, "confidence": 0.0-1.0}}
  }}
}}

Se provincia sbagliata, indica in correct_value la provincia corretta."""

        return prompt

    def _parse_validation_response(self, response: str) -> Optional[Dict]:
        """
        Parse risposta JSON da LLM.

        Args:
            response: Risposta LLM (possibilmente con JSON dentro)

        Returns:
            Dict parsed o None se fallisce
        """
        try:
            # Prova parsing diretto
            return json.loads(response)
        except json.JSONDecodeError:
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


def validate_regex_with_llm(
    dati_regex: Dict[str, Any],
    testo: str,
    llm_client=None
) -> Dict[str, Any]:
    """
    Helper function per validazione rapida.

    Args:
        dati_regex: Dati da validare
        testo: Testo originale
        llm_client: Client LLM (opzionale)

    Returns:
        Dict con risultato validazione
    """
    validator = RegexValidator(llm_client=llm_client)
    return validator.validate_extracted_data(dati_regex, testo)
