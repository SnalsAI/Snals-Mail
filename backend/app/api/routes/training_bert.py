"""
API Routes per Training BERT - Fine-tuning modelli NER.

Endpoint per:
- Status modello BERT
- Fine-tuning su sample approvati
- Benchmark BERT-only
- Rollback versione modello
- Predizione test
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import Email
from app.services.training_service import get_training_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/training/bert", tags=["BERT Training"])


# ============================================
# REQUEST/RESPONSE MODELS
# ============================================

class BertTrainRequest(BaseModel):
    """Request per training BERT."""
    epochs: int = 3
    batch_size: int = 8
    learning_rate: float = 2e-5
    version_name: Optional[str] = None


class BertBenchmarkRequest(BaseModel):
    """Request per benchmark BERT."""
    email_ids: List[int]
    tipo: str = "interpello"
    name: Optional[str] = None


class BertRollbackRequest(BaseModel):
    """Request per rollback BERT."""
    version_id: str


class BertPredictRequest(BaseModel):
    """Request per predizione BERT."""
    text: str


# ============================================
# HELPER FUNCTIONS
# ============================================

def _calculate_bert_metrics(results: List[Dict]) -> Dict:
    """Calcola metriche per benchmark BERT."""
    total_correct = 0
    total_predicted = 0
    total_actual = 0

    field_metrics = {}

    for r in results:
        if not r.get("has_ground_truth"):
            continue

        pred_entities = r.get("bert_entities", [])
        gt_entities = r.get("ground_truth", [])

        # Normalizza per confronto
        pred_set = set()
        for e in pred_entities:
            label = e.get("label", "").upper()
            text = e.get("text", "").lower().strip()
            if label and text:
                pred_set.add((label, text))

        gt_set = set()
        for e in gt_entities:
            label = e.get("label", "").upper()
            text = e.get("text", e.get("value", ""))
            if isinstance(text, str):
                text = text.lower().strip()
            if label and text:
                gt_set.add((label, text))

        # Conta match
        correct = len(pred_set & gt_set)
        total_correct += correct
        total_predicted += len(pred_set)
        total_actual += len(gt_set)

        # Per campo
        for label, text in gt_set:
            if label not in field_metrics:
                field_metrics[label] = {"tp": 0, "fp": 0, "fn": 0}
            if (label, text) in pred_set:
                field_metrics[label]["tp"] += 1
            else:
                field_metrics[label]["fn"] += 1

        for label, text in pred_set:
            if label not in field_metrics:
                field_metrics[label] = {"tp": 0, "fp": 0, "fn": 0}
            if (label, text) not in gt_set:
                field_metrics[label]["fp"] += 1

    # Calcola metriche globali
    precision = total_correct / total_predicted if total_predicted > 0 else 0
    recall = total_correct / total_actual if total_actual > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    # Metriche per campo
    by_field = {}
    for label, counts in field_metrics.items():
        tp = counts["tp"]
        fp = counts["fp"]
        fn = counts["fn"]
        p = tp / (tp + fp) if (tp + fp) > 0 else 0
        r = tp / (tp + fn) if (tp + fn) > 0 else 0
        f = 2 * p * r / (p + r) if (p + r) > 0 else 0
        by_field[label] = {
            "precision": round(p, 4),
            "recall": round(r, 4),
            "f1_score": round(f, 4),
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn
        }

    return {
        "overall": {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "correct": total_correct,
            "predicted": total_predicted,
            "actual": total_actual
        },
        "by_field": by_field
    }


# ============================================
# ENDPOINTS
# ============================================

@router.get("/status")
async def get_bert_status():
    """
    Restituisce stato del modello BERT.

    Returns:
        - is_available: True se BERT caricato
        - is_trained: True se esiste modello fine-tuned
        - current_model: Info sul modello corrente
        - available_models: Lista modelli disponibili
        - models_count: Numero modelli
    """
    from app.services.bert_training_service import get_bert_training_service

    try:
        service = get_bert_training_service()
        current = service.get_current_model_info()
        models = service.list_available_models()

        return {
            "is_available": True,
            "is_trained": not current.get("is_base", True),
            "current_model": current,
            "available_models": models,
            "models_count": len(models)
        }
    except Exception as e:
        logger.warning(f"⚠️ BERT non disponibile: {e}")
        return {
            "is_available": False,
            "is_trained": False,
            "current_model": None,
            "available_models": [],
            "models_count": 0,
            "error": str(e)
        }


@router.post("/train")
async def train_bert_model(request: BertTrainRequest):
    """
    Avvia fine-tuning BERT sui sample approvati.

    IMPORTANTE:
    - Richiede almeno 5 sample approvati
    - Il training è asincrono
    - Usa GET /training/bert/job/{job_id} per monitorare

    Body:
        - epochs: Numero epoche (default 3)
        - batch_size: Batch size (default 8)
        - learning_rate: Learning rate (default 2e-5)
        - version_name: Nome versione (opzionale)

    Returns:
        - success: True se avviato
        - job_id: ID per monitorare progresso
        - samples_count: Numero sample usati
    """
    from app.services.bert_training_service import get_bert_training_service

    # Recupera samples approvati
    training_service = get_training_service()
    samples = training_service.get_training_samples(approved_only=True)

    if len(samples) < 5:
        raise HTTPException(
            status_code=400,
            detail=f"Servono almeno 5 sample approvati per il training BERT. Attualmente: {len(samples)}"
        )

    bert_service = get_bert_training_service()

    job_id = bert_service.train_async(
        samples=samples,
        epochs=request.epochs,
        batch_size=request.batch_size,
        learning_rate=request.learning_rate
    )

    return {
        "success": True,
        "job_id": job_id,
        "message": f"Training BERT avviato con {len(samples)} sample",
        "samples_count": len(samples),
        "config": {
            "epochs": request.epochs,
            "batch_size": request.batch_size,
            "learning_rate": request.learning_rate
        }
    }


@router.get("/job/{job_id}")
async def get_bert_job_status(job_id: str):
    """
    Verifica stato di un job di training BERT.

    Path params:
        - job_id: ID del job

    Returns:
        - status: "running" | "completed" | "failed"
        - progress: Percentuale (0-100)
        - message: Messaggio stato
        - result: Risultato training (se completato)
        - error: Messaggio errore (se fallito)
    """
    from app.services.bert_training_service import BERTTrainingService

    job = BERTTrainingService.get_job_status(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job non trovato")

    return job


@router.post("/rollback")
async def rollback_bert_model(request: BertRollbackRequest):
    """
    Ripristina una versione precedente del modello BERT.

    Body:
        - version_id: ID versione da ripristinare

    Returns:
        - success: True se ripristinato
        - version_id: Versione ripristinata
        - metrics: Metriche della versione
    """
    from app.services.bert_training_service import get_bert_training_service

    service = get_bert_training_service()
    result = service.rollback_to_version(request.version_id)

    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "Errore rollback BERT")
        )

    return result


@router.post("/benchmark")
async def run_bert_benchmark(
    request: BertBenchmarkRequest,
    db: Session = Depends(get_db)
):
    """
    Esegue benchmark SOLO su BERT (modello fine-tuned o base).

    Confronta estrazione BERT vs ground truth (ChatGPT approvati).

    Body:
        - email_ids: Lista ID email da testare
        - tipo: Tipo estrazione (interpello, calendario)
        - name: Nome opzionale per il benchmark

    Returns:
        - success: True se completato
        - engine: "bert"
        - benchmark: Risultati con metriche
    """
    from app.services.bert_training_service import get_bert_training_service

    if not request.email_ids:
        raise HTTPException(status_code=400, detail="Nessuna email selezionata")

    bert_service = get_bert_training_service()
    training_service = get_training_service()

    # Info modello corrente
    current = bert_service.get_current_model_info()
    if current.get("is_base", True):
        logger.warning("⚠️ Nessun modello BERT fine-tuned. Uso modello base.")

    try:
        # Carica ground truth
        approved_samples = training_service.get_training_samples(
            tipo=request.tipo,
            approved_only=True
        )

        # Mappa email_id -> sample
        ground_truth_map = {s.get("email_id"): s for s in approved_samples if s.get("email_id")}

        results = []
        emails_with_gt = 0

        for email_id in request.email_ids:
            email = db.query(Email).filter(Email.id == email_id).first()
            if not email:
                continue

            # Estrazione BERT
            text = f"{email.oggetto or ''}\n{email.corpo_testo or ''}"
            bert_entities = bert_service.predict(text)

            # Ground truth
            gt = ground_truth_map.get(email_id)
            gt_entities = []
            if gt:
                emails_with_gt += 1
                gt_entities = gt.get("entities", [])
                # Anche da openai_extraction
                extraction = gt.get("openai_extraction", {})
                for key, value in extraction.items():
                    if value and isinstance(value, str):
                        gt_entities.append({"label": key.upper(), "text": value})

            results.append({
                "email_id": email_id,
                "bert_entities": bert_entities,
                "ground_truth": gt_entities,
                "has_ground_truth": gt is not None
            })

        # Calcola metriche
        metrics = _calculate_bert_metrics(results)

        # Crea dati benchmark
        benchmark_data = {
            "name": f"bert_{request.name}" if request.name else f"bert_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "timestamp": datetime.now().isoformat(),
            "engine": "bert",
            "tipo": request.tipo,
            "email_count": len(request.email_ids),
            "with_ground_truth": emails_with_gt,
            "metrics": metrics,
            "model_info": current,
            "results": results[:10]  # Solo primi 10
        }

        return {
            "success": True,
            "engine": "bert",
            "message": f"Benchmark BERT completato su {len(request.email_ids)} email ({emails_with_gt} con ground truth)",
            "benchmark": benchmark_data
        }

    except Exception as e:
        logger.error(f"❌ Errore benchmark BERT: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models")
async def list_bert_models():
    """
    Lista tutti i modelli BERT disponibili (fine-tuned).

    Returns:
        - count: Numero modelli
        - models: Lista modelli con version_id, metrics, is_current
    """
    from app.services.bert_training_service import get_bert_training_service

    service = get_bert_training_service()
    models = service.list_available_models()

    return {
        "count": len(models),
        "models": models
    }


@router.get("/history")
async def get_bert_history(
    limit: int = Query(20, description="Numero massimo versioni")
):
    """
    Storico training BERT.

    Returns:
        - count: Numero entry
        - history: Lista versioni con timestamp, metrics, type
    """
    from app.services.bert_training_service import get_bert_training_service

    service = get_bert_training_service()
    history = service.get_training_history(limit)

    return {
        "count": len(history),
        "history": history
    }


@router.post("/predict")
async def bert_predict(request: BertPredictRequest):
    """
    Esegue predizione NER con il modello BERT corrente.

    Utile per testare il modello fine-tuned.

    Body:
        - text: Testo da analizzare

    Returns:
        - entities: Entità trovate con label, text, score
        - count: Numero entità
        - model_info: Info sul modello usato
    """
    from app.services.bert_training_service import get_bert_training_service

    if not request.text or len(request.text) < 10:
        raise HTTPException(status_code=400, detail="Testo troppo corto (minimo 10 caratteri)")

    service = get_bert_training_service()
    entities = service.predict(request.text)
    model_info = service.get_current_model_info()

    return {
        "text": request.text[:500] + "..." if len(request.text) > 500 else request.text,
        "entities": entities,
        "count": len(entities),
        "model_info": {
            "is_base": model_info.get("is_base", True),
            "version": model_info.get("version_id")
        }
    }


@router.get("/export")
async def export_bert_format(
    approved_only: bool = Query(True, description="Solo sample approvati")
):
    """
    Esporta training data in formato BERT (BIO tagged).

    Query params:
        - approved_only: Se True, esporta solo sample approvati

    Returns:
        JSON con training data in formato BERT NER
    """
    from fastapi.responses import JSONResponse

    training_service = get_training_service()
    data = training_service.export_bert_format(approved_only=approved_only)

    return JSONResponse(
        content=data,
        headers={
            "Content-Disposition": f"attachment; filename=training_bert_{data['total_samples']}.json"
        }
    )
