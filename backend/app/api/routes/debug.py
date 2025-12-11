"""
API Routes per Debug e Monitoring
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_

from app.database import get_db
from app.models.email import Email
from app.models.azione import Azione
from app.models.interpello import Interpello

router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/emails")
def list_debug_emails(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    categoria: Optional[str] = None,
    con_azioni: Optional[bool] = None,
    con_interpelli: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """
    Lista email con informazioni di debug complete.

    - **skip**: Numero email da saltare (paginazione)
    - **limit**: Numero massimo email da restituire
    - **categoria**: Filtra per categoria
    - **con_azioni**: Se True, solo email con azioni
    - **con_interpelli**: Se True, solo email con interpelli
    """
    query = db.query(Email)

    # Filtri
    if categoria:
        query = query.filter(Email.categoria == categoria)

    if con_azioni:
        query = query.join(Azione).filter(Azione.email_id == Email.id)

    if con_interpelli:
        query = query.join(Interpello).filter(Interpello.email_id == Email.id)

    total = query.count()
    emails = query.order_by(desc(Email.id)).offset(skip).limit(limit).all()

    # Costruisci response con dettagli debug
    results = []
    for email in emails:
        # Recupera azioni
        azioni = db.query(Azione).filter(Azione.email_id == email.id).order_by(Azione.id).all()

        # Recupera interpello (se esiste)
        interpello = db.query(Interpello).filter(Interpello.email_id == email.id).first()

        email_debug = {
            "id": email.id,
            "oggetto": email.oggetto[:100] + "..." if len(email.oggetto) > 100 else email.oggetto,
            "mittente": email.mittente,
            "data_ricezione": email.data_ricezione.isoformat() if email.data_ricezione else None,
            "stato": email.stato.value,
            "categoria": email.get_categoria_value(),
            "sottocategoria": email.sottocategoria,
            "categoria_confidence": email.categoria_confidence,

            # Azioni eseguite
            "azioni": [
                {
                    "id": a.id,
                    "tipo": a.tipo.value,
                    "stato": a.stato.value,
                    "dettagli": a.dettagli,
                    "risultato": a.risultato,
                    "errore": a.errore,
                    "created_at": a.created_at.isoformat() if hasattr(a, 'created_at') and a.created_at else None
                }
                for a in azioni
            ],

            # Interpello (se esiste)
            "interpello": None
        }

        if interpello:
            email_debug["interpello"] = {
                "id": interpello.id,
                "classe_concorso": interpello.classe_concorso,
                "numero_posti": interpello.numero_posti,
                "ore_settimanali": interpello.ore_settimanali,
                "data_scadenza": interpello.data_scadenza.isoformat() if interpello.data_scadenza else None,
                "provincia": interpello.provincia,
                "citta": interpello.citta,
                "istituto": interpello.istituto,
                "data_fine_contratto": interpello.data_fine_contratto.isoformat() if interpello.data_fine_contratto else None,
                "metadata_estrazione": interpello.metadata_estrazione,  # Chi ha estratto
                "stato": interpello.stato,
                "verificato": interpello.verificato
            }

        results.append(email_debug)

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "emails": results
    }


@router.get("/emails/{email_id}")
def get_debug_email(email_id: int, db: Session = Depends(get_db)):
    """
    Dettagli completi di debug per una singola email.

    Include:
    - Metadati email
    - Tutte le azioni con dettagli completi
    - Interpello con metadata estrazione
    - Logs di processing
    """
    email = db.query(Email).filter(Email.id == email_id).first()

    if not email:
        raise HTTPException(status_code=404, detail="Email non trovata")

    # Recupera azioni con tutti i dettagli
    azioni = db.query(Azione).filter(Azione.email_id == email_id).order_by(Azione.id).all()

    # Recupera interpello
    interpello = db.query(Interpello).filter(Interpello.email_id == email_id).first()

    return {
        "email": {
            "id": email.id,
            "message_id": email.message_id,
            "oggetto": email.oggetto,
            "mittente": email.mittente,
            "destinatario": email.destinatario,
            "corpo_testo": email.corpo_testo[:500] if email.corpo_testo else None,  # Primi 500 caratteri
            "data_ricezione": email.data_ricezione.isoformat() if email.data_ricezione else None,
            "stato": email.stato.value,
            "categoria": email.get_categoria_value(),
            "sottocategoria": email.sottocategoria,
            "categoria_confidence": email.categoria_confidence,
            "categoria_motivazione": email.categoria_motivazione,
            "priorita": email.priorita,
            "note": email.note,
            "created_at": email.created_at.isoformat() if email.created_at else None,
            "updated_at": email.updated_at.isoformat() if email.updated_at else None
        },

        "azioni": [
            {
                "id": a.id,
                "tipo": a.tipo.value,
                "stato": a.stato.value,
                "dettagli": a.dettagli,
                "risultato": a.risultato,
                "errore": a.errore,
                "created_at": a.created_at.isoformat() if hasattr(a, 'created_at') and a.created_at else None
            }
            for a in azioni
        ],

        "interpello": {
            "id": interpello.id,
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
            "testo_completo": interpello.testo_completo[:1000] if interpello.testo_completo else None,  # Primi 1000 char
            "metadata_estrazione": interpello.metadata_estrazione,
            "stato": interpello.stato,
            "verificato": interpello.verificato,
            "data_creazione": interpello.data_creazione.isoformat() if interpello.data_creazione else None,
            "data_aggiornamento": interpello.data_aggiornamento.isoformat() if interpello.data_aggiornamento else None
        } if interpello else None
    }


@router.get("/interpelli")
def list_debug_interpelli(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    incompleti: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """
    Lista interpelli con informazioni di debug.

    - **incompleti**: Se True, mostra solo interpelli con dati mancanti
    """
    query = db.query(Interpello).join(Email)

    # Filtra interpelli incompleti (campi chiave mancanti)
    if incompleti:
        query = query.filter(
            or_(
                Interpello.classe_concorso.is_(None),
                Interpello.data_scadenza.is_(None),
                Interpello.provincia.is_(None),
                Interpello.ore_settimanali.is_(None)
            )
        )

    total = query.count()
    interpelli = query.order_by(desc(Interpello.id)).offset(skip).limit(limit).all()

    results = []
    for interp in interpelli:
        email = db.query(Email).filter(Email.id == interp.email_id).first()

        # Calcola completezza
        campi_richiesti = ['classe_concorso', 'ore_settimanali', 'provincia', 'data_scadenza']
        campi_presenti = sum(1 for field in campi_richiesti if getattr(interp, field) is not None)
        completezza = (campi_presenti / len(campi_richiesti)) * 100

        results.append({
            "interpello_id": interp.id,
            "email_id": interp.email_id,
            "email_oggetto": email.oggetto[:80] + "..." if len(email.oggetto) > 80 else email.oggetto,
            "classe_concorso": interp.classe_concorso,
            "ore_settimanali": interp.ore_settimanali,
            "provincia": interp.provincia,
            "data_scadenza": interp.data_scadenza.isoformat() if interp.data_scadenza else None,
            "istituto": interp.istituto,
            "metadata_estrazione": interp.metadata_estrazione,
            "completezza_pct": round(completezza, 1),
            "verificato": interp.verificato
        })

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "interpelli": results
    }


@router.post("/interpelli/{interpello_id}/reparse")
def reparse_interpello(
    interpello_id: int,
    strategy: str = Query("smart", regex="^(regex|smart|ollama|openai)$"),
    db: Session = Depends(get_db)
):
    """
    Ri-esegue il parsing di un interpello con una strategia specifica.

    - **strategy**: regex, smart, ollama, openai
    """
    interpello = db.query(Interpello).filter(Interpello.id == interpello_id).first()

    if not interpello:
        raise HTTPException(status_code=404, detail="Interpello non trovato")

    email = db.query(Email).filter(Email.id == interpello.email_id).first()

    if not email:
        raise HTTPException(status_code=404, detail="Email associata non trovata")

    # Riesegui parsing
    from app.services.interpello_parser import InterpelloParser

    try:
        parser = InterpelloParser(strategy=strategy, db_session=db)

        # Estrai testo completo dall'interpello esistente se disponibile
        corpo_completo = interpello.testo_completo if interpello.testo_completo else (email.corpo_testo or "")

        # Use extract_from_email() method
        dati_estratti = parser.extract_from_email(
            corpo=corpo_completo,
            allegati_path=None,
            allegati_nomi=None,
            allegati_testo=None,
            oggetto=email.oggetto  # Passa oggetto per estrazione scadenza
        )

        if dati_estratti:
            # Aggiorna interpello esistente
            for key, value in dati_estratti.items():
                if hasattr(interpello, key) and value is not None:
                    setattr(interpello, key, value)

            # Aggiorna metadata
            from datetime import datetime
            if not interpello.metadata_estrazione:
                interpello.metadata_estrazione = {}
            interpello.metadata_estrazione['reparse_strategy'] = strategy
            interpello.metadata_estrazione['reparse_at'] = datetime.now().isoformat()

            db.commit()
            db.refresh(interpello)

            return {
                "status": "success",
                "message": f"Interpello {interpello_id} ri-parsato con strategia {strategy}",
                "interpello_id": interpello.id,
                "dati_estratti": dati_estratti,
                "metadata": interpello.metadata_estrazione
            }
        else:
            return {
                "status": "warning",
                "message": f"Parsing con strategia {strategy} non ha estratto dati",
                "interpello_id": interpello.id
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore durante re-parsing: {str(e)}")
