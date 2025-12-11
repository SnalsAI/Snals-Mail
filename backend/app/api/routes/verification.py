"""
API Routes per Verifica Estrazioni - Confronto locale vs OpenAI

Questi endpoint permettono di confrontare le estrazioni del LLM locale
con OpenAI per identificare discrepanze e migliorare gli algoritmi.
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import Email, Interpello, EventoCalendario
from app.services.verification_service import get_verification_service, VerificationService
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/verification", tags=["Verification"])
settings = get_settings()


class VerifyTextRequest(BaseModel):
    """Request per verifica di testo generico."""
    testo: str
    tipo: str = "interpello"  # interpello, calendario, categorizzazione


class VerifyEmailRequest(BaseModel):
    """Request per verifica email."""
    email_id: int
    tipo: str = "auto"  # auto, interpello, calendario, categorizzazione


class VerificationResponse(BaseModel):
    """Response standard per verifica."""
    success: bool
    message: str
    data: dict


@router.get("/status")
async def get_verification_status():
    """
    Verifica lo stato del servizio di verifica.

    Returns:
        - openai_available: True se OpenAI è configurato
        - ollama_available: True se Ollama è disponibile
        - hybrid_available: True se HybridExtractor è disponibile
        - nlp_available: True se spaCy + BERT sono disponibili
        - nlp_stats: Statistiche sui training data NLP
    """
    service = get_verification_service()

    # NLP statistics
    nlp_stats = None
    try:
        from app.services.nlp_training_data import get_training_data
        td = get_training_data()
        patterns = td.get_entity_ruler_patterns()

        # Conta pattern per tipo
        counts = {}
        for p in patterns:
            label = p.get("label", "UNKNOWN")
            counts[label] = counts.get(label, 0) + 1

        nlp_stats = {
            "total_patterns": len(patterns),
            "classi_concorso": counts.get("CLASSE_CONCORSO", 0),
            "meccanografici": counts.get("MECCANOGRAFICO", 0),
            "istituti": counts.get("ISTITUTO", 0),
            "province": counts.get("PROVINCIA", 0)
        }
    except Exception as e:
        logger.warning(f"Impossibile caricare stats NLP: {e}")

    return {
        "openai_available": service.is_openai_available(),
        "ollama_available": service.ollama_extractor is not None,
        "hybrid_available": service.hybrid_extractor is not None,
        "nlp_available": service.nlp_extractor is not None,
        "nlp_stats": nlp_stats,
        "openai_model": getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini'),
        "message": "OpenAI API key richiesta per verifiche" if not service.is_openai_available() else "Servizio pronto"
    }


@router.post("/interpello")
async def verify_interpello(
    request: VerifyTextRequest,
    model: Optional[str] = Query(None, description="Modello OpenAI da usare (es: gpt-4o-mini, gpt-4o)"),
    db: Session = Depends(get_db)
):
    """
    Verifica estrazione interpello confrontando locale vs OpenAI.

    Body:
        - testo: Testo dell'interpello da analizzare
    Query:
        - model: Modello OpenAI (opzionale)
    """
    service = get_verification_service()

    if not service.is_openai_available():
        raise HTTPException(
            status_code=400,
            detail="OpenAI API key non configurata. Aggiungi OPENAI_API_KEY nel .env"
        )

    try:
        results = service.verify_interpello(request.testo, model=model)
        return VerificationResponse(
            success=True,
            message=f"Verifica completata. {len(results.get('discrepancies', []))} discrepanze trovate.",
            data=results
        )
    except Exception as e:
        logger.error(f"Errore verifica interpello: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/calendario")
async def verify_calendario(
    request: VerifyTextRequest,
    model: Optional[str] = Query(None, description="Modello OpenAI da usare"),
    db: Session = Depends(get_db)
):
    """
    Verifica estrazione evento calendario confrontando locale vs OpenAI.

    Body:
        - testo: Testo dell'email con convocazione
    Query:
        - model: Modello OpenAI (opzionale)
    """
    service = get_verification_service()

    if not service.is_openai_available():
        raise HTTPException(
            status_code=400,
            detail="OpenAI API key non configurata. Aggiungi OPENAI_API_KEY nel .env"
        )

    try:
        results = service.verify_calendar_event(request.testo, model=model)
        return VerificationResponse(
            success=True,
            message=f"Verifica completata. {len(results.get('discrepancies', []))} discrepanze trovate.",
            data=results
        )
    except Exception as e:
        logger.error(f"Errore verifica calendario: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/categorizzazione")
async def verify_categorizzazione(
    oggetto: str,
    corpo: str,
    model: Optional[str] = Query(None, description="Modello OpenAI da usare"),
    db: Session = Depends(get_db)
):
    """
    Verifica categorizzazione email confrontando locale vs OpenAI.

    Query params:
        - oggetto: Oggetto dell'email
        - corpo: Corpo dell'email
        - model: Modello OpenAI (opzionale)
    """
    service = get_verification_service()

    if not service.is_openai_available():
        raise HTTPException(
            status_code=400,
            detail="OpenAI API key non configurata. Aggiungi OPENAI_API_KEY nel .env"
        )

    try:
        results = service.verify_categorization(oggetto, corpo, model=model)
        return VerificationResponse(
            success=True,
            message=f"Verifica completata. {len(results.get('discrepancies', []))} discrepanze trovate.",
            data=results
        )
    except Exception as e:
        logger.error(f"Errore verifica categorizzazione: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/email/{email_id}")
async def verify_email_by_id(
    email_id: int,
    tipo: str = Query("auto", description="Tipo verifica: auto, interpello, calendario, categorizzazione"),
    model: Optional[str] = Query(None, description="Modello OpenAI da usare"),
    db: Session = Depends(get_db)
):
    """
    Verifica estrazione per una specifica email.

    Path params:
        - email_id: ID dell'email

    Query params:
        - tipo: Tipo di verifica (auto determina dal tipo email)
    """
    service = get_verification_service()

    if not service.is_openai_available():
        raise HTTPException(
            status_code=400,
            detail="OpenAI API key non configurata. Aggiungi OPENAI_API_KEY nel .env"
        )

    # Carica email
    email = db.query(Email).filter(Email.id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email non trovata")

    # Costruisci testo completo
    testo_completo = f"Oggetto: {email.oggetto}\n\n"
    if email.corpo_testo:
        testo_completo += email.corpo_testo[:3000]
    if email.allegati_testo and isinstance(email.allegati_testo, dict):
        for filename, testo in email.allegati_testo.items():
            if testo:
                testo_completo += f"\n\n--- {filename} ---\n{testo[:2000]}"

    # Determina tipo se auto
    if tipo == "auto":
        categoria = email.categoria
        if categoria == "interpello":
            tipo = "interpello"
        elif categoria == "convocazione_riunione":
            tipo = "calendario"
        else:
            tipo = "categorizzazione"

    try:
        if tipo == "interpello":
            results = service.verify_interpello(testo_completo, model=model)
        elif tipo == "calendario":
            results = service.verify_calendar_event(testo_completo, model=model)
        else:
            results = service.verify_categorization(email.oggetto, testo_completo, model=model)

        # Aggiungi info email
        results['email_info'] = {
            'id': email.id,
            'oggetto': email.oggetto,
            'categoria': email.categoria,
            'mittente': email.mittente
        }

        return VerificationResponse(
            success=True,
            message=f"Verifica {tipo} completata per email {email_id}. {len(results.get('discrepancies', []))} discrepanze.",
            data=results
        )

    except Exception as e:
        logger.error(f"Errore verifica email {email_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/interpelli/batch")
async def verify_interpelli_batch(
    limit: int = Query(5, description="Numero max di interpelli da verificare"),
    model: Optional[str] = Query(None, description="Modello OpenAI da usare"),
    db: Session = Depends(get_db)
):
    """
    Verifica batch di interpelli esistenti confrontando con OpenAI.

    Utile per identificare pattern di errore negli algoritmi locali.
    """
    service = get_verification_service()

    if not service.is_openai_available():
        raise HTTPException(
            status_code=400,
            detail="OpenAI API key non configurata"
        )

    # Carica interpelli recenti con le loro email
    interpelli = db.query(Interpello).order_by(Interpello.id.desc()).limit(limit).all()

    results = []
    for interpello in interpelli:
        email = db.query(Email).filter(Email.id == interpello.email_id).first()
        if not email:
            continue

        # Costruisci testo
        testo = f"Oggetto: {email.oggetto}\n"
        if email.corpo_testo:
            testo += email.corpo_testo[:2000]
        if email.allegati_testo:
            for _, t in (email.allegati_testo or {}).items():
                if t:
                    testo += f"\n{t[:1500]}"

        try:
            verification = service.verify_interpello(testo, model=model)

            # Confronta con dati salvati
            saved_data = {
                'classe_concorso': interpello.classe_concorso,
                'ore_settimanali': interpello.ore_settimanali,
                'provincia': interpello.provincia,
                'istituto': interpello.istituto
            }

            verification['saved_data'] = saved_data
            verification['interpello_id'] = interpello.id
            verification['email_id'] = email.id

            results.append(verification)
        except Exception as e:
            results.append({
                'interpello_id': interpello.id,
                'error': str(e)
            })

    # Riepilogo discrepanze
    total_discrepancies = sum(
        len(r.get('discrepancies', [])) for r in results if 'discrepancies' in r
    )

    return {
        "success": True,
        "message": f"Verificati {len(results)} interpelli. {total_discrepancies} discrepanze totali.",
        "count": len(results),
        "total_discrepancies": total_discrepancies,
        "results": results
    }


@router.get("/calendari/batch")
async def verify_calendari_batch(
    limit: int = Query(5, description="Numero max di eventi da verificare"),
    model: Optional[str] = Query(None, description="Modello OpenAI da usare"),
    db: Session = Depends(get_db)
):
    """
    Verifica batch di eventi calendario esistenti confrontando con OpenAI.
    """
    service = get_verification_service()

    if not service.is_openai_available():
        raise HTTPException(
            status_code=400,
            detail="OpenAI API key non configurata"
        )

    # Carica eventi recenti
    eventi = db.query(EventoCalendario).order_by(EventoCalendario.id.desc()).limit(limit).all()

    results = []
    for evento in eventi:
        email = db.query(Email).filter(Email.id == evento.email_id).first()
        if not email:
            continue

        # Costruisci testo
        testo = f"Oggetto: {email.oggetto}\n"
        if email.corpo_testo:
            testo += email.corpo_testo[:2000]
        if email.allegati_testo:
            for _, t in (email.allegati_testo or {}).items():
                if t:
                    testo += f"\n{t[:1500]}"

        try:
            verification = service.verify_calendar_event(testo, model=model)

            # Confronta con dati salvati
            saved_data = {
                'data_inizio': str(evento.data_inizio.date()) if evento.data_inizio else None,
                'ora_inizio': evento.data_inizio.strftime('%H:%M') if evento.data_inizio else None,
                'luogo': evento.luogo,
                'titolo': evento.titolo
            }

            verification['saved_data'] = saved_data
            verification['evento_id'] = evento.id
            verification['email_id'] = email.id

            results.append(verification)
        except Exception as e:
            results.append({
                'evento_id': evento.id,
                'error': str(e)
            })

    total_discrepancies = sum(
        len(r.get('discrepancies', [])) for r in results if 'discrepancies' in r
    )

    return {
        "success": True,
        "message": f"Verificati {len(results)} eventi. {total_discrepancies} discrepanze totali.",
        "count": len(results),
        "total_discrepancies": total_discrepancies,
        "results": results
    }
