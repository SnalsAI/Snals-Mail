"""
BERT Training Service - Fine-tuning BERT per NER su dati scolastici italiani.

Questo servizio permette di:
1. Convertire samples approvati in formato NER (BIO tagging)
2. Fine-tune BERT italiano sui dati
3. Salvare/caricare modelli addestrati con versioning
4. Valutare performance separatamente da spaCy
"""

import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import threading

logger = logging.getLogger(__name__)

# Directory per modelli e dati
MODELS_DIR = Path(__file__).parent.parent / "data" / "bert_models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Label map per NER scolastico
LABEL_LIST = [
    "O",           # Outside
    "B-CLASSE",    # Begin Classe Concorso
    "I-CLASSE",    # Inside Classe Concorso
    "B-MECCA",     # Begin Meccanografico
    "I-MECCA",     # Inside Meccanografico
    "B-ISTITUTO",  # Begin Istituto
    "I-ISTITUTO",  # Inside Istituto
    "B-PROV",      # Begin Provincia
    "I-PROV",      # Inside Provincia
    "B-LOC",       # Begin Località
    "I-LOC",       # Inside Località
    "B-EMAIL",     # Begin Email
    "I-EMAIL",     # Inside Email
    "B-PHONE",     # Begin Telefono
    "I-PHONE",     # Inside Telefono
    "B-DATE",      # Begin Data
    "I-DATE",      # Inside Data
    "B-PER",       # Begin Persona
    "I-PER",       # Inside Persona
    "B-ORG",       # Begin Organizzazione
    "I-ORG",       # Inside Organizzazione
    "B-ORE",       # Begin Ore settimanali
    "I-ORE",       # Inside Ore settimanali
]

LABEL2ID = {label: i for i, label in enumerate(LABEL_LIST)}
ID2LABEL = {i: label for i, label in enumerate(LABEL_LIST)}

# Mapping da etichette ChatGPT a BIO
CHATGPT_TO_BIO = {
    "CLASSE_CONCORSO": "CLASSE",
    "MECCANOGRAFICO": "MECCA",
    "ISTITUTO": "ISTITUTO",
    "PROVINCIA": "PROV",
    "LOC": "LOC",
    "EMAIL": "EMAIL",
    "PHONE": "PHONE",
    "DATE": "DATE",
    "PER": "PER",
    "ORG": "ORG",
    "ORE": "ORE",
}

# Job storage per training asincrono
_training_jobs: Dict[str, Dict[str, Any]] = {}


class BERTTrainingService:
    """Servizio per fine-tuning BERT su NER scolastico."""

    def __init__(self):
        self.base_model = "dbmdz/bert-base-italian-xxl-cased"
        self.current_model_path: Optional[Path] = None
        self.model = None
        self.tokenizer = None
        self._load_current_model_info()

    def _load_current_model_info(self):
        """Carica info sul modello corrente."""
        info_file = MODELS_DIR / "current_model.json"
        if info_file.exists():
            try:
                with open(info_file, 'r') as f:
                    info = json.load(f)
                self.current_model_path = Path(info.get("path", ""))
                logger.info(f"📦 Modello BERT corrente: {info.get('version_id', 'N/A')}")
            except:
                pass

    def _save_current_model_info(self, version_id: str, path: Path, metrics: Dict):
        """Salva info sul modello corrente."""
        info_file = MODELS_DIR / "current_model.json"
        info = {
            "version_id": version_id,
            "path": str(path),
            "timestamp": datetime.now().isoformat(),
            "metrics": metrics
        }
        with open(info_file, 'w') as f:
            json.dump(info, f, indent=2)

    def get_current_model_info(self) -> Dict:
        """Restituisce info sul modello BERT corrente."""
        info_file = MODELS_DIR / "current_model.json"
        if info_file.exists():
            try:
                with open(info_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {
            "version_id": "base_pretrained",
            "path": None,
            "timestamp": None,
            "metrics": None,
            "is_base": True
        }

    def convert_samples_to_ner_format(self, samples: List[Dict]) -> List[Dict]:
        """
        Converte samples ChatGPT approvati in formato NER per training BERT.

        Input: Lista di samples con 'text' e 'entities' (span-based)
        Output: Lista di {'tokens': [...], 'ner_tags': [...]} (BIO format)
        """
        ner_data = []

        for sample in samples:
            if not sample.get("approved"):
                continue

            text = sample.get("text", "")
            entities = sample.get("entities", [])

            # Anche da openai_extraction
            extraction = sample.get("openai_extraction", {})

            # Tokenizza il testo (semplice split per ora)
            tokens = text.split()
            ner_tags = ["O"] * len(tokens)

            # Mappa caratteri a token
            char_to_token = {}
            char_pos = 0
            for i, token in enumerate(tokens):
                for j in range(len(token)):
                    char_to_token[char_pos + j] = i
                char_pos += len(token) + 1  # +1 per spazio

            # Applica etichette dalle entities
            for ent in entities:
                start = ent.get("start", 0)
                end = ent.get("end", 0)
                label = ent.get("label", "")

                # Mappa label ChatGPT a BIO
                bio_label = CHATGPT_TO_BIO.get(label, label)
                if bio_label not in [l.split("-")[1] if "-" in l else l for l in LABEL_LIST]:
                    continue

                # Trova token corrispondenti
                token_start = char_to_token.get(start)
                token_end = char_to_token.get(end - 1) if end > 0 else None

                if token_start is not None:
                    ner_tags[token_start] = f"B-{bio_label}"
                    if token_end is not None and token_end > token_start:
                        for t in range(token_start + 1, min(token_end + 1, len(tokens))):
                            ner_tags[t] = f"I-{bio_label}"

            # Aggiungi anche entità da campi specifici di extraction
            field_to_label = {
                "classe_concorso": "CLASSE",
                "meccanografico": "MECCA",
                "scuola_codice": "MECCA",
                "istituto": "ISTITUTO",
                "scuola_nome": "ISTITUTO",
                "provincia": "PROV",
                "citta": "LOC",
                "scuola_comune": "LOC",
                "email_contatto": "EMAIL",
                "contatto_email": "EMAIL",
                "telefono_contatto": "PHONE",
                "contatto_telefono": "PHONE",
                "ore_settimanali": "ORE",
            }

            for field, bio_label in field_to_label.items():
                value = extraction.get(field)
                if value and isinstance(value, str):
                    # Cerca nel testo
                    value_lower = value.lower()
                    text_lower = text.lower()
                    pos = text_lower.find(value_lower)
                    if pos >= 0:
                        token_idx = char_to_token.get(pos)
                        if token_idx is not None and ner_tags[token_idx] == "O":
                            ner_tags[token_idx] = f"B-{bio_label}"
                            # Tag token successivi
                            value_tokens = value.split()
                            for vt in range(1, len(value_tokens)):
                                if token_idx + vt < len(ner_tags):
                                    ner_tags[token_idx + vt] = f"I-{bio_label}"

            # Valida tags
            valid_tags = []
            for tag in ner_tags:
                if tag in LABEL_LIST:
                    valid_tags.append(tag)
                else:
                    valid_tags.append("O")

            if tokens:
                ner_data.append({
                    "tokens": tokens,
                    "ner_tags": valid_tags,
                    "sample_id": sample.get("id", ""),
                    "type": sample.get("type", "")
                })

        logger.info(f"📊 Convertiti {len(ner_data)} samples in formato NER")
        return ner_data

    def train_model(
        self,
        ner_data: List[Dict],
        epochs: int = 3,
        batch_size: int = 8,
        learning_rate: float = 2e-5,
        version_name: Optional[str] = None
    ) -> Dict:
        """
        Fine-tune BERT sui dati NER.

        Args:
            ner_data: Lista di {'tokens': [...], 'ner_tags': [...]}
            epochs: Numero di epoche
            batch_size: Batch size
            learning_rate: Learning rate
            version_name: Nome versione (opzionale)

        Returns:
            Dict con risultati training
        """
        try:
            import torch
            from transformers import (
                AutoTokenizer,
                AutoModelForTokenClassification,
                TrainingArguments,
                Trainer,
                DataCollatorForTokenClassification
            )
            from datasets import Dataset
            import numpy as np
        except ImportError as e:
            logger.error(f"❌ Dipendenze ML non installate: {e}")
            return {"success": False, "error": f"Dipendenze mancanti: {e}"}

        if len(ner_data) < 5:
            return {"success": False, "error": "Servono almeno 5 samples per il training"}

        # Genera version ID
        if not version_name:
            version_name = f"bert_v{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        output_dir = MODELS_DIR / version_name
        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"🚀 Inizio training BERT: {version_name}")
        logger.info(f"   Samples: {len(ner_data)}, Epochs: {epochs}, Batch: {batch_size}")

        try:
            # Carica tokenizer e modello base
            tokenizer = AutoTokenizer.from_pretrained(self.base_model)
            model = AutoModelForTokenClassification.from_pretrained(
                self.base_model,
                num_labels=len(LABEL_LIST),
                id2label=ID2LABEL,
                label2id=LABEL2ID,
                ignore_mismatched_sizes=True
            )

            # Prepara dataset
            def tokenize_and_align_labels(examples):
                tokenized_inputs = tokenizer(
                    examples["tokens"],
                    truncation=True,
                    is_split_into_words=True,
                    max_length=512,
                    padding="max_length"
                )

                labels = []
                for i, label in enumerate(examples["ner_tags"]):
                    word_ids = tokenized_inputs.word_ids(batch_index=i)
                    previous_word_idx = None
                    label_ids = []
                    for word_idx in word_ids:
                        if word_idx is None:
                            label_ids.append(-100)
                        elif word_idx != previous_word_idx:
                            label_ids.append(LABEL2ID.get(label[word_idx], 0))
                        else:
                            # Per subword, usa I- se il token originale è B-
                            orig_label = label[word_idx]
                            if orig_label.startswith("B-"):
                                label_ids.append(LABEL2ID.get("I-" + orig_label[2:], 0))
                            else:
                                label_ids.append(LABEL2ID.get(orig_label, 0))
                        previous_word_idx = word_idx
                    labels.append(label_ids)

                tokenized_inputs["labels"] = labels
                return tokenized_inputs

            # Crea dataset
            dataset = Dataset.from_dict({
                "tokens": [d["tokens"] for d in ner_data],
                "ner_tags": [d["ner_tags"] for d in ner_data]
            })

            # Split train/eval (80/20)
            split = dataset.train_test_split(test_size=0.2, seed=42)
            train_dataset = split["train"].map(
                tokenize_and_align_labels,
                batched=True,
                remove_columns=["tokens", "ner_tags"]
            )
            eval_dataset = split["test"].map(
                tokenize_and_align_labels,
                batched=True,
                remove_columns=["tokens", "ner_tags"]
            )

            # Data collator
            data_collator = DataCollatorForTokenClassification(tokenizer=tokenizer)

            # Metriche
            def compute_metrics(p):
                predictions, labels = p
                predictions = np.argmax(predictions, axis=2)

                true_predictions = []
                true_labels = []

                for prediction, label in zip(predictions, labels):
                    for pred, lab in zip(prediction, label):
                        if lab != -100:
                            true_predictions.append(ID2LABEL[pred])
                            true_labels.append(ID2LABEL[lab])

                # Calcola precision, recall, f1
                from collections import Counter
                correct = sum(1 for p, l in zip(true_predictions, true_labels) if p == l and l != "O")
                predicted = sum(1 for p in true_predictions if p != "O")
                actual = sum(1 for l in true_labels if l != "O")

                precision = correct / predicted if predicted > 0 else 0
                recall = correct / actual if actual > 0 else 0
                f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

                return {
                    "precision": precision,
                    "recall": recall,
                    "f1": f1
                }

            # Training arguments
            training_args = TrainingArguments(
                output_dir=str(output_dir),
                evaluation_strategy="epoch",
                save_strategy="epoch",
                learning_rate=learning_rate,
                per_device_train_batch_size=batch_size,
                per_device_eval_batch_size=batch_size,
                num_train_epochs=epochs,
                weight_decay=0.01,
                logging_dir=str(output_dir / "logs"),
                logging_steps=10,
                load_best_model_at_end=True,
                metric_for_best_model="f1",
                greater_is_better=True,
                save_total_limit=2,
                report_to="none"
            )

            # Trainer
            trainer = Trainer(
                model=model,
                args=training_args,
                train_dataset=train_dataset,
                eval_dataset=eval_dataset,
                tokenizer=tokenizer,
                data_collator=data_collator,
                compute_metrics=compute_metrics
            )

            # Training
            logger.info("🏋️ Training in corso...")
            train_result = trainer.train()

            # Salva modello finale
            trainer.save_model(str(output_dir / "final"))
            tokenizer.save_pretrained(str(output_dir / "final"))

            # Valutazione finale
            eval_results = trainer.evaluate()

            # Salva metriche
            metrics = {
                "train_loss": train_result.training_loss,
                "eval_loss": eval_results.get("eval_loss", 0),
                "precision": eval_results.get("eval_precision", 0),
                "recall": eval_results.get("eval_recall", 0),
                "f1": eval_results.get("eval_f1", 0),
                "epochs": epochs,
                "samples": len(ner_data),
                "train_samples": len(train_dataset),
                "eval_samples": len(eval_dataset)
            }

            with open(output_dir / "metrics.json", 'w') as f:
                json.dump(metrics, f, indent=2)

            # Aggiorna modello corrente
            self._save_current_model_info(version_name, output_dir / "final", metrics)
            self.current_model_path = output_dir / "final"

            # Salva nella history
            self._save_to_history(version_name, metrics)

            logger.info(f"✅ Training completato: F1={metrics['f1']:.3f}")

            return {
                "success": True,
                "version_id": version_name,
                "metrics": metrics,
                "model_path": str(output_dir / "final")
            }

        except Exception as e:
            logger.error(f"❌ Errore training BERT: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def _save_to_history(self, version_id: str, metrics: Dict):
        """Salva entry nella history."""
        history_file = MODELS_DIR / "training_history.json"

        history = []
        if history_file.exists():
            try:
                with open(history_file, 'r') as f:
                    history = json.load(f)
            except:
                pass

        history.append({
            "version_id": version_id,
            "timestamp": datetime.now().isoformat(),
            "metrics": metrics,
            "type": "bert_training"
        })

        # Mantieni ultimi 50
        history = history[-50:]

        with open(history_file, 'w') as f:
            json.dump(history, f, indent=2)

    def get_training_history(self, limit: int = 20) -> List[Dict]:
        """Restituisce storico training BERT."""
        history_file = MODELS_DIR / "training_history.json"

        if not history_file.exists():
            return []

        try:
            with open(history_file, 'r') as f:
                history = json.load(f)
            return list(reversed(history[-limit:]))
        except:
            return []

    def load_trained_model(self, version_id: Optional[str] = None):
        """
        Carica un modello BERT addestrato.

        Args:
            version_id: ID versione da caricare (None = corrente)
        """
        try:
            from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline

            if version_id:
                model_path = MODELS_DIR / version_id / "final"
            elif self.current_model_path:
                model_path = self.current_model_path
            else:
                # Usa modello base
                logger.info("🔄 Caricamento modello BERT base (pre-trained)...")
                self.tokenizer = AutoTokenizer.from_pretrained(self.base_model)
                self.model = pipeline(
                    "ner",
                    model=self.base_model,
                    aggregation_strategy="simple"
                )
                return True

            if not model_path.exists():
                logger.warning(f"⚠️ Modello non trovato: {model_path}")
                return False

            logger.info(f"🔄 Caricamento modello BERT: {model_path}")

            self.tokenizer = AutoTokenizer.from_pretrained(str(model_path))
            model = AutoModelForTokenClassification.from_pretrained(str(model_path))
            self.model = pipeline(
                "ner",
                model=model,
                tokenizer=self.tokenizer,
                aggregation_strategy="simple"
            )

            logger.info(f"✅ Modello BERT caricato: {version_id or 'current'}")
            return True

        except Exception as e:
            logger.error(f"❌ Errore caricamento modello: {e}")
            return False

    def predict(self, text: str) -> List[Dict]:
        """
        Esegue predizione NER con il modello caricato.

        Args:
            text: Testo da analizzare

        Returns:
            Lista di entità trovate
        """
        if self.model is None:
            self.load_trained_model()

        if self.model is None:
            return []

        try:
            # Limita lunghezza
            text = text[:4096]

            results = self.model(text)

            # Mappa etichette a formato standard
            entities = []
            for ent in results:
                label = ent.get("entity_group", ent.get("entity", ""))
                # Rimuovi prefisso B-/I-
                if label.startswith("B-") or label.startswith("I-"):
                    label = label[2:]

                entities.append({
                    "text": ent.get("word", ""),
                    "label": label,
                    "start": ent.get("start", 0),
                    "end": ent.get("end", 0),
                    "score": ent.get("score", 0),
                    "source": "bert_trained"
                })

            return entities

        except Exception as e:
            logger.error(f"Errore predizione BERT: {e}")
            return []

    def rollback_to_version(self, version_id: str) -> Dict:
        """Ripristina una versione precedente del modello."""
        model_path = MODELS_DIR / version_id / "final"

        if not model_path.exists():
            return {"success": False, "error": f"Versione {version_id} non trovata"}

        # Carica metriche
        metrics_file = MODELS_DIR / version_id / "metrics.json"
        metrics = {}
        if metrics_file.exists():
            with open(metrics_file, 'r') as f:
                metrics = json.load(f)

        # Aggiorna modello corrente
        self._save_current_model_info(version_id, model_path, metrics)
        self.current_model_path = model_path

        # Ricarica modello
        self.load_trained_model(version_id)

        # Salva nella history
        self._save_to_history(f"rollback_to_{version_id}", {"restored_from": version_id})

        return {
            "success": True,
            "message": f"Ripristinato modello {version_id}",
            "version_id": version_id,
            "metrics": metrics
        }

    def list_available_models(self) -> List[Dict]:
        """Lista tutti i modelli disponibili."""
        models = []

        for model_dir in MODELS_DIR.iterdir():
            if model_dir.is_dir() and (model_dir / "final").exists():
                metrics_file = model_dir / "metrics.json"
                metrics = {}
                if metrics_file.exists():
                    try:
                        with open(metrics_file, 'r') as f:
                            metrics = json.load(f)
                    except:
                        pass

                models.append({
                    "version_id": model_dir.name,
                    "path": str(model_dir / "final"),
                    "metrics": metrics,
                    "is_current": self.current_model_path == model_dir / "final"
                })

        # Ordina per data (più recente prima)
        models.sort(key=lambda x: x["version_id"], reverse=True)
        return models

    # ==================== ASYNC TRAINING ====================

    def train_async(
        self,
        samples: List[Dict],
        epochs: int = 3,
        batch_size: int = 8,
        learning_rate: float = 2e-5
    ) -> str:
        """
        Avvia training BERT in background.

        Returns:
            job_id per monitorare lo stato
        """
        import uuid
        job_id = str(uuid.uuid4())

        _training_jobs[job_id] = {
            "type": "bert_training",
            "status": "running",
            "started_at": datetime.now().isoformat(),
            "progress": 0,
            "message": "Preparazione dati...",
            "samples_count": len(samples)
        }

        def run_training():
            try:
                # Converti samples
                _training_jobs[job_id]["message"] = "Conversione samples in formato NER..."
                _training_jobs[job_id]["progress"] = 10

                ner_data = self.convert_samples_to_ner_format(samples)

                if len(ner_data) < 5:
                    _training_jobs[job_id]["status"] = "failed"
                    _training_jobs[job_id]["error"] = f"Servono almeno 5 samples approvati. Trovati: {len(ner_data)}"
                    return

                # Analizza entità nel training set
                entity_counts = {}
                for item in ner_data:
                    for tag in item["ner_tags"]:
                        if tag != "O":
                            label = tag.split("-")[1] if "-" in tag else tag
                            entity_counts[label] = entity_counts.get(label, 0) + 1

                _training_jobs[job_id]["ner_data_info"] = {
                    "samples": len(ner_data),
                    "entity_counts": entity_counts,
                    "total_tokens": sum(len(d["tokens"]) for d in ner_data)
                }

                _training_jobs[job_id]["message"] = f"Training BERT: {len(ner_data)} samples, {sum(entity_counts.values())} entità..."
                _training_jobs[job_id]["progress"] = 20

                # Training
                result = self.train_model(
                    ner_data,
                    epochs=epochs,
                    batch_size=batch_size,
                    learning_rate=learning_rate
                )

                if result.get("success"):
                    _training_jobs[job_id]["status"] = "completed"
                    _training_jobs[job_id]["progress"] = 100
                    _training_jobs[job_id]["result"] = result

                    # Messaggio dettagliato
                    metrics = result.get("metrics", {})
                    details = [
                        f"F1: {metrics.get('f1', 0)*100:.1f}%",
                        f"Precision: {metrics.get('precision', 0)*100:.1f}%",
                        f"Recall: {metrics.get('recall', 0)*100:.1f}%",
                        f"Samples: {metrics.get('samples', 0)}",
                        f"Epochs: {metrics.get('epochs', 0)}"
                    ]
                    _training_jobs[job_id]["message"] = f"✅ Training completato! {' | '.join(details)}"
                    _training_jobs[job_id]["entity_summary"] = entity_counts
                else:
                    _training_jobs[job_id]["status"] = "failed"
                    _training_jobs[job_id]["error"] = result.get("error", "Errore sconosciuto")
                    _training_jobs[job_id]["message"] = f"❌ Errore: {result.get('error', 'sconosciuto')}"

            except Exception as e:
                logger.error(f"Errore training async: {e}", exc_info=True)
                _training_jobs[job_id]["status"] = "failed"
                _training_jobs[job_id]["error"] = str(e)
                _training_jobs[job_id]["message"] = f"❌ Errore: {str(e)}"

        thread = threading.Thread(target=run_training, daemon=True)
        thread.start()

        return job_id

    @staticmethod
    def get_job_status(job_id: str) -> Optional[Dict]:
        """Recupera stato job training."""
        return _training_jobs.get(job_id)


# Singleton
_bert_service: Optional[BERTTrainingService] = None


def get_bert_training_service() -> BERTTrainingService:
    """Ottiene istanza singleton del BERT training service."""
    global _bert_service
    if _bert_service is None:
        _bert_service = BERTTrainingService()
    return _bert_service
