"""
API routes per gestione classi di concorso
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List

from app.database import get_db
from app.data.classi_concorso import (
    CLASSI_CONCORSO,
    normalizza_classe_concorso,
    get_info_classe,
    get_esempi_classi
)
from app.models.interpello import Interpello

router = APIRouter(prefix="/classi-concorso", tags=["Classi di Concorso"])


@router.get("/")
def list_classi_concorso(
    grado: Optional[str] = Query(None, description="Filtra per grado (I GRADO, II GRADO)"),
    search: Optional[str] = Query(None, description="Cerca per codice o denominazione"),
    db: Session = Depends(get_db)
):
    """
    Lista tutte le classi di concorso con statistiche di utilizzo.
    """
    # Conta interpelli per classe
    interpelli_stats = {}
    query = db.query(
        Interpello.classe_concorso,
        func.count(Interpello.id).label('count')
    ).filter(
        Interpello.classe_concorso.isnot(None)
    ).group_by(Interpello.classe_concorso).all()

    for classe, count in query:
        interpelli_stats[classe] = count

    # Prepara lista classi
    result = []
    for codice_uff, (codice_sidi, grado_classe, denominazione) in CLASSI_CONCORSO.items():
        # Filtra per grado se richiesto
        if grado and grado.upper() not in grado_classe:
            continue

        # Filtra per search se richiesto
        if search:
            search_term = search.lower()
            if (search_term not in codice_uff.lower() and
                search_term not in codice_sidi.lower() and
                search_term not in denominazione.lower()):
                continue

        result.append({
            'codice_ufficiale': codice_uff,
            'codice_sidi': codice_sidi,
            'grado': grado_classe,
            'denominazione': denominazione,
            'interpelli_count': interpelli_stats.get(codice_uff, 0)
        })

    # Ordina per numero di interpelli (decrescente), poi per codice
    result.sort(key=lambda x: (-x['interpelli_count'], x['codice_ufficiale']))

    return {
        'total': len(result),
        'classi': result
    }


@router.get("/stats")
def get_classi_stats(db: Session = Depends(get_db)):
    """
    Statistiche generali sulle classi di concorso.
    """
    # Conta interpelli per classe
    interpelli_per_classe = db.query(
        Interpello.classe_concorso,
        func.count(Interpello.id).label('count')
    ).filter(
        Interpello.classe_concorso.isnot(None)
    ).group_by(Interpello.classe_concorso).all()

    # Conta interpelli senza classe
    interpelli_senza_classe = db.query(func.count(Interpello.id)).filter(
        Interpello.classe_concorso.is_(None)
    ).scalar()

    # Trova classi più richieste
    top_classi = sorted(interpelli_per_classe, key=lambda x: x[1], reverse=True)[:10]
    top_classi_list = []
    for classe, count in top_classi:
        info = get_info_classe(classe)
        top_classi_list.append({
            'classe': classe,
            'interpelli_count': count,
            'info': info
        })

    # Conta per grado
    per_grado = {'I GRADO': 0, 'II GRADO': 0, 'NON_VALIDE': 0}
    for classe, count in interpelli_per_classe:
        info = get_info_classe(classe)
        if info:
            per_grado[info['grado']] = per_grado.get(info['grado'], 0) + count
        else:
            per_grado['NON_VALIDE'] += count

    return {
        'totale_classi_database': len(CLASSI_CONCORSO),
        'classi_con_interpelli': len(interpelli_per_classe),
        'interpelli_senza_classe': interpelli_senza_classe,
        'top_classi': top_classi_list,
        'per_grado': per_grado
    }


@router.get("/validate/{codice}")
def validate_classe(codice: str):
    """
    Valida un codice classe di concorso.
    """
    normalizzato = normalizza_classe_concorso(codice)

    if not normalizzato:
        return {
            'valido': False,
            'codice_raw': codice,
            'codice_normalizzato': None,
            'info': None,
            'messaggio': f"Codice '{codice}' non riconosciuto nel database ufficiale"
        }

    info = get_info_classe(normalizzato)

    return {
        'valido': True,
        'codice_raw': codice,
        'codice_normalizzato': normalizzato,
        'info': info,
        'messaggio': 'Codice valido' if codice == normalizzato else f"Codice normalizzato da '{codice}' a '{normalizzato}'"
    }


@router.get("/{codice}")
def get_classe_detail(codice: str, db: Session = Depends(get_db)):
    """
    Dettagli completi di una classe di concorso.
    """
    # Normalizza il codice
    codice_norm = normalizza_classe_concorso(codice)

    if not codice_norm:
        return {
            'trovato': False,
            'codice': codice,
            'messaggio': 'Classe di concorso non trovata'
        }

    info = get_info_classe(codice_norm)

    # Conta interpelli per questa classe
    interpelli_count = db.query(func.count(Interpello.id)).filter(
        Interpello.classe_concorso == codice_norm
    ).scalar()

    # Ultimi interpelli per questa classe
    ultimi_interpelli = db.query(Interpello).filter(
        Interpello.classe_concorso == codice_norm
    ).order_by(Interpello.data_pubblicazione.desc()).limit(5).all()

    return {
        'trovato': True,
        'codice': codice,
        'info': info,
        'interpelli_count': interpelli_count,
        'ultimi_interpelli': [
            {
                'id': i.id,
                'email_id': i.email_id,
                'provincia': i.provincia,
                'istituto': i.istituto,
                'data_pubblicazione': i.data_pubblicazione.isoformat() if i.data_pubblicazione else None,
                'stato': i.stato
            }
            for i in ultimi_interpelli
        ]
    }


@router.get("/esempi/llm")
def get_esempi_per_llm():
    """
    Restituisce esempi di classi per il prompt LLM.
    """
    return {
        'esempi': get_esempi_classi()
    }
