"""
Servizio interpretazione email con LLM
"""

from typing import Dict, Optional, List
import logging
import json

from app.integrations.llm_client import LLMClient
from app.models.email import EmailCategory
from app.services.attachment_extractor import get_attachment_extractor

logger = logging.getLogger(__name__)


class EmailInterpreter:
    """Interprete email"""
    
    def __init__(self):
        self.llm_client = LLMClient()
    
    def interpret(self, categoria: EmailCategory, mittente: str, oggetto: str,
                  corpo: str, allegati: list, data_oggi: str,
                  attachment_paths: Optional[List[str]] = None,
                  allegati_testo: Optional[dict] = None) -> Dict:
        """
        Interpreta email e estrae informazioni strutturate.

        Args:
            categoria: Categoria email
            mittente: Email mittente
            oggetto: Oggetto email
            corpo: Corpo testo email
            allegati: Lista nomi allegati (per retrocompatibilità)
            data_oggi: Data corrente
            attachment_paths: Path completi degli allegati (per estrazione testo)
            allegati_testo: Testo pre-estratto dai PDF (opzionale)

        Returns:
            Dict con informazioni strutturate
        """
        # PARSING BUSTE PEC: Se è una busta PEC, estrai il messaggio reale dall'allegato EML
        is_pec_envelope = 'posta-certificata' in mittente.lower() or 'legalmail' in mittente.lower()

        if attachment_paths and is_pec_envelope:
            # Cerca allegati .eml
            import os
            eml_files = [path for path in attachment_paths if path.lower().endswith('.eml')]

            if eml_files:
                logger.info(f"📧 Rilevata busta PEC con {len(eml_files)} allegati EML - parsing messaggio interno...")
                try:
                    extractor = get_attachment_extractor()
                    # Parsa il primo EML trovato
                    eml_data = extractor.parse_eml_complete(eml_files[0])

                    if eml_data:
                        # Sostituisci mittente, oggetto e corpo con quelli del messaggio interno
                        mittente = eml_data['from']
                        oggetto = eml_data['subject']
                        corpo = eml_data['body']
                        logger.info(f"✅ Dati EML estratti - Mittente reale: {mittente[:50]}, Oggetto: {oggetto[:50]}")
                    else:
                        logger.warning(f"⚠️ Parsing EML fallito, uso dati busta")
                except Exception as e:
                    logger.error(f"❌ Errore parsing busta PEC: {e}")
                    # Continua con i dati della busta se il parsing fallisce

        # Estrai testo dagli allegati se presenti (escludendo EML già parsati e file tecnici PEC)
        attachments_text = ""
        if attachment_paths:
            try:
                extractor = get_attachment_extractor()
                # Filtra file tecnici PEC e EML già parsati
                paths_to_extract = attachment_paths
                if is_pec_envelope:
                    # Non estrarre file tecnici: EML (già usati per parsing), .p7s (firma), .xml (daticert)
                    paths_to_extract = [
                        p for p in attachment_paths
                        if not any(p.lower().endswith(ext) for ext in ['.eml', '.p7s', '.xml'])
                    ]

                if paths_to_extract:
                    attachments_text = extractor.extract_from_attachments(paths_to_extract)
                    if attachments_text:
                        logger.info(f"📎 Estratto testo da {len(paths_to_extract)} allegati per interpretazione")
            except Exception as e:
                logger.warning(f"Errore estrazione testo allegati: {e}")

        # Combina corpo + allegati
        full_text = corpo if corpo else "Non disponibile"
        if attachments_text:
            full_text = f"{full_text}\n\n{attachments_text}"

        # Limita lunghezza per LLM
        full_text = full_text[:5000] if full_text else "Non disponibile"

        prompt = f"""Analizza questa email di categoria "{categoria.value}" ed estrai informazioni in JSON.

EMAIL:
Mittente: {mittente}
Oggetto: {oggetto}
Corpo (include testo allegati se presenti): {full_text}
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
