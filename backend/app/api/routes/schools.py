"""
API Routes per gestione Scuole.

Endpoint per identificare scuole, cercare nel database,
e visualizzare informazioni.
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from app.services.school_identifier import get_school_identifier
from app.services.school_updater import get_school_updater

router = APIRouter(prefix="/schools", tags=["schools"])


class SchoolAddRequest(BaseModel):
    """Request per aggiungere nuova scuola."""
    school_code: str
    force_search: bool = True


class SchoolApproveRequest(BaseModel):
    """Request per approvare una scuola proposta."""
    nome: Optional[str] = None
    comune: Optional[str] = None
    indirizzo: Optional[str] = None
    tipo: Optional[str] = None


@router.get("/identify")
def identify_school_from_email(
    email: str = Query(..., description="Indirizzo email da cui estrarre il codice scuola")
):
    """
    Identifica scuola da indirizzo email mittente.

    Estrae il codice meccanografico dall'email e restituisce
    informazioni complete sulla scuola.
    """
    school_identifier = get_school_identifier()
    school_info = school_identifier.identify_from_email(email)

    if not school_info:
        return {
            "found": False,
            "message": "Scuola non identificata da questo indirizzo email"
        }

    return {
        "found": True,
        "school": school_info
    }


@router.get("/search")
def search_schools(
    q: str = Query(..., min_length=2, description="Testo da cercare (nome o comune)"),
    limit: int = Query(20, ge=1, le=100, description="Numero massimo risultati")
):
    """
    Cerca scuole per nome o comune.

    Restituisce lista di scuole che corrispondono alla query.
    """
    school_identifier = get_school_identifier()
    schools = school_identifier.search_schools(q)

    return {
        "total": len(schools),
        "limit": limit,
        "schools": schools[:limit]
    }


@router.get("/by-comune/{comune}")
def get_schools_by_comune(comune: str):
    """
    Recupera tutte le scuole di un comune specifico.

    Args:
        comune: Nome del comune (es: "TARANTO", "MASSAFRA")
    """
    school_identifier = get_school_identifier()
    schools = school_identifier.get_schools_by_comune(comune)

    return {
        "comune": comune.upper(),
        "total": len(schools),
        "schools": schools
    }


@router.get("/by-district/{district}")
def get_schools_by_district(district: str):
    """
    Recupera tutte le scuole di un distretto specifico.

    Args:
        district: Numero distretto (es: "049", "050", "051")
    """
    school_identifier = get_school_identifier()
    schools = school_identifier.get_schools_by_district(district)

    return {
        "district": district,
        "total": len(schools),
        "schools": schools
    }


@router.get("/stats")
def get_database_stats():
    """
    Recupera statistiche sul database scuole.

    Include conteggi per comune, distretto, data ultimo aggiornamento.
    """
    school_identifier = get_school_identifier()

    comuni = {}
    distretti = {}
    last_verified_dates = []

    for code, info in school_identifier.schools_db.items():
        # Conteggio per comune
        comune = info.get("comune", "N/A")
        comuni[comune] = comuni.get(comune, 0) + 1

        # Conteggio per distretto
        distretto = info.get("distretto", "N/A")
        distretti[distretto] = distretti.get(distretto, 0) + 1

        # Date verifica
        if info.get("last_verified"):
            last_verified_dates.append(info["last_verified"])

    return {
        "total_schools": len(school_identifier.schools_db),
        "comuni": dict(sorted(comuni.items())),
        "distretti": dict(sorted(distretti.items())),
        "verified_count": len(last_verified_dates),
        "last_update": max(last_verified_dates) if last_verified_dates else None
    }


@router.get("/{school_code}")
def get_school_info(school_code: str):
    """
    Recupera informazioni su una scuola dal codice meccanografico.

    Args:
        school_code: Codice meccanografico della scuola (es: "TAIC851009")
    """
    school_identifier = get_school_identifier()
    school_info = school_identifier.get_school_info(school_code)

    if not school_info:
        raise HTTPException(
            status_code=404,
            detail=f"Scuola con codice {school_code} non trovata"
        )

    return school_info


@router.get("/")
def list_all_schools():
    """
    Lista tutte le scuole nel database.

    Restituisce elenco completo di tutte le scuole caricate.
    """
    school_identifier = get_school_identifier()

    schools = []
    for code, info in school_identifier.schools_db.items():
        schools.append({
            "codice": code,
            **info
        })

    # Sort by comune then nome (handle None values)
    schools.sort(key=lambda x: (x.get("comune") or "", x.get("nome") or ""))

    return {
        "total": len(schools),
        "schools": schools
    }


@router.post("/update-all")
def update_all_schools(
    background_tasks: BackgroundTasks,
    force_online: bool = Query(False, description="Forza ricerca online per tutte le scuole"),
    limit: Optional[int] = Query(None, description="Limita numero scuole da aggiornare (per test)")
):
    """
    Aggiorna tutte le scuole nel database usando LLM.

    Verifica informazioni correnti e aggiorna se necessario.
    L'operazione viene eseguita in background.
    """
    def update_task():
        updater = get_school_updater()
        return updater.update_all_schools(force_online_search=force_online, limit=limit)

    # Esegui in background se non limitato
    if not limit or limit > 10:
        background_tasks.add_task(update_task)
        return {
            "message": "Aggiornamento database scuole avviato in background",
            "status": "running"
        }
    else:
        # Esegui sincrono per test con poche scuole
        stats = update_task()
        return {
            "message": "Aggiornamento completato",
            "status": "completed",
            "stats": stats
        }


@router.post("/update/{school_code}")
def update_single_school(
    school_code: str,
    force_online: bool = Query(False, description="Forza ricerca online")
):
    """
    Aggiorna una singola scuola nel database.

    Verifica e aggiorna informazioni usando LLM e ricerca online.
    """
    updater = get_school_updater()
    schools_db = updater.load_current_db()

    if school_code not in schools_db:
        raise HTTPException(
            status_code=404,
            detail=f"Scuola {school_code} non trovata nel database"
        )

    current_info = schools_db[school_code]
    updated_info = updater.update_school(school_code, current_info, force_online)

    # Salva aggiornamento
    schools_db[school_code] = updated_info
    updater.save_db(schools_db)

    return {
        "message": f"Scuola {school_code} aggiornata",
        "school": updated_info,
        "changes": updated_info.get('changes', [])
    }


@router.post("/add")
def add_new_school(request: SchoolAddRequest):
    """
    Aggiunge una nuova scuola al database.

    Cerca informazioni online usando codice meccanografico.
    """
    updater = get_school_updater()
    school_info = updater.add_new_school(request.school_code, request.force_search)

    if not school_info:
        raise HTTPException(
            status_code=404,
            detail=f"Impossibile trovare informazioni per scuola {request.school_code}"
        )

    return {
        "message": "Scuola aggiunta con successo",
        "school": {
            "codice": request.school_code,
            **school_info
        }
    }


@router.get("/pending/list")
def list_pending_schools():
    """
    Lista tutte le scuole in attesa di approvazione.

    Restituisce le proposte generate automaticamente dal sistema
    che necessitano di revisione da parte dell'utente.
    """
    updater = get_school_updater()
    pending = updater.load_pending_schools()

    schools = []
    for code, info in pending.items():
        schools.append({
            "codice": code,
            **info
        })

    # Ordina per data creazione (più recenti prima)
    schools.sort(key=lambda x: x.get('created_at', ''), reverse=True)

    return {
        "total": len(schools),
        "pending_schools": schools
    }


@router.post("/pending/{school_code}/approve")
def approve_pending_school(school_code: str, request: SchoolApproveRequest):
    """
    Approva una scuola proposta e la aggiunge al database.

    L'utente può modificare i dati proposti prima dell'approvazione.
    Se i campi nella request sono None, vengono usati i valori proposti.
    """
    updater = get_school_updater()
    school_info = updater.approve_pending_school(
        school_code,
        nome=request.nome,
        comune=request.comune,
        indirizzo=request.indirizzo,
        tipo=request.tipo
    )

    if not school_info:
        raise HTTPException(
            status_code=404,
            detail=f"Scuola {school_code} non trovata nelle proposte pendenti"
        )

    # Reload school identifier per aggiornare la cache
    school_identifier = get_school_identifier()
    school_identifier._load_schools_db()

    return {
        "message": f"Scuola {school_code} approvata e aggiunta al database",
        "school": {
            "codice": school_code,
            **school_info
        }
    }


@router.delete("/pending/{school_code}/reject")
def reject_pending_school(school_code: str):
    """
    Rifiuta una proposta di scuola.

    La scuola viene rimossa dalla coda delle proposte
    senza essere aggiunta al database.
    """
    updater = get_school_updater()
    success = updater.reject_pending_school(school_code)

    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Scuola {school_code} non trovata nelle proposte pendenti"
        )

    return {
        "message": f"Proposta per scuola {school_code} rifiutata"
    }


@router.post("/pending/{school_code}/generate")
def generate_school_proposal(
    school_code: str,
    allegati_testo: Optional[dict] = None
):
    """
    Genera una proposta per una nuova scuola.

    Cerca informazioni negli allegati forniti e/o online.
    NON aggiunge la scuola automaticamente - crea solo una proposta.
    """
    school_identifier = get_school_identifier()

    # Verifica se già nel database
    if school_identifier.get_school_info(school_code):
        raise HTTPException(
            status_code=400,
            detail=f"Scuola {school_code} già presente nel database"
        )

    # Genera proposta
    proposal = school_identifier.propose_new_school(school_code, allegati_testo)

    if proposal:
        # Aggiungi alla coda pendenti
        updater = get_school_updater()
        updater.add_pending_school(school_code, proposal)

        return {
            "message": "Proposta generata e aggiunta alla coda di approvazione",
            "proposal": proposal
        }

    return {
        "message": "Impossibile generare proposta - nessuna informazione trovata",
        "proposal": None
    }


@router.delete("/{school_code}")
def remove_school(school_code: str):
    """
    Rimuove una scuola dal database.

    Utile per scuole soppresse o accorpate.
    """
    updater = get_school_updater()
    success = updater.remove_school(school_code)

    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Scuola {school_code} non trovata"
        )

    return {
        "message": f"Scuola {school_code} rimossa dal database"
    }
