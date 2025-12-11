"""
API Routes per Training NLP - Generazione training data con ChatGPT.

Questi endpoint permettono di:
1. Analizzare email con ChatGPT per estrarre entità
2. Salvare e approvare training samples
3. Esportare dati in formato spaCy/BERT
"""

import logging
from typing import Optional, List, Dict
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import Email
from app.services.training_service import get_training_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/training", tags=["NLP Training"])


class AnalyzeEmailRequest(BaseModel):
    """Request per analisi email."""
    email_id: int
    tipo: str = "interpello"  # interpello, calendario, generico


class AnalyzeTextRequest(BaseModel):
    """Request per analisi testo diretto."""
    testo: str
    tipo: str = "interpello"


class ApproveRequest(BaseModel):
    """Request per approvazione sample."""
    sample_id: str
    corrections: Optional[dict] = None


class BatchAnalyzeRequest(BaseModel):
    """Request per analisi batch."""
    email_ids: List[int]
    tipo: str = "interpello"


@router.get("/status")
async def get_training_status():
    """
    Verifica stato del servizio training.

    Returns:
        - openai_available: True se ChatGPT disponibile
        - statistics: Statistiche sui training data
    """
    service = get_training_service()

    return {
        "openai_available": service.is_openai_available(),
        "statistics": service.get_statistics()
    }


@router.post("/analyze/email")
async def analyze_email(
    request: AnalyzeEmailRequest,
    db: Session = Depends(get_db)
):
    """
    Analizza una email con ChatGPT per generare training data.

    Body:
        - email_id: ID dell'email da analizzare
        - tipo: Tipo di estrazione (interpello, calendario, generico)
    """
    service = get_training_service()

    if not service.is_openai_available():
        raise HTTPException(
            status_code=400,
            detail="OpenAI API key non configurata. Aggiungi OPENAI_API_KEY nel .env"
        )

    # Carica email
    email = db.query(Email).filter(Email.id == request.email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email non trovata")

    try:
        result = service.analyze_email_with_chatgpt(
            email_id=email.id,
            oggetto=email.oggetto or "",
            corpo=email.corpo_testo or "",
            allegati_testo=email.allegati_testo,
            tipo=request.tipo
        )

        return {
            "success": True,
            "message": f"Analisi completata. {len(result.get('entities', []))} entità estratte.",
            "sample": result
        }

    except Exception as e:
        logger.error(f"Errore analisi email {request.email_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/text")
async def analyze_text(request: AnalyzeTextRequest):
    """
    Analizza testo diretto con ChatGPT.

    Body:
        - testo: Testo da analizzare
        - tipo: Tipo di estrazione
    """
    service = get_training_service()

    if not service.is_openai_available():
        raise HTTPException(
            status_code=400,
            detail="OpenAI API key non configurata"
        )

    try:
        result = service.analyze_email_with_chatgpt(
            email_id=0,  # No email ID for direct text
            oggetto="",
            corpo=request.testo,
            allegati_testo=None,
            tipo=request.tipo
        )

        return {
            "success": True,
            "message": f"Analisi completata. {len(result.get('entities', []))} entità estratte.",
            "sample": result
        }

    except Exception as e:
        logger.error(f"Errore analisi testo: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/batch")
async def analyze_batch(
    request: BatchAnalyzeRequest,
    db: Session = Depends(get_db)
):
    """
    Analizza multiple email con ChatGPT (batch).

    Body:
        - email_ids: Lista ID email da analizzare
        - tipo: Tipo di estrazione
    """
    service = get_training_service()

    if not service.is_openai_available():
        raise HTTPException(
            status_code=400,
            detail="OpenAI API key non configurata"
        )

    results = []
    errors = []

    for email_id in request.email_ids:
        email = db.query(Email).filter(Email.id == email_id).first()
        if not email:
            errors.append({"email_id": email_id, "error": "Email non trovata"})
            continue

        try:
            result = service.analyze_email_with_chatgpt(
                email_id=email.id,
                oggetto=email.oggetto or "",
                corpo=email.corpo_testo or "",
                allegati_testo=email.allegati_testo,
                tipo=request.tipo
            )
            results.append({
                "email_id": email_id,
                "sample_id": result.get("id"),
                "entities_count": len(result.get("entities", []))
            })
        except Exception as e:
            errors.append({"email_id": email_id, "error": str(e)})

    return {
        "success": True,
        "message": f"Analizzate {len(results)} email, {len(errors)} errori.",
        "results": results,
        "errors": errors
    }


@router.get("/samples")
async def get_samples(
    tipo: Optional[str] = Query(None, description="Filtra per tipo"),
    approved_only: bool = Query(False, description="Solo approvati")
):
    """
    Recupera training samples.

    Query:
        - tipo: Filtra per tipo (interpello, calendario)
        - approved_only: Solo samples approvati
    """
    service = get_training_service()
    samples = service.get_training_samples(tipo=tipo, approved_only=approved_only)

    return {
        "count": len(samples),
        "samples": samples
    }


@router.get("/samples/{sample_id}")
async def get_sample(sample_id: str):
    """Recupera un singolo training sample."""
    service = get_training_service()
    samples = service.get_training_samples()

    for sample in samples:
        if sample.get("id") == sample_id:
            return {"sample": sample}

    raise HTTPException(status_code=404, detail="Sample non trovato")


@router.post("/samples/{sample_id}/approve")
async def approve_sample(sample_id: str, request: Optional[ApproveRequest] = None):
    """
    Approva un training sample (con correzioni opzionali).

    Path:
        - sample_id: ID del sample da approvare

    Body (opzionale):
        - corrections: Dict con correzioni alle entità
    """
    service = get_training_service()

    corrections = request.corrections if request else None
    success = service.approve_sample(sample_id, corrections)

    if success:
        return {"success": True, "message": "Sample approvato"}
    else:
        raise HTTPException(status_code=404, detail="Sample non trovato")


@router.delete("/samples/{sample_id}")
async def delete_sample(sample_id: str):
    """Elimina un training sample."""
    service = get_training_service()

    success = service.delete_sample(sample_id)
    if success:
        return {"success": True, "message": "Sample eliminato"}
    else:
        raise HTTPException(status_code=404, detail="Sample non trovato")


@router.get("/export/spacy")
async def export_spacy(approved_only: bool = Query(True)):
    """
    Esporta training data in formato spaCy.

    Query:
        - approved_only: Se esportare solo samples approvati

    Returns:
        JSON con training data in formato spaCy
    """
    service = get_training_service()
    data = service.export_spacy_format(approved_only=approved_only)

    return JSONResponse(
        content=data,
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=training_spacy_{data['total_samples']}.json"
        }
    )


@router.get("/export/bert")
async def export_bert(approved_only: bool = Query(True)):
    """
    Esporta training data in formato BERT (BIO tagging).

    Query:
        - approved_only: Se esportare solo samples approvati

    Returns:
        JSON con training data in formato BERT
    """
    service = get_training_service()
    data = service.export_bert_format(approved_only=approved_only)

    return JSONResponse(
        content=data,
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=training_bert_{data['total_samples']}.json"
        }
    )


@router.get("/statistics")
async def get_statistics():
    """Restituisce statistiche dettagliate sui training data."""
    service = get_training_service()
    return service.get_statistics()


# ==================== BENCHMARK ENDPOINTS ====================


class BenchmarkRequest(BaseModel):
    """Request per esecuzione benchmark."""
    email_ids: List[int]
    tipo: str = "interpello"
    name: Optional[str] = None


class CompareBenchmarkRequest(BaseModel):
    """Request per confronto benchmark."""
    before_name: str
    after_name: str


@router.post("/benchmark/run")
async def run_benchmark(
    request: BenchmarkRequest,
    db: Session = Depends(get_db)
):
    """
    Esegue benchmark sul SISTEMA DI PRODUZIONE di estrazione.

    USA ESATTAMENTE lo stesso flusso di produzione:
    - UnifiedExtractor (Regex + NLP + LLM)
    - Costruzione testo con allegati identica a action_executor.py
    - use_chatgpt legge dalle impostazioni sistema

    Confronta l'estrazione con il ground truth (ChatGPT approvato).
    Usare PRIMA del training per baseline, DOPO per misurare miglioramenti.

    Body:
        - email_ids: Lista ID email da testare
        - tipo: Tipo estrazione (interpello, calendario)
        - name: Nome identificativo del benchmark (opzionale)
    """
    service = get_training_service()

    try:
        result = service.run_benchmark(
            email_ids=request.email_ids,
            tipo=request.tipo,
            benchmark_name=request.name,
            db_session=db
        )

        return {
            "success": True,
            "message": f"Benchmark completato su {len(request.email_ids)} email",
            "benchmark": result
        }
    except Exception as e:
        logger.error(f"Errore benchmark: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/benchmark/list")
async def list_benchmarks(limit: int = Query(10, description="Numero massimo benchmark")):
    """
    Recupera la lista dei benchmark salvati.

    Query:
        - limit: Numero massimo di benchmark da restituire (default 10)
    """
    service = get_training_service()
    benchmarks = service.get_benchmarks(limit=limit)

    # Restituisci solo summary senza i risultati dettagliati
    summaries = []
    for b in benchmarks:
        summaries.append({
            "name": b.get("name"),
            "timestamp": b.get("timestamp"),
            "tipo": b.get("tipo"),
            "email_count": b.get("email_count"),
            "with_ground_truth": b.get("with_ground_truth"),
            "metrics": b.get("metrics", {}).get("overall", {})
        })

    return {
        "count": len(summaries),
        "benchmarks": summaries
    }


@router.get("/benchmark/{benchmark_name}")
async def get_benchmark(benchmark_name: str):
    """
    Recupera un benchmark specifico con tutti i dettagli.

    Path:
        - benchmark_name: Nome del benchmark
    """
    service = get_training_service()
    benchmarks = service.get_benchmarks(50)

    benchmark = next((b for b in benchmarks if b["name"] == benchmark_name), None)
    if not benchmark:
        raise HTTPException(status_code=404, detail="Benchmark non trovato")

    return {"benchmark": benchmark}


@router.post("/benchmark/compare")
async def compare_benchmarks(request: CompareBenchmarkRequest):
    """
    Confronta due benchmark per vedere miglioramenti pre/post training.

    Body:
        - before_name: Nome benchmark pre-training
        - after_name: Nome benchmark post-training

    Returns:
        - Delta metriche per campo e overall
        - Flag "improved" se F1 score è migliorato
    """
    service = get_training_service()

    comparison = service.compare_benchmarks(
        benchmark_before=request.before_name,
        benchmark_after=request.after_name
    )

    if "error" in comparison:
        raise HTTPException(status_code=404, detail=comparison["error"])

    return {
        "success": True,
        "comparison": comparison
    }


@router.post("/apply")
async def apply_training():
    """
    Applica il training approvato all'EntityRuler.

    IMPORTANTE: Solo i sample APPROVATI vengono usati per creare nuovi pattern.
    Crea automaticamente un BACKUP prima di applicare modifiche.
    Dopo l'applicazione, eseguire un nuovo benchmark per verificare i miglioramenti.

    Returns:
        - patterns_added: Numero pattern aggiunti
        - total_patterns: Totale pattern nel file
        - backup_available: True se il rollback è possibile
    """
    service = get_training_service()

    result = service.apply_training()

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "Errore applicazione training"))

    return result


@router.post("/rollback")
async def rollback_training():
    """
    Ripristina il modello NLP allo stato precedente.

    Utile se il benchmark DOPO mostra performance peggiori rispetto al benchmark PRIMA.
    Ripristina i pattern dal backup creato automaticamente durante l'ultimo apply.

    Returns:
        - restored_patterns: Numero pattern ripristinati
        - backup_timestamp: Data/ora del backup ripristinato
    """
    service = get_training_service()

    result = service.rollback_training()

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "Errore rollback"))

    # Ricarica pattern dopo rollback
    try:
        from app.services.nlp_service import reload_nlp_model
        reload_nlp_model()
    except Exception as e:
        logger.warning(f"⚠️ Pattern ripristinati ma non ricaricati: {e}")

    return result


@router.get("/backup-info")
async def get_backup_info():
    """
    Restituisce informazioni sul backup disponibile per eventuale rollback.
    """
    service = get_training_service()
    return service.get_backup_info()


@router.get("/history")
async def get_training_history(limit: int = Query(20, description="Numero massimo versioni")):
    """
    Restituisce lo storico delle versioni di training.

    Mostra tutte le applicazioni di training e i rollback effettuati.
    """
    service = get_training_service()
    history = service.get_training_history(limit)
    return {
        "count": len(history),
        "history": history
    }


@router.get("/current-version")
async def get_current_version():
    """
    Restituisce informazioni sulla versione corrente del modello NLP.
    """
    service = get_training_service()
    return service.get_current_version()


@router.post("/reload-patterns")
async def reload_patterns():
    """
    Ricarica i pattern NLP dal file dopo l'applicazione del training.

    Necessario per rendere effettivi i nuovi pattern senza riavviare il container.
    """
    try:
        from app.services.nlp_service import reload_nlp_model
        reload_nlp_model()
        return {"success": True, "message": "Pattern NLP ricaricati"}
    except Exception as e:
        logger.error(f"Errore reload pattern: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ASYNC JOB ENDPOINTS ====================


class AsyncAnalyzeRequest(BaseModel):
    """Request per analisi batch asincrona."""
    email_ids: List[int]
    tipo: str = "interpello"


class AsyncBenchmarkRequest(BaseModel):
    """Request per benchmark asincrono."""
    email_ids: List[int]
    tipo: str = "interpello"
    name: Optional[str] = None


@router.post("/analyze/async")
async def analyze_batch_async(request: AsyncAnalyzeRequest):
    """
    Avvia analisi batch ChatGPT in background.

    Non blocca - restituisce immediatamente un job_id per verificare lo stato.

    Body:
        - email_ids: Lista ID email da analizzare
        - tipo: Tipo estrazione (interpello, calendario)

    Returns:
        - job_id: ID per verificare stato con GET /training/job/{job_id}
    """
    service = get_training_service()

    if not request.email_ids:
        raise HTTPException(status_code=400, detail="Nessuna email selezionata")

    job_id = service.analyze_batch_async(
        email_ids=request.email_ids,
        tipo=request.tipo
    )

    return {
        "success": True,
        "job_id": job_id,
        "message": f"Analisi avviata per {len(request.email_ids)} email. Usa GET /training/job/{job_id} per verificare lo stato."
    }


@router.post("/benchmark/async")
async def run_benchmark_async(request: AsyncBenchmarkRequest):
    """
    Avvia benchmark NLP in background.

    Non blocca - restituisce immediatamente un job_id per verificare lo stato.

    Body:
        - email_ids: Lista ID email da testare
        - tipo: Tipo estrazione (interpello, calendario)
        - name: Nome identificativo benchmark (opzionale)

    Returns:
        - job_id: ID per verificare stato con GET /training/job/{job_id}
    """
    service = get_training_service()

    if not request.email_ids:
        raise HTTPException(status_code=400, detail="Nessuna email selezionata")

    job_id = service.run_benchmark_async(
        email_ids=request.email_ids,
        tipo=request.tipo,
        benchmark_name=request.name
    )

    return {
        "success": True,
        "job_id": job_id,
        "message": f"Benchmark avviato per {len(request.email_ids)} email. Usa GET /training/job/{job_id} per verificare lo stato."
    }


@router.get("/job/{job_id}")
async def get_job_status(job_id: str):
    """
    Verifica stato di un job asincrono.

    Usare per polling periodico dopo aver avviato un job con /analyze/async o /benchmark/async.

    Returns:
        - status: "running" | "completed" | "failed"
        - progress: Percentuale completamento (0-100)
        - message: Messaggio stato corrente
        - result: Risultato (solo se completed)
        - error: Messaggio errore (solo se failed)
    """
    from app.services.training_service import TrainingService

    job = TrainingService.get_job_status(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job non trovato")

    return job


@router.get("/jobs")
async def list_jobs(limit: int = Query(10, description="Numero massimo job")):
    """
    Lista tutti i job attivi/recenti.

    Utile per debug e monitoraggio.
    """
    from app.services.training_service import TrainingService

    all_jobs = TrainingService.get_all_jobs()

    # Ordina per timestamp decrescente
    sorted_jobs = sorted(
        all_jobs.items(),
        key=lambda x: x[1].get("started_at", ""),
        reverse=True
    )[:limit]

    return {
        "count": len(sorted_jobs),
        "jobs": [{"job_id": jid, **jdata} for jid, jdata in sorted_jobs]
    }


@router.delete("/jobs/cleanup")
async def cleanup_old_jobs(max_age_hours: int = Query(24, description="Età massima job in ore")):
    """
    Rimuove job vecchi dalla memoria.
    """
    from app.services.training_service import TrainingService

    TrainingService.cleanup_old_jobs(max_age_hours)

    return {"success": True, "message": f"Rimossi job più vecchi di {max_age_hours} ore"}


# ==================== BERT ML TRAINING ENDPOINTS ====================


class BERTTrainRequest(BaseModel):
    """Request per training BERT."""
    epochs: int = 3
    batch_size: int = 8
    learning_rate: float = 2e-5
    version_name: Optional[str] = None


class BERTRollbackRequest(BaseModel):
    """Request per rollback BERT."""
    version_id: str


@router.get("/bert/status")
async def get_bert_status():
    """
    Verifica stato del modello BERT (base vs fine-tuned).

    Returns:
        - current_model: Info sul modello corrente
        - available_models: Lista modelli disponibili
        - is_trained: True se esiste un modello fine-tuned
    """
    from app.services.bert_training_service import get_bert_training_service

    service = get_bert_training_service()
    current = service.get_current_model_info()
    models = service.list_available_models()

    return {
        "current_model": current,
        "available_models": models,
        "is_trained": not current.get("is_base", True),
        "models_count": len(models)
    }


@router.post("/bert/train")
async def train_bert_model(request: BERTTrainRequest):
    """
    Avvia fine-tuning BERT sui samples approvati.

    IMPORTANTE: Richiede samples approvati da ChatGPT come ground truth.
    Il training è asincrono - usa GET /training/bert/job/{job_id} per lo stato.

    Body:
        - epochs: Numero epoche (default 3)
        - batch_size: Batch size (default 8)
        - learning_rate: Learning rate (default 2e-5)
        - version_name: Nome versione (opzionale)

    Returns:
        - job_id: ID per monitorare progresso
    """
    from app.services.bert_training_service import get_bert_training_service

    # Recupera samples approvati
    training_service = get_training_service()
    samples = training_service.get_training_samples(approved_only=True)

    if len(samples) < 5:
        raise HTTPException(
            status_code=400,
            detail=f"Servono almeno 5 samples approvati per il training BERT. Attualmente: {len(samples)}"
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
        "message": f"Training BERT avviato con {len(samples)} samples. Usa GET /training/bert/job/{job_id} per lo stato.",
        "samples_count": len(samples),
        "config": {
            "epochs": request.epochs,
            "batch_size": request.batch_size,
            "learning_rate": request.learning_rate
        }
    }


@router.get("/bert/job/{job_id}")
async def get_bert_job_status(job_id: str):
    """
    Verifica stato di un job di training BERT.

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


@router.get("/bert/models")
async def list_bert_models():
    """
    Lista tutti i modelli BERT disponibili (fine-tuned).

    Returns:
        Lista modelli con version_id, metrics, is_current
    """
    from app.services.bert_training_service import get_bert_training_service

    service = get_bert_training_service()
    models = service.list_available_models()

    return {
        "count": len(models),
        "models": models
    }


@router.get("/bert/history")
async def get_bert_history(limit: int = Query(20, description="Numero massimo versioni")):
    """
    Storico training BERT.

    Returns:
        Lista versioni con timestamp, metrics, type
    """
    from app.services.bert_training_service import get_bert_training_service

    service = get_bert_training_service()
    history = service.get_training_history(limit)

    return {
        "count": len(history),
        "history": history
    }


@router.post("/bert/rollback")
async def rollback_bert_model(request: BERTRollbackRequest):
    """
    Ripristina una versione precedente del modello BERT.

    Body:
        - version_id: ID versione da ripristinare

    Returns:
        - success: True se rollback riuscito
        - metrics: Metriche della versione ripristinata
    """
    from app.services.bert_training_service import get_bert_training_service

    service = get_bert_training_service()
    result = service.rollback_to_version(request.version_id)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Errore rollback"))

    return result


@router.post("/bert/predict")
async def bert_predict(text: str = Query(..., description="Testo da analizzare")):
    """
    Esegue predizione NER con il modello BERT corrente.

    Utile per testare il modello fine-tuned.

    Query:
        - text: Testo da analizzare

    Returns:
        Lista entità trovate con label, start, end, score
    """
    from app.services.bert_training_service import get_bert_training_service

    if not text or len(text) < 10:
        raise HTTPException(status_code=400, detail="Testo troppo corto")

    service = get_bert_training_service()
    entities = service.predict(text)

    return {
        "text": text[:500] + "..." if len(text) > 500 else text,
        "entities": entities,
        "count": len(entities)
    }


# ==================== BENCHMARK SEPARATI spaCy / BERT ====================


class SeparateBenchmarkRequest(BaseModel):
    """Request per benchmark separato."""
    email_ids: List[int]
    tipo: str = "interpello"
    name: Optional[str] = None


@router.post("/benchmark/spacy")
async def run_spacy_benchmark(
    request: SeparateBenchmarkRequest,
    db: Session = Depends(get_db)
):
    """
    Esegue benchmark SOLO su spaCy (EntityRuler + patterns).

    Confronta estrazione spaCy vs ground truth ChatGPT.
    """
    service = get_training_service()

    try:
        result = service.run_benchmark(
            email_ids=request.email_ids,
            tipo=request.tipo,
            benchmark_name=f"spacy_{request.name}" if request.name else None,
            db_session=db,
            engine="spacy"  # Solo spaCy
        )

        return {
            "success": True,
            "engine": "spacy",
            "message": f"Benchmark spaCy completato su {len(request.email_ids)} email",
            "benchmark": result
        }
    except Exception as e:
        logger.error(f"Errore benchmark spaCy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/benchmark/bert")
async def run_bert_benchmark(
    request: SeparateBenchmarkRequest,
    db: Session = Depends(get_db)
):
    """
    Esegue benchmark SOLO su BERT (modello fine-tuned).

    Confronta estrazione BERT vs ground truth ChatGPT.
    """
    from app.services.bert_training_service import get_bert_training_service

    bert_service = get_bert_training_service()
    training_service = get_training_service()

    # Verifica che ci sia un modello BERT
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

        # Carica email e analizza con BERT
        from app.models import Email

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

        # Salva benchmark
        benchmark_data = {
            "name": f"bert_{request.name}" if request.name else f"bert_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "timestamp": datetime.now().isoformat(),
            "engine": "bert",
            "tipo": request.tipo,
            "email_count": len(request.email_ids),
            "with_ground_truth": emails_with_gt,
            "metrics": metrics,
            "model_info": current,
            "results": results[:10]  # Solo primi 10 per non appesantire
        }

        return {
            "success": True,
            "engine": "bert",
            "message": f"Benchmark BERT completato su {len(request.email_ids)} email ({emails_with_gt} con ground truth)",
            "benchmark": benchmark_data
        }

    except Exception as e:
        logger.error(f"Errore benchmark BERT: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== CATEGORIZATION BENCHMARK ====================

class CategorizationBenchmarkRequest(BaseModel):
    """Request per benchmark categorizzazione."""
    email_ids: Optional[List[int]] = None
    limit: int = 50
    use_nlp: bool = True


@router.post("/benchmark/categorization")
async def run_categorization_benchmark(
    request: CategorizationBenchmarkRequest,
    db: Session = Depends(get_db)
):
    """
    Esegue benchmark sul SISTEMA DI PRODUZIONE di categorizzazione.

    Usa esattamente lo stesso flusso di email_polling.py:
    - EmailCategorizer(use_rules=True, use_nlp=True)
    - allegati_testo dal database

    Confronta la categorizzazione del sistema con le categorie salvate nel database.
    Restituisce accuracy globale e per categoria, più confusion matrix.
    """
    training_service = get_training_service()

    try:
        results = training_service.run_categorization_benchmark(
            email_ids=request.email_ids,
            limit=request.limit,
            db_session=db,
            use_nlp=request.use_nlp
        )

        return {
            "success": True,
            "results": results
        }

    except Exception as e:
        logger.error(f"Errore benchmark categorizzazione: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categorization/stats")
async def get_categorization_stats(db: Session = Depends(get_db)):
    """
    Recupera statistiche sulle categorie nel database.

    Restituisce conteggi per categoria e confidence medio.
    """
    training_service = get_training_service()

    try:
        stats = training_service.get_categorization_stats(db_session=db)
        return {
            "success": True,
            "stats": stats
        }

    except Exception as e:
        logger.error(f"Errore stats categorizzazione: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


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
                field_metrics[label] = {"correct": 0, "predicted": 0, "actual": 0}
            field_metrics[label]["actual"] += 1

        for label, text in pred_set:
            if label not in field_metrics:
                field_metrics[label] = {"correct": 0, "predicted": 0, "actual": 0}
            field_metrics[label]["predicted"] += 1
            if (label, text) in gt_set:
                field_metrics[label]["correct"] += 1

    # Calcola overall
    precision = total_correct / total_predicted if total_predicted > 0 else 0
    recall = total_correct / total_actual if total_actual > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    # Calcola per campo
    per_field = {}
    for field, m in field_metrics.items():
        p = m["correct"] / m["predicted"] if m["predicted"] > 0 else 0
        r = m["correct"] / m["actual"] if m["actual"] > 0 else 0
        f = 2 * p * r / (p + r) if (p + r) > 0 else 0
        per_field[field] = {
            "precision": round(p * 100, 1),
            "recall": round(r * 100, 1),
            "f1": round(f * 100, 1)
        }

    return {
        "overall": {
            "precision": round(precision * 100, 1),
            "recall": round(recall * 100, 1),
            "f1": round(f1 * 100, 1),
            "correct": total_correct,
            "predicted": total_predicted,
            "actual": total_actual
        },
        "per_field": per_field
    }


from datetime import datetime
