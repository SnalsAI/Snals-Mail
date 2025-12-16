"""
API Routes per gestione Pattern NLP.

Endpoint per:
- Listare pattern (base, trained, manuali)
- CRUD pattern manuali
- Preview pattern su testo
- Statistiche pattern
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.pattern_service import get_pattern_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/training/patterns", tags=["NLP Patterns"])


# ============================================
# REQUEST/RESPONSE MODELS
# ============================================

class AddPatternRequest(BaseModel):
    """Request per aggiungere un pattern manuale."""
    label: str
    pattern: str
    description: Optional[str] = None


class UpdatePatternRequest(BaseModel):
    """Request per modificare un pattern."""
    label: Optional[str] = None
    pattern: Optional[str] = None
    description: Optional[str] = None


class PreviewPatternRequest(BaseModel):
    """Request per preview pattern su testo."""
    pattern: str
    label: str
    text: str


class PatternResponse(BaseModel):
    """Response per un singolo pattern."""
    id: str
    label: str
    pattern: str
    source: str
    description: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class PatternListResponse(BaseModel):
    """Response per lista pattern."""
    patterns: List[dict]
    total: int
    by_source: dict
    by_label: dict


# ============================================
# ENDPOINTS
# ============================================

@router.get("")
async def list_patterns(
    source: Optional[str] = Query(None, description="Filtra per source: base, trained, manual, all"),
    label: Optional[str] = Query(None, description="Filtra per label: CLASSE_CONCORSO, MECCANOGRAFICO, etc.")
):
    """
    Lista tutti i pattern.

    Query params:
        - source: 'base', 'trained', 'manual', o None per tutti
        - label: Label specifica da filtrare

    Returns:
        Lista pattern con statistiche
    """
    service = get_pattern_service()

    patterns = service.get_all_patterns(source=source, label=label)
    stats = service.get_pattern_stats()

    return {
        "patterns": patterns,
        "total": len(patterns),
        "by_source": stats["by_source"],
        "by_label": stats["by_label"]
    }


@router.get("/stats")
async def get_pattern_stats():
    """
    Restituisce statistiche sui pattern.

    Returns:
        Conteggi per source e label
    """
    service = get_pattern_service()
    return service.get_pattern_stats()


@router.get("/history")
async def get_pattern_history(
    limit: int = Query(50, description="Numero massimo di entry")
):
    """
    Restituisce storico modifiche pattern manuali.

    Returns:
        Lista entry storico (più recenti prima)
    """
    service = get_pattern_service()
    return {
        "history": service.get_pattern_history(limit=limit)
    }


@router.post("")
async def add_pattern(request: AddPatternRequest):
    """
    Aggiunge un nuovo pattern manuale.

    Body:
        - label: Tipo entità (CLASSE_CONCORSO, MECCANOGRAFICO, etc.)
        - pattern: Testo del pattern
        - description: Descrizione opzionale

    Returns:
        Pattern creato
    """
    service = get_pattern_service()

    try:
        pattern = service.add_manual_pattern(
            label=request.label,
            pattern=request.pattern,
            description=request.description
        )
        return {
            "success": True,
            "pattern": pattern,
            "message": f"Pattern '{request.pattern}' aggiunto con successo"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Errore aggiunta pattern: {e}")
        raise HTTPException(status_code=500, detail="Errore interno")


@router.put("/{pattern_id}")
async def update_pattern(pattern_id: str, request: UpdatePatternRequest):
    """
    Modifica un pattern manuale esistente.

    Path params:
        - pattern_id: ID del pattern da modificare

    Body:
        - label: Nuovo label (opzionale)
        - pattern: Nuovo testo pattern (opzionale)
        - description: Nuova descrizione (opzionale)

    Returns:
        Pattern aggiornato
    """
    service = get_pattern_service()

    try:
        pattern = service.update_manual_pattern(
            pattern_id=pattern_id,
            label=request.label,
            pattern=request.pattern,
            description=request.description
        )
        return {
            "success": True,
            "pattern": pattern,
            "message": "Pattern aggiornato con successo"
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Errore aggiornamento pattern: {e}")
        raise HTTPException(status_code=500, detail="Errore interno")


@router.delete("/{pattern_id}")
async def delete_pattern(pattern_id: str):
    """
    Elimina un pattern manuale.

    Path params:
        - pattern_id: ID del pattern da eliminare

    Returns:
        Conferma eliminazione
    """
    service = get_pattern_service()

    try:
        service.delete_manual_pattern(pattern_id)
        return {
            "success": True,
            "message": f"Pattern {pattern_id} eliminato con successo"
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Errore eliminazione pattern: {e}")
        raise HTTPException(status_code=500, detail="Errore interno")


@router.post("/preview")
async def preview_pattern(request: PreviewPatternRequest):
    """
    Testa un pattern su un testo e mostra le corrispondenze.

    Body:
        - pattern: Testo del pattern da testare
        - label: Label del pattern
        - text: Testo su cui testare

    Returns:
        Lista match con posizioni
    """
    service = get_pattern_service()

    matches = service.preview_pattern(
        pattern=request.pattern,
        label=request.label,
        text=request.text
    )

    return {
        "pattern": request.pattern,
        "label": request.label,
        "text_length": len(request.text),
        "matches_count": len(matches),
        "matches": matches
    }


@router.get("/export")
async def export_patterns():
    """
    Esporta tutti i pattern in formato EntityRuler di spaCy.

    Returns:
        Lista pattern in formato spaCy
    """
    service = get_pattern_service()
    patterns = service.export_for_entity_ruler()

    return {
        "format": "spacy_entity_ruler",
        "count": len(patterns),
        "patterns": patterns
    }


@router.get("/labels")
async def get_valid_labels():
    """
    Restituisce la lista di label valide per i pattern.

    Returns:
        Lista label
    """
    service = get_pattern_service()
    return {
        "labels": service.VALID_LABELS
    }
