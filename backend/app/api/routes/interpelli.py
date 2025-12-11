"""
API Routes per gestione Interpelli
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_, and_, func
from datetime import datetime, date

from app.database import get_db
from app.models.interpello import Interpello, StatoInterpello
from app.models.email import Email
from app.services.interpello_parser import InterpelloParser

router = APIRouter(prefix="/interpelli", tags=["interpelli"])


@router.get("/")
def list_interpelli(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    classe_concorso: Optional[str] = None,
    provincia: Optional[str] = None,
    stato: Optional[str] = None,
    solo_aperti: bool = False,
    db: Session = Depends(get_db)
):
    """
    Lista interpelli con filtri e paginazione.

    - **skip**: Numero interpelli da saltare
    - **limit**: Numero massimo interpelli da restituire
    - **classe_concorso**: Filtra per classe di concorso (es. "A042")
    - **provincia**: Filtra per provincia
    - **stato**: Filtra per stato (aperto, chiuso, scaduto)
    - **solo_aperti**: Se True, mostra solo interpelli aperti non scaduti
    """
    query = db.query(Interpello)

    # Filtri
    if classe_concorso:
        query = query.filter(Interpello.classe_concorso.ilike(f"%{classe_concorso}%"))

    if provincia:
        query = query.filter(Interpello.provincia.ilike(f"%{provincia}%"))

    if stato:
        query = query.filter(Interpello.stato == stato)

    if solo_aperti:
        oggi = datetime.utcnow()
        query = query.filter(
            and_(
                Interpello.stato == "aperto",
                or_(
                    Interpello.data_scadenza.is_(None),
                    Interpello.data_scadenza > oggi
                )
            )
        )

    total = query.count()
    interpelli = query.order_by(desc(Interpello.data_pubblicazione)).offset(skip).limit(limit).all()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "interpelli": [format_interpello(i) for i in interpelli]
    }


@router.get("/statistiche")
def get_statistiche(db: Session = Depends(get_db)):
    """Statistiche sugli interpelli"""
    oggi = datetime.utcnow()

    totali = db.query(Interpello).count()
    aperti = db.query(Interpello).filter(
        and_(
            Interpello.stato == "aperto",
            or_(
                Interpello.data_scadenza.is_(None),
                Interpello.data_scadenza > oggi
            )
        )
    ).count()

    # Interpelli per classe di concorso (top 10)
    per_classe = db.query(
        Interpello.classe_concorso,
        func.count(Interpello.id).label('count')
    ).group_by(
        Interpello.classe_concorso
    ).order_by(
        desc('count')
    ).limit(10).all()

    # Interpelli per provincia (top 10)
    per_provincia = db.query(
        Interpello.provincia,
        func.count(Interpello.id).label('count')
    ).filter(
        Interpello.provincia.isnot(None)
    ).group_by(
        Interpello.provincia
    ).order_by(
        desc('count')
    ).limit(10).all()

    return {
        "totali": totali,
        "aperti": aperti,
        "chiusi": totali - aperti,
        "per_classe_concorso": [{"classe": c, "count": cnt} for c, cnt in per_classe],
        "per_provincia": [{"provincia": p, "count": cnt} for p, cnt in per_provincia]
    }


@router.get("/per-classe")
def list_interpelli_per_classe(
    solo_aperti: bool = False,
    db: Session = Depends(get_db)
):
    """
    Raggruppa interpelli per classe di concorso.

    Mostra per ogni classe di concorso:
    - Numero totale di posizioni disponibili
    - Province dove ci sono posizioni
    - Lista degli interpelli

    Ideale per vedere rapidamente dove ci sono opportunità per una specifica classe.
    """
    query = db.query(Interpello)

    # Filtra solo aperti se richiesto
    if solo_aperti:
        oggi = datetime.utcnow()
        query = query.filter(
            and_(
                Interpello.stato == "aperto",
                or_(
                    Interpello.data_scadenza.is_(None),
                    Interpello.data_scadenza > oggi
                )
            )
        )

    # Recupera tutti gli interpelli filtrati
    interpelli = query.order_by(desc(Interpello.data_pubblicazione)).all()

    # Raggruppa per classe di concorso
    per_classe = {}
    for interp in interpelli:
        classe = interp.classe_concorso or "NON_SPECIFICATA"

        if classe not in per_classe:
            per_classe[classe] = {
                "classe_concorso": None if classe == "NON_SPECIFICATA" else classe,
                "totale_interpelli": 0,
                "totale_posti": 0,
                "province": set(),
                "interpelli": []
            }

        per_classe[classe]["totale_interpelli"] += 1
        per_classe[classe]["totale_posti"] += (interp.numero_posti or 0)

        if interp.provincia:
            per_classe[classe]["province"].add(interp.provincia)

        per_classe[classe]["interpelli"].append(format_interpello(interp))

    # Converti set a lista e ordina per numero di interpelli
    result = []
    for classe, dati in per_classe.items():
        dati["province"] = sorted(list(dati["province"]))
        result.append(dati)

    # Ordina per numero di interpelli (decrescente)
    result = sorted(result, key=lambda x: x["totale_interpelli"], reverse=True)

    return {
        "total_classi": len(result),
        "per_classe": result
    }


@router.get("/{interpello_id}")
def get_interpello(interpello_id: int, db: Session = Depends(get_db)):
    """Recupera dettagli interpello singolo"""
    interpello = db.query(Interpello).filter(Interpello.id == interpello_id).first()

    if not interpello:
        raise HTTPException(status_code=404, detail="Interpello non trovato")

    return format_interpello(interpello, include_text=True)


@router.post("/parse/{email_id}")
def parse_interpello_from_email(email_id: int, db: Session = Depends(get_db)):
    """
    Schedula parsing interpello in background tramite Celery.

    Il parsing viene eseguito con timeout lunghi (5 minuti) permettendo a Ollama
    di analizzare il documento con calma senza bloccare la request HTTP.

    - **email_id**: ID dell'email da analizzare

    Returns:
        Informazioni sul task schedulato
    """
    # Recupera email
    email = db.query(Email).filter(Email.id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email non trovata")

    # Importa e schedula task Celery
    from app.tasks.interpello_tasks import parse_interpello

    task = parse_interpello.delay(
        email_id=email_id,
        azione_id=None  # Nessuna azione associata per chiamate API dirette
    )

    return {
        "success": True,
        "message": "Parsing interpello schedulato in background",
        "task_id": task.id,
        "email_id": email_id,
        "status": "scheduled",
        "note": "Il parsing verrà completato dal worker Celery con timeout di 5 minuti. Controlla lo stato del task o ricarica la pagina tra qualche istante."
    }


@router.put("/{interpello_id}")
def update_interpello(
    interpello_id: int,
    verificato: Optional[bool] = None,
    stato: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Aggiorna stato interpello manualmente"""
    interpello = db.query(Interpello).filter(Interpello.id == interpello_id).first()
    if not interpello:
        raise HTTPException(status_code=404, detail="Interpello non trovato")

    if verificato is not None:
        interpello.verificato = verificato

    if stato is not None:
        if stato not in ["aperto", "chiuso", "scaduto"]:
            raise HTTPException(status_code=400, detail="Stato non valido")
        interpello.stato = stato

    interpello.data_aggiornamento = datetime.utcnow()
    db.commit()
    db.refresh(interpello)

    return {"success": True, "interpello": format_interpello(interpello)}


@router.delete("/{interpello_id}")
def delete_interpello(interpello_id: int, db: Session = Depends(get_db)):
    """Elimina interpello"""
    interpello = db.query(Interpello).filter(Interpello.id == interpello_id).first()
    if not interpello:
        raise HTTPException(status_code=404, detail="Interpello non trovato")

    db.delete(interpello)
    db.commit()

    return {"success": True}


def format_interpello(interpello: Interpello, include_text: bool = False) -> dict:
    """Formatta interpello per risposta API"""
    data = {
        "id": interpello.id,
        "email_id": interpello.email_id,
        "classe_concorso": interpello.classe_concorso,
        "numero_posti": interpello.numero_posti,
        "ore_settimanali": interpello.ore_settimanali,
        "data_scadenza": interpello.data_scadenza.isoformat() if interpello.data_scadenza else None,
        "data_inizio_servizio": interpello.data_inizio_servizio.isoformat() if interpello.data_inizio_servizio else None,
        "data_fine_contratto": interpello.data_fine_contratto.isoformat() if interpello.data_fine_contratto else None,
        "provincia": interpello.provincia,
        "citta": interpello.citta,
        "istituto": interpello.istituto,
        "indirizzo": interpello.indirizzo,
        "tipo_contratto": interpello.tipo_contratto,
        "orario_giorni": interpello.orario_giorni,
        "link_candidatura": interpello.link_candidatura,
        "link_titoli_accesso": interpello.link_titoli_accesso,
        "email_contatto": interpello.email_contatto,
        "telefono_contatto": interpello.telefono_contatto,
        "referente_contatto": interpello.referente_contatto,
        "modalita_candidatura": interpello.modalita_candidatura,
        "stato": interpello.stato,
        "verificato": interpello.verificato,
        "data_pubblicazione": interpello.data_pubblicazione.isoformat() if interpello.data_pubblicazione else None,
        "data_creazione": interpello.data_creazione.isoformat() if interpello.data_creazione else None,
        "data_aggiornamento": interpello.data_aggiornamento.isoformat() if interpello.data_aggiornamento else None,
        "metadata_estrazione": interpello.metadata_estrazione  # Sempre incluso per validation indicators
    }

    if include_text:
        data["testo_completo"] = interpello.testo_completo

    return data
