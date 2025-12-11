"""
Training Service - Genera training data per spaCy/BERT usando ChatGPT come "teacher".

Workflow:
1. Seleziona email per training
2. Invia a ChatGPT per estrazione entità
3. Salva risultati come training data annotati
4. Esporta in formato spaCy/BERT per fine-tuning

Supporta operazioni asincrone per evitare timeout:
- analyze_batch_async: Analisi batch in background
- run_benchmark_async: Benchmark in background
- get_job_status: Verifica stato job
"""

import json
import logging
import os
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import hashlib

logger = logging.getLogger(__name__)

# Directory per training data
TRAINING_DATA_DIR = Path(__file__).parent.parent / "data" / "training"
TRAINING_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Job storage per operazioni asincrone
_async_jobs: Dict[str, Dict[str, Any]] = {}


class TrainingService:
    """Servizio per generazione training data."""

    def __init__(self):
        from app.config import get_settings
        settings = get_settings()
        self.openai_api_key = getattr(settings, 'OPENAI_API_KEY', None) or os.getenv('OPENAI_API_KEY')
        self.openai_model = getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini') or os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        self._training_cache_file = TRAINING_DATA_DIR / "training_samples.json"
        self._load_training_data()

    def _load_training_data(self):
        """Carica training data esistenti."""
        self.training_samples = []
        if self._training_cache_file.exists():
            try:
                with open(self._training_cache_file, 'r', encoding='utf-8') as f:
                    self.training_samples = json.load(f)
                logger.info(f"✅ Caricati {len(self.training_samples)} training samples")
            except Exception as e:
                logger.warning(f"⚠️ Errore caricamento training data: {e}")

    def _save_training_data(self):
        """Salva training data su file."""
        try:
            with open(self._training_cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.training_samples, f, ensure_ascii=False, indent=2)
            logger.info(f"✅ Salvati {len(self.training_samples)} training samples")
        except Exception as e:
            logger.error(f"❌ Errore salvataggio training data: {e}")

    def is_openai_available(self) -> bool:
        """Verifica se OpenAI è disponibile."""
        return bool(self.openai_api_key)

    def analyze_email_with_chatgpt(
        self,
        email_id: int,
        oggetto: str,
        corpo: str,
        allegati_testo: Optional[Dict[str, str]] = None,
        tipo: str = "interpello"
    ) -> Dict[str, Any]:
        """
        Analizza email con ChatGPT per estrarre entità.

        Args:
            email_id: ID email nel database
            oggetto: Oggetto email
            corpo: Corpo email
            allegati_testo: Testo estratto dagli allegati
            tipo: Tipo di estrazione (interpello, calendario, categorizzazione)

        Returns:
            Dict con entità estratte e metadati
        """
        if not self.is_openai_available():
            raise ValueError("OpenAI API key non configurata")

        # Costruisci testo completo
        testo_completo = f"Oggetto: {oggetto}\n\n{corpo or ''}"
        if allegati_testo:
            for filename, testo in allegati_testo.items():
                if testo:
                    testo_completo += f"\n\n--- {filename} ---\n{testo[:2000]}"

        # Hash per evitare duplicati
        text_hash = hashlib.md5(testo_completo.encode()).hexdigest()[:16]

        # Chiedi a ChatGPT
        result = self._call_chatgpt(testo_completo, tipo)

        # Prepara training sample
        training_sample = {
            "id": f"{email_id}_{text_hash}",
            "email_id": email_id,
            "timestamp": datetime.now().isoformat(),
            "type": tipo,
            "text": testo_completo[:5000],  # Limita per storage
            "text_hash": text_hash,
            "openai_extraction": result.get("extraction", {}),
            "openai_model": self.openai_model,
            "entities": self._convert_to_spacy_format(testo_completo, result.get("extraction", {})),
            "approved": False,
            "corrections": {}
        }

        # Aggiungi ai samples (evita duplicati)
        existing_ids = {s["id"] for s in self.training_samples}
        if training_sample["id"] not in existing_ids:
            self.training_samples.append(training_sample)
            self._save_training_data()

        return training_sample

    def _call_chatgpt(self, testo: str, tipo: str) -> Dict[str, Any]:
        """Chiama ChatGPT per estrazione entità."""
        import httpx
        import time
        from app.integrations.llm_client import llm_stats

        # Prompt specifico per tipo
        if tipo == "interpello":
            prompt = self._get_interpello_prompt(testo)
        elif tipo == "calendario":
            prompt = self._get_calendario_prompt(testo)
        else:
            prompt = self._get_generic_prompt(testo)

        start_time = time.time()
        input_tokens = 0
        output_tokens = 0
        success = True

        try:
            response = httpx.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openai_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.openai_model,
                    "messages": [
                        {"role": "system", "content": "Sei un assistente specializzato nell'estrazione di entità da documenti scolastici italiani. Rispondi SOLO con JSON valido."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 2000
                },
                timeout=60.0
            )
            response.raise_for_status()

            result = response.json()
            content = result["choices"][0]["message"]["content"]

            # Estrai token usage se disponibile
            usage = result.get("usage", {})
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)

            # Registra chiamata API
            duration_ms = (time.time() - start_time) * 1000
            llm_stats.record_call(
                provider="openai",
                model=self.openai_model,
                call_type=f"training_{tipo}",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                duration_ms=duration_ms,
                success=True
            )
            logger.info(f"📊 ChatGPT call tracked: {input_tokens}+{output_tokens} tokens, {duration_ms:.0f}ms")

            # Parse JSON dalla risposta
            try:
                # Rimuovi markdown se presente
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]

                extraction = json.loads(content.strip())
                return {"extraction": extraction, "raw_response": content}
            except json.JSONDecodeError:
                logger.warning(f"⚠️ Risposta ChatGPT non è JSON valido: {content[:200]}")
                return {"extraction": {}, "raw_response": content, "error": "Invalid JSON"}

        except Exception as e:
            logger.error(f"❌ Errore ChatGPT: {e}")
            # Registra errore
            duration_ms = (time.time() - start_time) * 1000
            llm_stats.record_call(
                provider="openai",
                model=self.openai_model,
                call_type=f"training_{tipo}",
                input_tokens=0,
                output_tokens=0,
                duration_ms=duration_ms,
                success=False
            )
            return {"extraction": {}, "error": str(e)}

    def _get_interpello_prompt(self, testo: str) -> str:
        """Prompt per estrazione interpello."""
        return f"""Analizza questo testo di un interpello scolastico italiano ed estrai tutte le entità.

TESTO:
{testo[:4000]}

Estrai e restituisci un JSON con questi campi (usa null se non trovato):
{{
    "classe_concorso": "codice classe concorso (es: A-42, A012, AA24)",
    "ore_settimanali": numero ore (intero),
    "data_scadenza": "data in formato YYYY-MM-DD",
    "provincia": "sigla provincia (es: TA, MI, RM)",
    "citta": "nome città",
    "istituto": "nome istituto/scuola",
    "meccanografico": "codice meccanografico scuola (es: TAIC824001)",
    "indirizzo": "via e numero civico",
    "email_contatto": "email riferimento",
    "telefono_contatto": "numero telefono",
    "referente": "nome persona di riferimento",
    "entities": [
        {{"text": "testo entità", "label": "TIPO", "start": posizione_inizio, "end": posizione_fine}}
    ]
}}

Nel campo "entities" includi TUTTE le entità trovate con i seguenti label:
- CLASSE_CONCORSO: codici classe concorso
- MECCANOGRAFICO: codici meccanografici scuole
- ISTITUTO: nomi di scuole/istituti
- PROVINCIA: sigle province (2 lettere)
- LOC: località/città
- DATE: date
- ORG: organizzazioni
- PER: persone
- EMAIL: indirizzi email
- PHONE: numeri telefono

Rispondi SOLO con il JSON, senza spiegazioni."""

    def _get_calendario_prompt(self, testo: str) -> str:
        """Prompt per estrazione evento calendario."""
        return f"""Analizza questo testo di una convocazione/riunione scolastica italiana ed estrai tutte le informazioni.

TESTO:
{testo[:4000]}

Estrai e restituisci un JSON con questi campi (usa null se non trovato):
{{
    "data_inizio": "data in formato YYYY-MM-DD",
    "ora_inizio": "orario in formato HH:MM",
    "data_fine": "data fine (se diversa da inizio)",
    "ora_fine": "orario fine",
    "luogo": "sede della riunione (aula, sala, indirizzo)",
    "modalita": "presenza/online/mista",
    "link_meet": "link per riunione online se presente",

    "scuola_nome": "nome completo della scuola che convoca (es: IC MANZONI, Liceo Archita)",
    "scuola_codice": "codice meccanografico scuola (es: TAIC824001, TAPS03000P)",
    "scuola_comune": "comune della scuola",
    "scuola_indirizzo": "indirizzo della scuola",

    "tipo_riunione": "tipo di riunione (collegio_docenti/consiglio_istituto/assemblea_sindacale/contrattazione/rsu/incontro/altro)",
    "motivo_convocazione": "motivo o argomento principale della convocazione (es: approvazione POF, elezioni RSU, contrattazione integrativa)",
    "ordine_del_giorno": ["lista punti all'ordine del giorno se presenti"],

    "organizzatore": "chi convoca (dirigente scolastico, RSU, sindacato)",
    "organizzatore_nome": "nome della persona che convoca",
    "partecipanti": ["categorie di partecipanti: docenti, ATA, RSU, delegati sindacali"],

    "urgente": true/false,
    "risposta_richiesta": true/false,
    "scadenza_risposta": "data entro cui rispondere se richiesta",

    "contatto_email": "email per informazioni",
    "contatto_telefono": "telefono per informazioni",

    "entities": [
        {{"text": "testo entità", "label": "TIPO", "start": posizione_inizio, "end": posizione_fine}}
    ]
}}

Nel campo "entities" includi tutte le entità trovate con questi label:
- ISTITUTO: nomi di scuole/istituti
- MECCANOGRAFICO: codici meccanografici (es: TAIC824001)
- LOC: località/città/comuni
- DATE: date
- TIME: orari
- PER: persone (nomi dirigenti, docenti)
- ORG: organizzazioni (sindacati, enti)
- EMAIL: indirizzi email
- PHONE: numeri telefono

Rispondi SOLO con il JSON, senza spiegazioni."""

    def _get_generic_prompt(self, testo: str) -> str:
        """Prompt generico per NER."""
        return f"""Analizza questo testo ed estrai tutte le entità nominate (Named Entities).

TESTO:
{testo[:4000]}

Restituisci un JSON con:
{{
    "entities": [
        {{"text": "testo entità", "label": "TIPO", "start": posizione_inizio, "end": posizione_fine}}
    ]
}}

Usa questi label:
- PER: persone
- ORG: organizzazioni
- LOC: luoghi
- DATE: date
- EMAIL: email
- PHONE: telefoni

Rispondi SOLO con il JSON."""

    def _convert_to_spacy_format(self, text: str, extraction: Dict) -> List[Dict]:
        """
        Converte le entità estratte in formato spaCy per training.

        Formato spaCy: [(start, end, label), ...]
        """
        entities = []

        # Estrai da campo 'entities' se presente
        if "entities" in extraction and isinstance(extraction["entities"], list):
            for ent in extraction["entities"]:
                if all(k in ent for k in ["text", "label", "start", "end"]):
                    entities.append({
                        "start": ent["start"],
                        "end": ent["end"],
                        "label": ent["label"]
                    })

        # Cerca anche nei campi specifici
        field_labels = {
            # Interpello
            "classe_concorso": "CLASSE_CONCORSO",
            "meccanografico": "MECCANOGRAFICO",
            "istituto": "ISTITUTO",
            "provincia": "PROVINCIA",
            "citta": "LOC",
            "email_contatto": "EMAIL",
            "telefono_contatto": "PHONE",
            "referente": "PER",
            # Calendario/Convocazione
            "scuola_nome": "ISTITUTO",
            "scuola_codice": "MECCANOGRAFICO",
            "scuola_comune": "LOC",
            "organizzatore_nome": "PER",
            "contatto_email": "EMAIL",
            "contatto_telefono": "PHONE",
            "motivo_convocazione": "MOTIVO",
            "tipo_riunione": "TIPO_RIUNIONE"
        }

        for field, label in field_labels.items():
            value = extraction.get(field)
            if value and isinstance(value, str):
                # Cerca posizione nel testo
                start = text.find(value)
                if start >= 0:
                    entities.append({
                        "start": start,
                        "end": start + len(value),
                        "label": label,
                        "text": value
                    })

        return entities

    def get_training_samples(
        self,
        tipo: Optional[str] = None,
        approved_only: bool = False
    ) -> List[Dict]:
        """
        Recupera training samples.

        Args:
            tipo: Filtra per tipo (interpello, calendario, etc.)
            approved_only: Solo samples approvati

        Returns:
            Lista di training samples
        """
        samples = self.training_samples

        if tipo:
            samples = [s for s in samples if s.get("type") == tipo]

        if approved_only:
            samples = [s for s in samples if s.get("approved", False)]

        return samples

    def approve_sample(self, sample_id: str, corrections: Optional[Dict] = None) -> bool:
        """
        Approva un training sample (opzionalmente con correzioni).

        Args:
            sample_id: ID del sample
            corrections: Correzioni manuali alle entità

        Returns:
            True se approvato con successo
        """
        for sample in self.training_samples:
            if sample["id"] == sample_id:
                sample["approved"] = True
                sample["approved_at"] = datetime.now().isoformat()
                if corrections:
                    sample["corrections"] = corrections
                    # Applica correzioni alle entità
                    if "entities" in corrections:
                        sample["entities"] = corrections["entities"]
                self._save_training_data()
                return True
        return False

    def delete_sample(self, sample_id: str) -> bool:
        """Elimina un training sample."""
        original_count = len(self.training_samples)
        self.training_samples = [s for s in self.training_samples if s["id"] != sample_id]
        if len(self.training_samples) < original_count:
            self._save_training_data()
            return True
        return False

    def export_spacy_format(self, approved_only: bool = True) -> Dict:
        """
        Esporta training data in formato spaCy.

        Formato:
        [
            ("testo", {"entities": [(start, end, "LABEL"), ...]})
        ]
        """
        samples = self.get_training_samples(approved_only=approved_only)

        spacy_data = []
        for sample in samples:
            text = sample.get("text", "")
            entities = sample.get("entities", [])

            # Converti in tuple (start, end, label)
            ent_tuples = []
            for ent in entities:
                if all(k in ent for k in ["start", "end", "label"]):
                    ent_tuples.append((ent["start"], ent["end"], ent["label"]))

            if text and ent_tuples:
                spacy_data.append({
                    "text": text,
                    "entities": ent_tuples
                })

        return {
            "format": "spacy",
            "version": "3.0",
            "total_samples": len(spacy_data),
            "data": spacy_data
        }

    def export_bert_format(self, approved_only: bool = True) -> Dict:
        """
        Esporta training data in formato BERT NER (BIO tagging).

        Formato:
        [
            {"tokens": ["token1", "token2", ...], "tags": ["O", "B-LABEL", "I-LABEL", ...]}
        ]
        """
        samples = self.get_training_samples(approved_only=approved_only)

        bert_data = []
        for sample in samples:
            text = sample.get("text", "")
            entities = sample.get("entities", [])

            # Tokenizza (semplice split per ora)
            tokens = text.split()
            tags = ["O"] * len(tokens)

            # Assegna tag BIO
            char_to_token = {}
            char_pos = 0
            for i, token in enumerate(tokens):
                for j in range(len(token)):
                    char_to_token[char_pos + j] = i
                char_pos += len(token) + 1  # +1 per spazio

            for ent in entities:
                start = ent.get("start", 0)
                end = ent.get("end", 0)
                label = ent.get("label", "")

                # Trova token corrispondenti
                token_start = char_to_token.get(start)
                token_end = char_to_token.get(end - 1) if end > 0 else None

                if token_start is not None:
                    tags[token_start] = f"B-{label}"
                    if token_end is not None and token_end > token_start:
                        for t in range(token_start + 1, token_end + 1):
                            if t < len(tags):
                                tags[t] = f"I-{label}"

            bert_data.append({
                "tokens": tokens,
                "tags": tags
            })

        return {
            "format": "bert_bio",
            "version": "1.0",
            "total_samples": len(bert_data),
            "data": bert_data
        }

    def get_statistics(self) -> Dict:
        """Restituisce statistiche sui training data."""
        samples = self.training_samples
        approved = [s for s in samples if s.get("approved", False)]

        # Conta entità per label
        label_counts = {}
        for sample in samples:
            for ent in sample.get("entities", []):
                label = ent.get("label", "UNKNOWN")
                label_counts[label] = label_counts.get(label, 0) + 1

        return {
            "total_samples": len(samples),
            "approved_samples": len(approved),
            "pending_approval": len(samples) - len(approved),
            "entity_counts": label_counts,
            "by_type": {
                "interpello": len([s for s in samples if s.get("type") == "interpello"]),
                "calendario": len([s for s in samples if s.get("type") == "calendario"]),
                "altro": len([s for s in samples if s.get("type") not in ["interpello", "calendario"]])
            }
        }

    # ==================== BENCHMARK SYSTEM ====================

    def run_benchmark(
        self,
        email_ids: List[int],
        tipo: str = "interpello",
        benchmark_name: str = None,
        db_session = None,
        engine: str = None,  # "unified", "spacy", "regex" o None per default
        use_ollama: bool = True,
        use_chatgpt: bool = None  # None = legge dalle impostazioni sistema (COME IN PRODUZIONE)
    ) -> Dict:
        """
        Esegue benchmark sul SISTEMA DI PRODUZIONE di estrazione.

        USA ESATTAMENTE lo stesso flusso di produzione:
        - UnifiedExtractor con parametri di default
        - use_chatgpt=None legge dalle impostazioni sistema
        - Costruzione testo con allegati_testo dal database

        Args:
            email_ids: Lista ID email da testare
            tipo: Tipo estrazione (interpello, calendario)
            benchmark_name: Nome identificativo del benchmark
            db_session: Sessione database
            engine: "unified" (default), "spacy", "regex"
            use_ollama: Usa LLM locale (default True come produzione)
            use_chatgpt: None=legge da impostazioni sistema (COME PRODUZIONE)

        Returns:
            Dict con risultati benchmark e metriche
        """
        from app.models import Email

        if not benchmark_name:
            benchmark_name = f"benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Usa estrattore unificato di default (sistema di produzione)
        if engine == "spacy":
            from app.services.nlp_service import get_nlp_extractor
            extractor = get_nlp_extractor()
            extraction_method = "spacy"
        elif engine == "regex":
            from app.services.unified_extractor import get_unified_extractor
            extractor = get_unified_extractor()
            extraction_method = "regex_only"
        else:
            # Default: unified (Regex + NLP + LLM) - SISTEMA DI PRODUZIONE
            from app.services.unified_extractor import get_unified_extractor
            extractor = get_unified_extractor()
            extraction_method = "unified"

        results = []
        ground_truth_samples = {s["email_id"]: s for s in self.training_samples if s.get("approved")}

        # Campi da confrontare in base al tipo
        if tipo == "calendario":
            fields = ['data_inizio', 'ora_inizio', 'luogo', 'scuola_nome', 'scuola_codice',
                      'modalita', 'tipo_riunione', 'motivo', 'contatto_email', 'contatto_telefono']
        else:  # interpello
            fields = ['classe_concorso', 'provincia', 'citta', 'istituto', 'meccanografico',
                      'email_contatto', 'telefono_contatto', 'ore_settimanali']

        for email_id in email_ids:
            if not db_session:
                continue

            email = db_session.query(Email).filter(Email.id == email_id).first()
            if not email:
                continue

            # Costruisci testo - IDENTICO A PRODUZIONE (action_executor.py)
            testo = f"Oggetto: {email.oggetto or ''}\n\n{email.corpo_testo or ''}"
            try:
                # Parse allegati come in produzione
                import json as json_lib
                allegati = json_lib.loads(email.allegati_testo) if isinstance(email.allegati_testo, str) else email.allegati_testo
                if allegati:
                    testi_allegati = [f"{nome}: {contenuto}" for nome, contenuto in allegati.items() if contenuto]
                    testo += "\n\n" + "\n\n".join(testi_allegati)
            except:
                pass

            # Estrazione - usa sistema appropriato
            try:
                if extraction_method == "unified":
                    # Sistema unificato (Regex + NLP + LLM) - COME IN PRODUZIONE
                    extraction_result = extractor.extract(
                        testo=testo,
                        tipo=tipo,
                        use_ollama=use_ollama,
                        use_chatgpt=use_chatgpt
                    )
                elif extraction_method == "spacy":
                    if tipo == "calendario":
                        extraction_result = extractor.extract_calendar_event(testo)
                    else:
                        extraction_result = extractor.extract_for_interpello(testo)
                else:  # regex_only
                    extraction_result = extractor._extract_with_regex(testo, tipo)
            except Exception as e:
                logger.error(f"Errore estrazione email {email_id}: {e}")
                extraction_result = {}

            # Ground truth (se disponibile)
            ground_truth = ground_truth_samples.get(email_id, {}).get("openai_extraction", {})

            # Calcola match per ogni campo
            field_results = {}
            for field in fields:
                extracted_val = self._normalize_value(extraction_result.get(field))
                gt_val = self._normalize_value(ground_truth.get(field))

                field_results[field] = {
                    "extracted": extracted_val,
                    "ground_truth": gt_val,
                    "match": extracted_val == gt_val if gt_val else None,
                    "has_ground_truth": gt_val is not None
                }

            # Aggiungi info pipeline se disponibile
            pipeline_info = {}
            if extraction_method == "unified":
                pipeline_info = {
                    "steps": extraction_result.get('_pipeline_steps', []),
                    "completeness": extraction_result.get('_completeness', 0),
                    "confidence": extraction_result.get('_overall_confidence', 0)
                }

            results.append({
                "email_id": email_id,
                "oggetto": email.oggetto,
                "has_ground_truth": email_id in ground_truth_samples,
                "extraction_method": extraction_method,
                "fields": field_results,
                "pipeline_info": pipeline_info
            })

        # Calcola metriche aggregate
        metrics = self._calculate_benchmark_metrics(results)

        # Conta email con/senza ground truth
        emails_with_gt = [r for r in results if r["has_ground_truth"]]
        emails_without_gt = [r for r in results if not r["has_ground_truth"]]

        benchmark_result = {
            "name": benchmark_name,
            "timestamp": datetime.now().isoformat(),
            "tipo": tipo,
            "email_count": len(email_ids),
            "with_ground_truth": len(emails_with_gt),
            "without_ground_truth": len(emails_without_gt),
            "emails_without_gt_list": [{"id": r["email_id"], "oggetto": r["oggetto"]} for r in emails_without_gt],
            "testable_percentage": round(len(emails_with_gt) / len(results) * 100, 1) if results else 0,
            "metrics": metrics,
            "results": results,
            "warning": f"⚠️ {len(emails_without_gt)} email senza ground truth approvato (non incluse nelle metriche)" if emails_without_gt else None
        }

        # Salva benchmark
        self._save_benchmark(benchmark_result)

        return benchmark_result

    def _normalize_value(self, val) -> Optional[str]:
        """Normalizza valore per confronto."""
        if val is None:
            return None
        val = str(val).strip().upper()
        # Rimuovi trattini e spazi per confronto
        val = val.replace("-", "").replace(" ", "")
        return val if val else None

    def _calculate_benchmark_metrics(self, results: List[Dict]) -> Dict:
        """Calcola metriche da risultati benchmark."""
        # Estrai campi dinamicamente dai risultati
        fields = set()
        for result in results:
            fields.update(result.get("fields", {}).keys())
        fields = list(fields)

        metrics = {"by_field": {}, "overall": {}}

        for field in fields:
            true_positives = 0
            false_positives = 0
            false_negatives = 0
            total_with_gt = 0

            for result in results:
                field_data = result.get("fields", {}).get(field, {})
                if not field_data.get("has_ground_truth"):
                    continue

                total_with_gt += 1
                extracted_val = field_data.get("extracted")
                gt_val = field_data.get("ground_truth")

                if extracted_val and gt_val and extracted_val == gt_val:
                    true_positives += 1
                elif extracted_val and not gt_val:
                    # Estratto qualcosa ma ground truth vuoto - potenziale FP
                    false_positives += 1
                elif extracted_val and gt_val and extracted_val != gt_val:
                    false_positives += 1
                    false_negatives += 1
                elif not extracted_val and gt_val:
                    false_negatives += 1

            precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
            recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

            metrics["by_field"][field] = {
                "precision": round(precision, 3),
                "recall": round(recall, 3),
                "f1_score": round(f1, 3),
                "true_positives": true_positives,
                "false_positives": false_positives,
                "false_negatives": false_negatives,
                "total_with_gt": total_with_gt
            }

        # Overall metrics (media)
        all_precisions = [m["precision"] for m in metrics["by_field"].values() if m["total_with_gt"] > 0]
        all_recalls = [m["recall"] for m in metrics["by_field"].values() if m["total_with_gt"] > 0]
        all_f1s = [m["f1_score"] for m in metrics["by_field"].values() if m["total_with_gt"] > 0]

        metrics["overall"] = {
            "avg_precision": round(sum(all_precisions) / len(all_precisions), 3) if all_precisions else 0,
            "avg_recall": round(sum(all_recalls) / len(all_recalls), 3) if all_recalls else 0,
            "avg_f1_score": round(sum(all_f1s) / len(all_f1s), 3) if all_f1s else 0
        }

        return metrics

    def _save_benchmark(self, benchmark: Dict):
        """Salva benchmark su file."""
        benchmarks_file = TRAINING_DATA_DIR / "benchmarks.json"

        benchmarks = []
        if benchmarks_file.exists():
            try:
                with open(benchmarks_file, 'r', encoding='utf-8') as f:
                    benchmarks = json.load(f)
            except:
                pass

        benchmarks.append(benchmark)

        # Mantieni solo ultimi 50 benchmark
        benchmarks = benchmarks[-50:]

        with open(benchmarks_file, 'w', encoding='utf-8') as f:
            json.dump(benchmarks, f, ensure_ascii=False, indent=2)

    def get_benchmarks(self, limit: int = 10) -> List[Dict]:
        """Recupera ultimi benchmark."""
        benchmarks_file = TRAINING_DATA_DIR / "benchmarks.json"

        if not benchmarks_file.exists():
            return []

        try:
            with open(benchmarks_file, 'r', encoding='utf-8') as f:
                benchmarks = json.load(f)
            return benchmarks[-limit:]
        except:
            return []

    def compare_benchmarks(self, benchmark_before: str, benchmark_after: str) -> Dict:
        """
        Confronta due benchmark per vedere miglioramenti.

        Args:
            benchmark_before: Nome benchmark pre-training
            benchmark_after: Nome benchmark post-training

        Returns:
            Dict con confronto metriche e delta
        """
        benchmarks = self.get_benchmarks(50)

        before = next((b for b in benchmarks if b["name"] == benchmark_before), None)
        after = next((b for b in benchmarks if b["name"] == benchmark_after), None)

        if not before or not after:
            return {"error": "Benchmark non trovati"}

        comparison = {
            "before": {
                "name": before["name"],
                "timestamp": before["timestamp"],
                "metrics": before["metrics"]["overall"]
            },
            "after": {
                "name": after["name"],
                "timestamp": after["timestamp"],
                "metrics": after["metrics"]["overall"]
            },
            "delta": {},
            "by_field": {},
            "improved": False
        }

        # Calcola delta overall
        for metric in ["avg_precision", "avg_recall", "avg_f1_score"]:
            before_val = before["metrics"]["overall"].get(metric, 0)
            after_val = after["metrics"]["overall"].get(metric, 0)
            delta = round(after_val - before_val, 3)
            comparison["delta"][metric] = delta

        # Delta per campo
        for field in before["metrics"].get("by_field", {}):
            if field in after["metrics"].get("by_field", {}):
                before_f1 = before["metrics"]["by_field"][field]["f1_score"]
                after_f1 = after["metrics"]["by_field"][field]["f1_score"]
                comparison["by_field"][field] = {
                    "before_f1": before_f1,
                    "after_f1": after_f1,
                    "delta": round(after_f1 - before_f1, 3)
                }

        # Determina se c'è miglioramento (F1 complessivo aumentato)
        comparison["improved"] = comparison["delta"].get("avg_f1_score", 0) > 0

        return comparison

    def apply_training(self) -> Dict:
        """
        Applica training approvato aggiungendo pattern a EntityRuler.

        IMPORTANTE: Solo i sample APPROVATI vengono usati!
        CREA BACKUP automatico e SALVA NELLA HISTORY prima di applicare modifiche.

        Returns:
            Dict con risultato applicazione
        """
        approved_samples = [s for s in self.training_samples if s.get("approved")]

        if not approved_samples:
            return {"success": False, "message": "Nessun sample approvato da applicare"}

        # File patterns, backup e history
        trained_patterns_file = TRAINING_DATA_DIR / "trained_patterns.json"
        backup_file = TRAINING_DATA_DIR / "trained_patterns_backup.json"
        history_file = TRAINING_DATA_DIR / "training_history.json"

        # Carica history esistente
        history = []
        if history_file.exists():
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            except:
                history = []

        # Genera version ID
        version_id = f"v{len(history) + 1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # BACKUP: Salva stato corrente prima di modificare
        existing_patterns = []
        if trained_patterns_file.exists():
            try:
                with open(trained_patterns_file, 'r', encoding='utf-8') as f:
                    existing_patterns = json.load(f)
                # Crea backup (per rollback immediato)
                with open(backup_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        "timestamp": datetime.now().isoformat(),
                        "version_id": history[-1]["version_id"] if history else "v0_initial",
                        "patterns": existing_patterns,
                        "pattern_count": len(existing_patterns)
                    }, f, ensure_ascii=False, indent=2)
                logger.info(f"📦 Backup creato: {len(existing_patterns)} pattern salvati")
            except Exception as e:
                logger.warning(f"⚠️ Errore creazione backup: {e}")

        # Estrai nuovi pattern dai sample approvati
        new_patterns = []

        for sample in approved_samples:
            extraction = sample.get("openai_extraction", {})

            # Classe concorso
            cc = extraction.get("classe_concorso")
            if cc and len(cc) >= 2:
                new_patterns.append({
                    "label": "CLASSE_CONCORSO",
                    "pattern": cc.upper(),
                    "id": f"trained_cc_{cc}"
                })

            # Meccanografico
            mec = extraction.get("meccanografico") or extraction.get("scuola_codice")
            if mec and len(mec) >= 8:
                new_patterns.append({
                    "label": "MECCANOGRAFICO",
                    "pattern": mec.upper(),
                    "id": f"trained_mec_{mec}"
                })

            # Istituto (da interpello o calendario)
            ist = extraction.get("istituto") or extraction.get("scuola_nome")
            if ist and len(ist) >= 5:
                new_patterns.append({
                    "label": "ISTITUTO",
                    "pattern": ist,
                    "id": f"trained_ist_{sample['id']}"
                })

            # Motivo convocazione (per calendario)
            motivo = extraction.get("motivo_convocazione")
            if motivo and len(motivo) >= 5:
                new_patterns.append({
                    "label": "MOTIVO",
                    "pattern": motivo,
                    "id": f"trained_motivo_{sample['id']}"
                })

        # Merge evitando duplicati
        existing_ids = {p.get("id") for p in existing_patterns}
        for p in new_patterns:
            if p.get("id") not in existing_ids:
                existing_patterns.append(p)

        with open(trained_patterns_file, 'w', encoding='utf-8') as f:
            json.dump(existing_patterns, f, ensure_ascii=False, indent=2)

        logger.info(f"✅ Applicati {len(new_patterns)} nuovi pattern da training")

        # Salva nella history
        history_entry = {
            "version_id": version_id,
            "timestamp": datetime.now().isoformat(),
            "patterns_added": len(new_patterns),
            "total_patterns": len(existing_patterns),
            "samples_used": len(approved_samples),
            "pattern_types": {
                "CLASSE_CONCORSO": len([p for p in new_patterns if p.get("label") == "CLASSE_CONCORSO"]),
                "MECCANOGRAFICO": len([p for p in new_patterns if p.get("label") == "MECCANOGRAFICO"]),
                "ISTITUTO": len([p for p in new_patterns if p.get("label") == "ISTITUTO"]),
                "MOTIVO": len([p for p in new_patterns if p.get("label") == "MOTIVO"])
            },
            "status": "applied"
        }
        history.append(history_entry)

        # Salva history (mantieni ultimi 50)
        history = history[-50:]
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

        logger.info(f"📜 Salvato nella history: {version_id}")

        return {
            "success": True,
            "message": f"Applicati {len(new_patterns)} nuovi pattern",
            "version_id": version_id,
            "patterns_added": len(new_patterns),
            "total_patterns": len(existing_patterns),
            "patterns_file": str(trained_patterns_file),
            "backup_available": backup_file.exists()
        }

    def rollback_training(self) -> Dict:
        """
        Ripristina i pattern dal backup precedente.

        Returns:
            Dict con risultato rollback
        """
        trained_patterns_file = TRAINING_DATA_DIR / "trained_patterns.json"
        backup_file = TRAINING_DATA_DIR / "trained_patterns_backup.json"
        history_file = TRAINING_DATA_DIR / "training_history.json"

        if not backup_file.exists():
            return {
                "success": False,
                "message": "Nessun backup disponibile per il rollback"
            }

        try:
            # Leggi backup
            with open(backup_file, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)

            backup_patterns = backup_data.get("patterns", [])
            backup_timestamp = backup_data.get("timestamp", "unknown")
            backup_version = backup_data.get("version_id", "unknown")

            # Conta pattern attuali prima del rollback
            current_patterns = []
            if trained_patterns_file.exists():
                with open(trained_patterns_file, 'r', encoding='utf-8') as f:
                    current_patterns = json.load(f)

            # Ripristina patterns
            with open(trained_patterns_file, 'w', encoding='utf-8') as f:
                json.dump(backup_patterns, f, ensure_ascii=False, indent=2)

            # Salva nella history
            history = []
            if history_file.exists():
                try:
                    with open(history_file, 'r', encoding='utf-8') as f:
                        history = json.load(f)
                except:
                    history = []

            rollback_entry = {
                "version_id": f"rollback_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "timestamp": datetime.now().isoformat(),
                "patterns_before": len(current_patterns),
                "patterns_after": len(backup_patterns),
                "restored_to": backup_version,
                "status": "rollback"
            }
            history.append(rollback_entry)

            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(history[-50:], f, ensure_ascii=False, indent=2)

            logger.info(f"🔄 Rollback completato: ripristinati {len(backup_patterns)} pattern dal backup {backup_timestamp}")

            return {
                "success": True,
                "message": f"Rollback completato! Ripristinata versione {backup_version}",
                "restored_patterns": len(backup_patterns),
                "removed_patterns": len(current_patterns) - len(backup_patterns),
                "restored_to_version": backup_version,
                "backup_timestamp": backup_timestamp
            }

        except Exception as e:
            logger.error(f"❌ Errore rollback: {e}")
            return {
                "success": False,
                "message": f"Errore durante il rollback: {str(e)}"
            }

    def get_backup_info(self) -> Dict:
        """
        Restituisce informazioni sul backup disponibile.
        """
        backup_file = TRAINING_DATA_DIR / "trained_patterns_backup.json"

        if not backup_file.exists():
            return {"backup_available": False}

        try:
            with open(backup_file, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)

            return {
                "backup_available": True,
                "timestamp": backup_data.get("timestamp"),
                "version_id": backup_data.get("version_id", "unknown"),
                "pattern_count": backup_data.get("pattern_count", len(backup_data.get("patterns", [])))
            }
        except:
            return {"backup_available": False}

    def get_training_history(self, limit: int = 20) -> List[Dict]:
        """
        Restituisce lo storico delle versioni di training.
        """
        history_file = TRAINING_DATA_DIR / "training_history.json"

        if not history_file.exists():
            return []

        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
            # Ritorna dal più recente al più vecchio
            return list(reversed(history[-limit:]))
        except:
            return []

    def get_current_version(self) -> Dict:
        """
        Restituisce informazioni sulla versione corrente del modello.
        """
        history = self.get_training_history(1)
        trained_patterns_file = TRAINING_DATA_DIR / "trained_patterns.json"

        current_patterns = 0
        if trained_patterns_file.exists():
            try:
                with open(trained_patterns_file, 'r', encoding='utf-8') as f:
                    current_patterns = len(json.load(f))
            except:
                pass

        if history:
            latest = history[0]
            return {
                "version_id": latest.get("version_id", "unknown"),
                "timestamp": latest.get("timestamp"),
                "total_patterns": current_patterns,
                "status": latest.get("status", "unknown")
            }
        else:
            return {
                "version_id": "v0_initial",
                "timestamp": None,
                "total_patterns": current_patterns,
                "status": "initial"
            }

    # ==================== ASYNC JOB METHODS ====================

    def analyze_batch_async(
        self,
        email_ids: List[int],
        tipo: str = "interpello",
        db_session_factory=None
    ) -> str:
        """
        Avvia analisi batch in background.

        Returns:
            job_id: ID del job per verificare lo stato
        """
        job_id = str(uuid.uuid4())

        _async_jobs[job_id] = {
            "type": "analyze_batch",
            "status": "running",
            "started_at": datetime.now().isoformat(),
            "progress": 0,
            "total": len(email_ids),
            "completed": 0,
            "errors": [],
            "results": [],
            "message": f"Analisi 0/{len(email_ids)} email..."
        }

        def run_analysis():
            try:
                from app.database import SessionLocal
                from app.models import Email

                db = SessionLocal()
                results = []
                errors = []

                for i, email_id in enumerate(email_ids):
                    try:
                        email = db.query(Email).filter(Email.id == email_id).first()
                        if not email:
                            errors.append({"email_id": email_id, "error": "Email non trovata"})
                            continue

                        result = self.analyze_email_with_chatgpt(
                            email_id=email.id,
                            oggetto=email.oggetto or "",
                            corpo=email.corpo_testo or "",
                            allegati_testo=email.allegati_testo,
                            tipo=tipo
                        )
                        results.append({
                            "email_id": email_id,
                            "sample_id": result.get("id"),
                            "entities_count": len(result.get("entities", []))
                        })
                    except Exception as e:
                        logger.error(f"Errore analisi email {email_id}: {e}")
                        errors.append({"email_id": email_id, "error": str(e)})

                    # Aggiorna progresso
                    _async_jobs[job_id]["completed"] = i + 1
                    _async_jobs[job_id]["progress"] = int((i + 1) / len(email_ids) * 100)
                    _async_jobs[job_id]["message"] = f"Analisi {i + 1}/{len(email_ids)} email..."

                db.close()

                _async_jobs[job_id]["status"] = "completed"
                _async_jobs[job_id]["results"] = results
                _async_jobs[job_id]["errors"] = errors
                _async_jobs[job_id]["completed_at"] = datetime.now().isoformat()
                _async_jobs[job_id]["message"] = f"Completato: {len(results)} analizzate, {len(errors)} errori"

            except Exception as e:
                logger.error(f"Errore job {job_id}: {e}")
                _async_jobs[job_id]["status"] = "failed"
                _async_jobs[job_id]["error"] = str(e)
                _async_jobs[job_id]["message"] = f"Errore: {str(e)}"

        thread = threading.Thread(target=run_analysis, daemon=True)
        thread.start()

        return job_id

    def run_benchmark_async(
        self,
        email_ids: List[int],
        tipo: str = "interpello",
        benchmark_name: str = None
    ) -> str:
        """
        Avvia benchmark in background.

        Returns:
            job_id: ID del job per verificare lo stato
        """
        job_id = str(uuid.uuid4())

        if not benchmark_name:
            benchmark_name = f"benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        _async_jobs[job_id] = {
            "type": "benchmark",
            "status": "running",
            "started_at": datetime.now().isoformat(),
            "progress": 0,
            "total": len(email_ids),
            "completed": 0,
            "benchmark_name": benchmark_name,
            "message": f"Benchmark 0/{len(email_ids)} email..."
        }

        def run_benchmark_task():
            try:
                from app.database import SessionLocal
                from app.models import Email
                from app.services.nlp_service import get_nlp_extractor

                db = SessionLocal()
                nlp_extractor = get_nlp_extractor()
                results = []
                ground_truth_samples = {s["email_id"]: s for s in self.training_samples if s.get("approved")}

                for i, email_id in enumerate(email_ids):
                    try:
                        email = db.query(Email).filter(Email.id == email_id).first()
                        if not email:
                            continue

                        # Costruisci testo
                        testo = f"Oggetto: {email.oggetto or ''}\n\n{email.corpo_testo or ''}"
                        if email.allegati_testo:
                            for _, t in (email.allegati_testo or {}).items():
                                if t:
                                    testo += f"\n{t[:2000]}"

                        # Estrazione NLP locale
                        try:
                            nlp_result = nlp_extractor.extract_for_interpello(testo)
                        except Exception as e:
                            logger.error(f"Errore NLP email {email_id}: {e}")
                            nlp_result = {}

                        # Ground truth (se disponibile)
                        ground_truth = ground_truth_samples.get(email_id, {}).get("openai_extraction", {})

                        # Calcola match per ogni campo
                        fields = ['classe_concorso', 'provincia', 'citta', 'istituto', 'meccanografico',
                                  'email_contatto', 'telefono_contatto', 'ore_settimanali']

                        field_results = {}
                        for field in fields:
                            nlp_val = self._normalize_value(nlp_result.get(field))
                            gt_val = self._normalize_value(ground_truth.get(field))

                            field_results[field] = {
                                "nlp": nlp_val,
                                "ground_truth": gt_val,
                                "match": nlp_val == gt_val if gt_val else None,
                                "has_ground_truth": gt_val is not None
                            }

                        results.append({
                            "email_id": email_id,
                            "oggetto": email.oggetto,
                            "has_ground_truth": email_id in ground_truth_samples,
                            "fields": field_results
                        })

                    except Exception as e:
                        logger.error(f"Errore benchmark email {email_id}: {e}")

                    # Aggiorna progresso
                    _async_jobs[job_id]["completed"] = i + 1
                    _async_jobs[job_id]["progress"] = int((i + 1) / len(email_ids) * 100)
                    _async_jobs[job_id]["message"] = f"Benchmark {i + 1}/{len(email_ids)} email..."

                db.close()

                # Calcola metriche aggregate
                metrics = self._calculate_benchmark_metrics(results)

                # Conta email con/senza ground truth
                emails_with_gt = [r for r in results if r["has_ground_truth"]]
                emails_without_gt = [r for r in results if not r["has_ground_truth"]]

                benchmark_result = {
                    "name": benchmark_name,
                    "timestamp": datetime.now().isoformat(),
                    "tipo": tipo,
                    "email_count": len(email_ids),
                    "with_ground_truth": len(emails_with_gt),
                    "without_ground_truth": len(emails_without_gt),
                    "emails_without_gt_list": [{"id": r["email_id"], "oggetto": r["oggetto"]} for r in emails_without_gt],
                    "testable_percentage": round(len(emails_with_gt) / len(results) * 100, 1) if results else 0,
                    "metrics": metrics,
                    "results": results,
                    "warning": f"⚠️ {len(emails_without_gt)} email senza ground truth approvato" if emails_without_gt else None
                }

                # Salva benchmark
                self._save_benchmark(benchmark_result)

                _async_jobs[job_id]["status"] = "completed"
                _async_jobs[job_id]["result"] = benchmark_result
                _async_jobs[job_id]["completed_at"] = datetime.now().isoformat()
                f1 = metrics.get("overall", {}).get("avg_f1_score", 0)
                testable_msg = f" ({len(emails_with_gt)}/{len(results)} email testabili)" if emails_without_gt else ""
                _async_jobs[job_id]["message"] = f"Completato: F1 Score {f1*100:.1f}%{testable_msg}"

            except Exception as e:
                logger.error(f"Errore job benchmark {job_id}: {e}")
                _async_jobs[job_id]["status"] = "failed"
                _async_jobs[job_id]["error"] = str(e)
                _async_jobs[job_id]["message"] = f"Errore: {str(e)}"

        thread = threading.Thread(target=run_benchmark_task, daemon=True)
        thread.start()

        return job_id

    @staticmethod
    def get_job_status(job_id: str) -> Optional[Dict]:
        """
        Recupera stato di un job asincrono.

        Returns:
            Dict con stato job o None se non trovato
        """
        return _async_jobs.get(job_id)

    @staticmethod
    def get_all_jobs() -> Dict[str, Dict]:
        """Recupera tutti i job (per debug)."""
        return _async_jobs

    @staticmethod
    def cleanup_old_jobs(max_age_hours: int = 24):
        """Rimuove job vecchi."""
        now = datetime.now()
        to_remove = []
        for job_id, job in _async_jobs.items():
            started = datetime.fromisoformat(job.get("started_at", now.isoformat()))
            if (now - started).total_seconds() > max_age_hours * 3600:
                to_remove.append(job_id)
        for job_id in to_remove:
            del _async_jobs[job_id]

    # ==================== CATEGORIZATION BENCHMARK ====================

    def run_categorization_benchmark(
        self,
        email_ids: List[int] = None,
        limit: int = 50,
        db_session = None,
        use_nlp: bool = True
    ) -> Dict:
        """
        Esegue benchmark sul sistema di categorizzazione.
        Confronta categorizzazione NLP con ground truth nel database.

        Args:
            email_ids: Lista ID email da testare (se None, prende ultime N)
            limit: Numero max email se email_ids è None
            db_session: Sessione database
            use_nlp: Se True usa NLP enhancement (default)

        Returns:
            Dict con risultati benchmark e metriche per categoria
        """
        from app.models import Email
        from app.services.categorizer import EmailCategorizer

        if not db_session:
            from app.database import SessionLocal
            db_session = SessionLocal()
            should_close = True
        else:
            should_close = False

        try:
            # Recupera email
            if email_ids:
                emails = db_session.query(Email).filter(Email.id.in_(email_ids)).all()
            else:
                emails = db_session.query(Email).filter(
                    Email.categoria.isnot(None),
                    Email.categoria != 'da_categorizzare'
                ).order_by(Email.id.desc()).limit(limit).all()

            categorizer = EmailCategorizer(use_rules=True, use_nlp=use_nlp)

            results = {
                'total': len(emails),
                'correct': 0,
                'incorrect': 0,
                'by_category': {},
                'confusion_matrix': {},
                'details': []
            }

            for email in emails:
                try:
                    # Categorizza - USA ESATTAMENTE LO STESSO FLUSSO DI PRODUZIONE
                    # Come in email_polling.py, passa allegati_testo dal database
                    new_cat, conf, subcat, _ = categorizer.categorize(
                        mittente=email.mittente or '',
                        oggetto=email.oggetto or '',
                        corpo=email.corpo_testo or '',
                        allegati_testo=email.allegati_testo  # Da DB, come in produzione
                    )

                    actual = email.categoria
                    predicted = new_cat.value

                    # Aggiorna metriche
                    if actual not in results['by_category']:
                        results['by_category'][actual] = {'total': 0, 'correct': 0, 'incorrect': 0}

                    results['by_category'][actual]['total'] += 1

                    if actual == predicted:
                        results['correct'] += 1
                        results['by_category'][actual]['correct'] += 1
                    else:
                        results['incorrect'] += 1
                        results['by_category'][actual]['incorrect'] += 1

                    # Confusion matrix
                    if actual not in results['confusion_matrix']:
                        results['confusion_matrix'][actual] = {}
                    if predicted not in results['confusion_matrix'][actual]:
                        results['confusion_matrix'][actual][predicted] = 0
                    results['confusion_matrix'][actual][predicted] += 1

                    # Dettaglio
                    results['details'].append({
                        'email_id': email.id,
                        'oggetto': (email.oggetto or '')[:50],
                        'actual': actual,
                        'predicted': predicted,
                        'confidence': conf,
                        'correct': actual == predicted
                    })

                except Exception as e:
                    logger.warning(f"Errore categorizzazione email {email.id}: {e}")

            # Calcola accuracy per categoria
            for cat, data in results['by_category'].items():
                if data['total'] > 0:
                    data['accuracy'] = data['correct'] / data['total']
                else:
                    data['accuracy'] = 0

            # Accuracy globale
            if results['total'] > 0:
                results['accuracy'] = results['correct'] / results['total']
            else:
                results['accuracy'] = 0

            logger.info(f"📊 Categorization benchmark: {results['correct']}/{results['total']} correct ({results['accuracy']:.1%})")

            return results

        finally:
            if should_close:
                db_session.close()

    def get_categorization_stats(self, db_session = None) -> Dict:
        """
        Recupera statistiche sulle categorie nel database.

        Returns:
            Dict con conteggi per categoria e confidence medio
        """
        from app.models import Email
        from sqlalchemy import func

        if not db_session:
            from app.database import SessionLocal
            db_session = SessionLocal()
            should_close = True
        else:
            should_close = False

        try:
            # Conteggio per categoria
            category_counts = db_session.query(
                Email.categoria,
                func.count(Email.id).label('count'),
                func.avg(Email.categoria_confidence).label('avg_confidence')
            ).group_by(Email.categoria).all()

            stats = {
                'total': 0,
                'by_category': {},
                'avg_confidence': 0
            }

            total_conf = 0
            for cat, count, avg_conf in category_counts:
                stats['by_category'][cat or 'None'] = {
                    'count': count,
                    'avg_confidence': float(avg_conf) if avg_conf else 0
                }
                stats['total'] += count
                if avg_conf:
                    total_conf += avg_conf * count

            if stats['total'] > 0:
                stats['avg_confidence'] = total_conf / stats['total']

            return stats

        finally:
            if should_close:
                db_session.close()


# Singleton
_training_service: Optional[TrainingService] = None


def get_training_service() -> TrainingService:
    """Ottiene istanza singleton del training service."""
    global _training_service
    if _training_service is None:
        _training_service = TrainingService()
    return _training_service
