"""
API Routes per Training spaCy - EntityRuler e pattern-based extraction.

Endpoint per:
- Status modello spaCy
- Applicazione pattern da sample approvati
- Benchmark spaCy-only
- Rollback versione pattern
- Export formato spaCy
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.services.training_service import get_training_service
from app.services.pattern_service import get_pattern_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/training/spacy", tags=["spaCy Training"])


# ============================================
# REQUEST/RESPONSE MODELS
# ============================================

class SpacyBenchmarkRequest(BaseModel):
    """Request per benchmark spaCy."""
    email_ids: List[int]
    tipo: str = "interpello"
    name: Optional[str] = None


class SpacyRollbackRequest(BaseModel):
    """Request per rollback spaCy patterns."""
    version_id: Optional[str] = None  # Se None, usa backup più recente


# ============================================
# ENDPOINTS
# ============================================

@router.get("/status")
async def get_spacy_status():
    """
    Restituisce stato del modello spaCy.

    Returns:
        - is_available: True se spaCy caricato
        - current_version: Versione corrente pattern
        - patterns_count: Numero totale pattern
        - pattern_stats: Statistiche per label e source
        - last_training: Data ultimo training applicato
    """
    training_service = get_training_service()
    pattern_service = get_pattern_service()

    # Versione corrente
    version_info = training_service.get_current_version()
    pattern_stats = pattern_service.get_pattern_stats()

    # Verifica spaCy disponibile
    spacy_available = True
    try:
        from app.services.nlp_service import get_nlp_extractor
        extractor = get_nlp_extractor()
        spacy_available = extractor is not None
    except Exception as e:
        logger.warning(f"⚠️ spaCy non disponibile: {e}")
        spacy_available = False

    return {
        "is_available": spacy_available,
        "current_version": version_info.get("version_id"),
        "patterns_count": pattern_stats["total"],
        "pattern_stats": pattern_stats,
        "last_training": version_info.get("timestamp"),
        "backup_available": training_service.get_backup_info().get("backup_available", False)
    }


@router.post("/apply")
async def apply_spacy_training():
    """
    Applica il training approvato all'EntityRuler di spaCy.

    IMPORTANTE:
    - Solo i sample APPROVATI vengono usati per creare nuovi pattern
    - Crea automaticamente un BACKUP prima di applicare modifiche
    - Dopo l'applicazione, ricarica automaticamente il modello

    Returns:
        - success: True se applicato
        - patterns_added: Numero pattern aggiunti
        - total_patterns: Totale pattern nel file
        - backup_available: True se rollback possibile
        - version_id: ID versione creata
    """
    service = get_training_service()

    result = service.apply_training()

    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("message", "Errore applicazione training")
        )

    # Ricarica modello automaticamente
    try:
        from app.services.nlp_service import reload_nlp_model
        reload_nlp_model()
        result["model_reloaded"] = True
    except Exception as e:
        logger.warning(f"⚠️ Pattern applicati ma modello non ricaricato: {e}")
        result["model_reloaded"] = False
        result["reload_warning"] = str(e)

    return result


@router.post("/rollback")
async def rollback_spacy_training(request: SpacyRollbackRequest = None):
    """
    Ripristina i pattern spaCy allo stato precedente.

    Utile se il benchmark DOPO mostra performance peggiori.
    Ripristina dal backup creato durante l'ultimo apply.

    Body (opzionale):
        - version_id: ID versione specifica da ripristinare (default: ultimo backup)

    Returns:
        - success: True se ripristinato
        - restored_patterns: Numero pattern ripristinati
        - backup_timestamp: Data/ora del backup
    """
    service = get_training_service()

    result = service.rollback_training()

    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("message", "Errore rollback")
        )

    # Ricarica modello dopo rollback
    try:
        from app.services.nlp_service import reload_nlp_model
        reload_nlp_model()
        result["model_reloaded"] = True
    except Exception as e:
        logger.warning(f"⚠️ Pattern ripristinati ma modello non ricaricato: {e}")
        result["model_reloaded"] = False

    return result


@router.post("/reload")
async def reload_spacy_model():
    """
    Ricarica il modello spaCy con i pattern correnti.

    Necessario per rendere effettivi i nuovi pattern senza riavviare il container.

    Returns:
        - success: True se ricaricato
        - patterns_loaded: Numero pattern caricati
    """
    try:
        from app.services.nlp_service import reload_nlp_model
        reload_nlp_model()

        # Conta pattern caricati
        pattern_service = get_pattern_service()
        stats = pattern_service.get_pattern_stats()

        return {
            "success": True,
            "message": "Modello spaCy ricaricato",
            "patterns_loaded": stats["total"]
        }
    except Exception as e:
        logger.error(f"❌ Errore reload spaCy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/benchmark")
async def run_spacy_benchmark(
    request: SpacyBenchmarkRequest,
    db: Session = Depends(get_db)
):
    """
    Esegue benchmark SOLO su spaCy (EntityRuler + patterns).

    Confronta estrazione spaCy vs ground truth (ChatGPT approvati).

    Body:
        - email_ids: Lista ID email da testare
        - tipo: Tipo estrazione (interpello, calendario)
        - name: Nome opzionale per il benchmark

    Returns:
        - success: True se completato
        - engine: "spacy"
        - benchmark: Risultati con metriche
    """
    service = get_training_service()

    if not request.email_ids:
        raise HTTPException(status_code=400, detail="Nessuna email selezionata")

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
        logger.error(f"❌ Errore benchmark spaCy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_spacy_history(
    limit: int = Query(20, description="Numero massimo versioni")
):
    """
    Restituisce lo storico delle versioni di training spaCy.

    Mostra tutte le applicazioni di training e i rollback effettuati.

    Returns:
        - count: Numero versioni
        - history: Lista versioni
    """
    service = get_training_service()
    history = service.get_training_history(limit)

    return {
        "count": len(history),
        "history": history
    }


@router.get("/backup-info")
async def get_spacy_backup_info():
    """
    Restituisce informazioni sul backup disponibile per rollback.

    Returns:
        - backup_available: True se backup presente
        - backup_timestamp: Data/ora backup
        - patterns_count: Numero pattern nel backup
    """
    service = get_training_service()
    return service.get_backup_info()


@router.get("/export")
async def export_spacy_format(
    approved_only: bool = Query(True, description="Solo sample approvati")
):
    """
    Esporta training data in formato spaCy.

    Query params:
        - approved_only: Se True, esporta solo sample approvati

    Returns:
        JSON con training data in formato spaCy
    """
    service = get_training_service()
    data = service.export_spacy_format(approved_only=approved_only)

    return JSONResponse(
        content=data,
        headers={
            "Content-Disposition": f"attachment; filename=training_spacy_{data['total_samples']}.json"
        }
    )


@router.post("/test")
async def test_spacy_extraction(
    text: str = Query(..., description="Testo da analizzare"),
    tipo: str = Query("interpello", description="Tipo estrazione")
):
    """
    Testa l'estrazione spaCy su un testo.

    Query params:
        - text: Testo da analizzare
        - tipo: Tipo estrazione (interpello, calendario, generico)

    Returns:
        - entities: Entità estratte
        - extraction_time_ms: Tempo estrazione
    """
    import time

    try:
        from app.services.nlp_service import get_nlp_extractor

        extractor = get_nlp_extractor()

        start = time.time()

        if tipo == "interpello":
            result = extractor.extract_for_interpello(text)
        elif tipo == "calendario":
            result = extractor.extract_calendar_event(text)
        else:
            result = extractor.extract_entities(text)

        elapsed_ms = (time.time() - start) * 1000

        return {
            "success": True,
            "tipo": tipo,
            "text_length": len(text),
            "extraction_time_ms": round(elapsed_ms, 2),
            "result": result
        }
    except Exception as e:
        logger.error(f"❌ Errore test spaCy: {e}")
        raise HTTPException(status_code=500, detail=str(e))
