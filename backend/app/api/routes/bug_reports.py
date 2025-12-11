"""
API Routes per Bug Reports
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
import asyncio
import json

from app.database import get_db
from app.models.bug_report import BugReport
from app.services.claude_code_runner import get_claude_runner, build_bug_fix_prompt

# Stati e priorità validi (ora sono stringhe, non enum)
VALID_STATI = ['aperto', 'in_analisi', 'in_corso', 'risolto', 'chiuso', 'non_riproducibile']
VALID_PRIORITA = ['bassa', 'media', 'alta', 'critica']

router = APIRouter(prefix="/bugs", tags=["bugs"])


# Pydantic schemas
class BugReportCreate(BaseModel):
    descrizione: str
    pagina: Optional[str] = None
    componente: Optional[str] = None
    browser: Optional[str] = None
    viewport: Optional[str] = None
    console_errors: Optional[List[dict]] = None
    network_errors: Optional[List[dict]] = None
    email_id: Optional[int] = None
    azione_id: Optional[int] = None


class BugReportUpdate(BaseModel):
    stato: Optional[str] = None
    priorita: Optional[str] = None
    note_tecniche: Optional[str] = None
    file_coinvolti: Optional[List[str]] = None
    soluzione_proposta: Optional[str] = None


class BugReportResponse(BaseModel):
    id: int
    descrizione: str
    pagina: Optional[str]
    componente: Optional[str]
    browser: Optional[str]
    viewport: Optional[str]
    console_errors: Optional[List[dict]]
    network_errors: Optional[List[dict]]
    email_id: Optional[int]
    azione_id: Optional[int]
    stato: str
    priorita: str
    note_tecniche: Optional[str]
    file_coinvolti: Optional[List[str]]
    soluzione_proposta: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]
    resolved_at: Optional[str]

    class Config:
        from_attributes = True


@router.post("/", response_model=dict)
def create_bug_report(bug: BugReportCreate, db: Session = Depends(get_db)):
    """
    Crea un nuovo bug report dall'interfaccia utente.
    Raccoglie automaticamente i dati di contesto.
    """
    db_bug = BugReport(
        descrizione=bug.descrizione,
        pagina=bug.pagina,
        componente=bug.componente,
        browser=bug.browser,
        viewport=bug.viewport,
        console_errors=bug.console_errors,
        network_errors=bug.network_errors,
        email_id=bug.email_id,
        azione_id=bug.azione_id,
        stato='aperto',
        priorita='media'
    )

    db.add(db_bug)
    db.commit()
    db.refresh(db_bug)

    return {
        "success": True,
        "message": "Bug report salvato con successo",
        "bug_id": db_bug.id
    }


@router.get("/", response_model=List[dict])
def get_bug_reports(
    stato: Optional[str] = None,
    priorita: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Recupera tutti i bug reports, opzionalmente filtrati per stato/priorità.
    """
    query = db.query(BugReport)

    if stato and stato in VALID_STATI:
        query = query.filter(BugReport.stato == stato)

    if priorita and priorita in VALID_PRIORITA:
        query = query.filter(BugReport.priorita == priorita)

    bugs = query.order_by(BugReport.created_at.desc()).limit(limit).all()

    return [bug.to_dict() for bug in bugs]


@router.get("/open", response_model=List[dict])
def get_open_bugs(db: Session = Depends(get_db)):
    """
    Recupera tutti i bug aperti (non risolti/chiusi).
    Utile per Claude per vedere cosa c'è da risolvere.
    """
    open_stati = ['aperto', 'in_analisi', 'in_corso']

    bugs = db.query(BugReport).filter(
        BugReport.stato.in_(open_stati)
    ).order_by(
        BugReport.created_at.asc()  # Più vecchi prima
    ).all()

    return [bug.to_dict() for bug in bugs]


@router.get("/summary", response_model=dict)
def get_bugs_summary(db: Session = Depends(get_db)):
    """
    Riassunto dei bug per dashboard.
    """
    total = db.query(BugReport).count()
    aperti = db.query(BugReport).filter(BugReport.stato == 'aperto').count()
    in_corso = db.query(BugReport).filter(BugReport.stato == 'in_corso').count()
    risolti = db.query(BugReport).filter(BugReport.stato == 'risolto').count()
    critici = db.query(BugReport).filter(
        BugReport.priorita == 'critica',
        BugReport.stato.in_(['aperto', 'in_analisi', 'in_corso'])
    ).count()

    return {
        "totale": total,
        "aperti": aperti,
        "in_corso": in_corso,
        "risolti": risolti,
        "critici": critici
    }


# ============================================================
# FIX-ALL-STREAM - Deve essere PRIMA di /{bug_id} per evitare conflitto
# ============================================================

def build_all_bugs_prompt(bugs_data: List[dict]) -> str:
    """Costruisce un prompt unico per risolvere tutti i bug."""
    prompt = f"""Risolvi questi {len(bugs_data)} bug segnalati dagli utenti in sequenza.

IMPORTANTE:
- Risolvi TUTTI i bug elencati sotto, uno dopo l'altro
- Non fermarti finché non hai risolto tutti i bug
- Per ogni bug, identifica la causa, trova i file, applica la fix
- Dopo ogni fix, passa al bug successivo

"""

    for i, bug_info in enumerate(bugs_data, 1):
        bug = bug_info["dict"]
        prompt += f"""
---
## Bug {i}/{len(bugs_data)} - ID #{bug.get('id')}
**Descrizione:** {bug.get('descrizione')}
**Pagina:** {bug.get('pagina', 'N/A')}
**Viewport:** {bug.get('viewport', 'N/A')}
"""
        if bug.get('console_errors'):
            prompt += f"**Errori Console:** {json.dumps(bug['console_errors'])[:200]}\n"
        if bug.get('email_id'):
            prompt += f"**Email correlata:** ID {bug['email_id']}\n"

    prompt += """
---

## Istruzioni finali
1. Procedi in ordine dal Bug 1 all'ultimo
2. Per ogni bug: analizza → trova file → applica fix
3. Non chiedere conferme, procedi direttamente
4. Alla fine, fai un riepilogo di tutti i bug risolti
"""

    return prompt


@router.get("/fix-all-stream")
async def fix_all_bugs_stream(db: Session = Depends(get_db)):
    """
    Risolve TUTTI i bug aperti in un'UNICA sessione Claude Code.
    Questo evita di dover rileggere il codebase per ogni bug.
    """
    # Recupera tutti i bug aperti
    open_stati = ['aperto', 'in_analisi']
    bugs = db.query(BugReport).filter(
        BugReport.stato.in_(open_stati)
    ).order_by(
        BugReport.created_at.asc()
    ).all()

    if not bugs:
        raise HTTPException(status_code=404, detail="Nessun bug aperto da risolvere")

    # Prepara i dati dei bug PRIMA del generator
    bugs_data = [{"id": b.id, "dict": b.to_dict()} for b in bugs]
    bug_ids = [b.id for b in bugs]

    # Aggiorna stato di tutti i bug a "in_corso"
    for bug in bugs:
        bug.stato = "in_corso"
        bug.updated_at = datetime.utcnow()
    db.commit()

    # Costruisci un UNICO prompt con tutti i bug
    prompt = build_all_bugs_prompt(bugs_data)

    from app.database import SessionLocal

    async def event_generator():
        runner = get_claude_runner()
        final_success = False

        # Evento iniziale con lista bug
        yield f"data: {json.dumps({'type': 'batch_start', 'bug_ids': bug_ids, 'count': len(bug_ids)})}\n\n"

        try:
            async for event in runner.run_prompt(prompt, timeout=600):  # 10 minuti per batch
                data = json.dumps(event, ensure_ascii=False)
                yield f"data: {data}\n\n"

                if event.get("type") == "complete":
                    final_success = event.get("success", False)

        except Exception as e:
            error_event = {"type": "error", "message": str(e)}
            yield f"data: {json.dumps(error_event)}\n\n"

        # Aggiorna stato di tutti i bug
        try:
            new_db = SessionLocal()
            try:
                for bug_id in bug_ids:
                    bug_to_update = new_db.query(BugReport).filter(BugReport.id == bug_id).first()
                    if bug_to_update:
                        if final_success:
                            bug_to_update.stato = "risolto"
                            bug_to_update.resolved_at = datetime.utcnow()
                        else:
                            bug_to_update.stato = "aperto"
                        bug_to_update.updated_at = datetime.utcnow()
                new_db.commit()
            finally:
                new_db.close()
        except Exception as db_error:
            yield f"data: {json.dumps({'type': 'db_error', 'message': str(db_error)})}\n\n"

        yield f"data: {json.dumps({'type': 'batch_done', 'success': final_success, 'count': len(bug_ids)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ============================================================


@router.get("/{bug_id}", response_model=dict)
def get_bug_report(bug_id: int, db: Session = Depends(get_db)):
    """
    Recupera un singolo bug report con tutti i dettagli.
    """
    bug = db.query(BugReport).filter(BugReport.id == bug_id).first()
    if not bug:
        raise HTTPException(status_code=404, detail="Bug report non trovato")

    return bug.to_dict()


@router.patch("/{bug_id}", response_model=dict)
def update_bug_report(bug_id: int, update: BugReportUpdate, db: Session = Depends(get_db)):
    """
    Aggiorna un bug report (stato, priorità, note tecniche, soluzione).
    Usato da Claude per documentare l'analisi e la risoluzione.
    """
    bug = db.query(BugReport).filter(BugReport.id == bug_id).first()
    if not bug:
        raise HTTPException(status_code=404, detail="Bug report non trovato")

    if update.stato:
        if update.stato not in VALID_STATI:
            raise HTTPException(status_code=400, detail=f"Stato non valido: {update.stato}")
        bug.stato = update.stato
        if update.stato == 'risolto':
            bug.resolved_at = datetime.utcnow()

    if update.priorita:
        if update.priorita not in VALID_PRIORITA:
            raise HTTPException(status_code=400, detail=f"Priorità non valida: {update.priorita}")
        bug.priorita = update.priorita

    if update.note_tecniche is not None:
        bug.note_tecniche = update.note_tecniche

    if update.file_coinvolti is not None:
        bug.file_coinvolti = update.file_coinvolti

    if update.soluzione_proposta is not None:
        bug.soluzione_proposta = update.soluzione_proposta

    bug.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(bug)

    return {
        "success": True,
        "message": "Bug report aggiornato",
        "bug": bug.to_dict()
    }


@router.delete("/{bug_id}", response_model=dict)
def delete_bug_report(bug_id: int, db: Session = Depends(get_db)):
    """
    Elimina un bug report.
    """
    bug = db.query(BugReport).filter(BugReport.id == bug_id).first()
    if not bug:
        raise HTTPException(status_code=404, detail="Bug report non trovato")

    db.delete(bug)
    db.commit()

    return {
        "success": True,
        "message": f"Bug report {bug_id} eliminato"
    }


@router.get("/{bug_id}/fix-stream")
async def fix_bug_stream(bug_id: int, db: Session = Depends(get_db)):
    """
    Avvia Claude Code per risolvere un bug e ritorna output in streaming SSE.

    Usa Server-Sent Events per streaming real-time dell'output.
    """
    bug = db.query(BugReport).filter(BugReport.id == bug_id).first()
    if not bug:
        raise HTTPException(status_code=404, detail="Bug report non trovato")

    # Aggiorna stato bug
    bug.stato = "in_corso"
    bug.updated_at = datetime.utcnow()
    db.commit()

    # Costruisci prompt PRIMA di entrare nel generator
    bug_dict = bug.to_dict()
    prompt = build_bug_fix_prompt(bug_dict)

    # Importa qui per evitare circular imports e per avere accesso al SessionLocal
    from app.database import SessionLocal

    async def event_generator():
        runner = get_claude_runner()
        final_success = False

        try:
            async for event in runner.run_prompt(prompt):
                # Formato SSE
                data = json.dumps(event, ensure_ascii=False)
                yield f"data: {data}\n\n"

                # Traccia il successo
                if event.get("type") == "complete":
                    final_success = event.get("success", False)

        except Exception as e:
            error_event = {"type": "error", "message": str(e)}
            yield f"data: {json.dumps(error_event)}\n\n"

        # Aggiorna stato bug con una NUOVA sessione DB
        try:
            new_db = SessionLocal()
            try:
                bug_to_update = new_db.query(BugReport).filter(BugReport.id == bug_id).first()
                if bug_to_update:
                    if final_success:
                        bug_to_update.stato = "risolto"
                        bug_to_update.resolved_at = datetime.utcnow()
                    else:
                        bug_to_update.stato = "aperto"  # Torna ad aperto se fallito
                    bug_to_update.updated_at = datetime.utcnow()
                    new_db.commit()
            finally:
                new_db.close()
        except Exception as db_error:
            yield f"data: {json.dumps({'type': 'db_error', 'message': str(db_error)})}\n\n"

        # Evento finale
        yield f"data: {json.dumps({'type': 'done', 'success': final_success})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/{bug_id}/fix")
async def fix_bug(bug_id: int, db: Session = Depends(get_db)):
    """
    Avvia Claude Code per risolvere un bug (versione non-streaming).
    Ritorna il risultato completo alla fine.
    """
    bug = db.query(BugReport).filter(BugReport.id == bug_id).first()
    if not bug:
        raise HTTPException(status_code=404, detail="Bug report non trovato")

    # Aggiorna stato bug
    bug.stato = "in_corso"
    bug.updated_at = datetime.utcnow()
    db.commit()

    # Costruisci prompt
    prompt = build_bug_fix_prompt(bug.to_dict())

    runner = get_claude_runner()
    outputs = []
    success = False

    try:
        async for event in runner.run_prompt(prompt, timeout=300):
            outputs.append(event)
            if event.get("type") == "complete":
                success = event.get("success", False)

        if success:
            bug.stato = "risolto"
            bug.resolved_at = datetime.utcnow()
        else:
            bug.stato = "aperto"  # Ritorna ad aperto se fallito

        db.commit()

    except Exception as e:
        outputs.append({"type": "error", "message": str(e)})
        bug.stato = "aperto"
        db.commit()

    return {
        "success": success,
        "bug_id": bug_id,
        "outputs": outputs
    }
