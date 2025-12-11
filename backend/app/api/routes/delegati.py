"""
API Routes per gestione delegati e zone per contrattazioni
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models.delegato import Delegato, Zona

router = APIRouter(prefix="/delegati", tags=["delegati"])


# ============ SCHEMAS ============

class DelegatoCreate(BaseModel):
    """Schema per creazione delegato"""
    nome: str
    cognome: str
    email: str
    telefono: Optional[str] = None
    note: Optional[str] = None
    zone_ids: List[int] = []


class DelegatoUpdate(BaseModel):
    """Schema per aggiornamento delegato"""
    nome: Optional[str] = None
    cognome: Optional[str] = None
    email: Optional[str] = None
    telefono: Optional[str] = None
    attivo: Optional[bool] = None
    note: Optional[str] = None
    zone_ids: Optional[List[int]] = None


class ZonaCreate(BaseModel):
    """Schema per creazione zona"""
    nome: str
    descrizione: Optional[str] = None
    comuni: List[str] = []


class ZonaUpdate(BaseModel):
    """Schema per aggiornamento zona"""
    nome: Optional[str] = None
    descrizione: Optional[str] = None
    attiva: Optional[bool] = None
    comuni: Optional[List[str]] = None


# ============ ZONE ENDPOINTS ============

@router.get("/zone/")
def list_zone(
    attive_solo: bool = True,
    db: Session = Depends(get_db)
):
    """Lista tutte le zone"""
    query = db.query(Zona)

    if attive_solo:
        query = query.filter(Zona.attiva == True)

    zone = query.all()

    return {
        'total': len(zone),
        'zone': [z.to_dict() for z in zone]
    }


@router.get("/zone/{zona_id}")
def get_zona(zona_id: int, db: Session = Depends(get_db)):
    """Recupera dettagli zona singola"""
    zona = db.query(Zona).filter(Zona.id == zona_id).first()

    if not zona:
        raise HTTPException(status_code=404, detail="Zona non trovata")

    return zona.to_dict()


@router.post("/zone/")
def create_zona(data: ZonaCreate, db: Session = Depends(get_db)):
    """Crea nuova zona"""
    # Verifica nome univoco
    existing = db.query(Zona).filter(Zona.nome == data.nome).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Zona '{data.nome}' già esistente")

    zona = Zona(
        nome=data.nome,
        descrizione=data.descrizione,
        attiva=True
    )
    zona.set_comuni(data.comuni)

    db.add(zona)
    db.commit()
    db.refresh(zona)

    return {
        'message': 'Zona creata',
        'zona': zona.to_dict()
    }


@router.put("/zone/{zona_id}")
def update_zona(zona_id: int, data: ZonaUpdate, db: Session = Depends(get_db)):
    """Aggiorna zona"""
    zona = db.query(Zona).filter(Zona.id == zona_id).first()

    if not zona:
        raise HTTPException(status_code=404, detail="Zona non trovata")

    if data.nome is not None:
        # Verifica nome univoco
        existing = db.query(Zona).filter(Zona.nome == data.nome, Zona.id != zona_id).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Zona '{data.nome}' già esistente")
        zona.nome = data.nome

    if data.descrizione is not None:
        zona.descrizione = data.descrizione

    if data.attiva is not None:
        zona.attiva = data.attiva

    if data.comuni is not None:
        zona.set_comuni(data.comuni)

    db.commit()
    db.refresh(zona)

    return {
        'message': 'Zona aggiornata',
        'zona': zona.to_dict()
    }


@router.delete("/zone/{zona_id}")
def delete_zona(zona_id: int, db: Session = Depends(get_db)):
    """Elimina zona"""
    zona = db.query(Zona).filter(Zona.id == zona_id).first()

    if not zona:
        raise HTTPException(status_code=404, detail="Zona non trovata")

    db.delete(zona)
    db.commit()

    return {'message': 'Zona eliminata'}


@router.get("/zone/{zona_id}/delegati")
def get_delegati_by_zona(zona_id: int, db: Session = Depends(get_db)):
    """Recupera tutti i delegati di una zona"""
    zona = db.query(Zona).filter(Zona.id == zona_id).first()

    if not zona:
        raise HTTPException(status_code=404, detail="Zona non trovata")

    return {
        'zona': zona.nome,
        'delegati': [d.to_dict() for d in zona.delegati]
    }


# ============ DELEGATI ENDPOINTS ============

@router.get("/")
def list_delegati(
    attivi_solo: bool = True,
    zona_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Lista tutti i delegati"""
    query = db.query(Delegato)

    if attivi_solo:
        query = query.filter(Delegato.attivo == True)

    delegati = query.all()

    # Filtra per zona se specificato
    if zona_id:
        delegati = [d for d in delegati if any(z.id == zona_id for z in d.zone)]

    return {
        'total': len(delegati),
        'delegati': [d.to_dict() for d in delegati]
    }


@router.get("/{delegato_id}")
def get_delegato(delegato_id: int, db: Session = Depends(get_db)):
    """Recupera dettagli delegato singolo"""
    delegato = db.query(Delegato).filter(Delegato.id == delegato_id).first()

    if not delegato:
        raise HTTPException(status_code=404, detail="Delegato non trovato")

    return delegato.to_dict()


@router.post("/")
def create_delegato(data: DelegatoCreate, db: Session = Depends(get_db)):
    """Crea nuovo delegato"""
    delegato = Delegato(
        nome=data.nome,
        cognome=data.cognome,
        email=data.email,
        telefono=data.telefono,
        note=data.note,
        attivo=True
    )

    # Associa zone
    if data.zone_ids:
        zone = db.query(Zona).filter(Zona.id.in_(data.zone_ids)).all()
        delegato.zone = zone

    db.add(delegato)
    db.commit()
    db.refresh(delegato)

    return {
        'message': 'Delegato creato',
        'delegato': delegato.to_dict()
    }


@router.put("/{delegato_id}")
def update_delegato(delegato_id: int, data: DelegatoUpdate, db: Session = Depends(get_db)):
    """Aggiorna delegato"""
    delegato = db.query(Delegato).filter(Delegato.id == delegato_id).first()

    if not delegato:
        raise HTTPException(status_code=404, detail="Delegato non trovato")

    if data.nome is not None:
        delegato.nome = data.nome

    if data.cognome is not None:
        delegato.cognome = data.cognome

    if data.email is not None:
        delegato.email = data.email

    if data.telefono is not None:
        delegato.telefono = data.telefono

    if data.attivo is not None:
        delegato.attivo = data.attivo

    if data.note is not None:
        delegato.note = data.note

    if data.zone_ids is not None:
        zone = db.query(Zona).filter(Zona.id.in_(data.zone_ids)).all()
        delegato.zone = zone

    db.commit()
    db.refresh(delegato)

    return {
        'message': 'Delegato aggiornato',
        'delegato': delegato.to_dict()
    }


@router.delete("/{delegato_id}")
def delete_delegato(delegato_id: int, db: Session = Depends(get_db)):
    """Elimina delegato"""
    delegato = db.query(Delegato).filter(Delegato.id == delegato_id).first()

    if not delegato:
        raise HTTPException(status_code=404, detail="Delegato non trovato")

    db.delete(delegato)
    db.commit()

    return {'message': 'Delegato eliminato'}


# ============ UTILITY ENDPOINTS ============

@router.get("/zone/by-school/{school_code}")
def get_zona_by_school(school_code: str, db: Session = Depends(get_db)):
    """
    Trova la zona di una scuola dato il suo codice meccanografico.

    Identifica prima la scuola, prende il suo comune, e trova la zona che include quel comune.
    """
    from app.services.school_identifier import get_school_identifier

    # Identifica la scuola dal codice
    school_identifier = get_school_identifier()
    school_info = school_identifier.get_school_info(school_code)

    if not school_info:
        return {
            'found': False,
            'message': f'Scuola {school_code} non trovata nel database'
        }

    comune = school_info.get('comune', '').upper()
    if not comune:
        return {
            'found': False,
            'message': f'Comune non disponibile per scuola {school_code}'
        }

    # Cerca la zona che include questo comune
    zone = db.query(Zona).filter(Zona.attiva == True).all()

    for zona in zone:
        if comune in [c.upper() for c in zona.get_comuni()]:
            return {
                'found': True,
                'zona': zona.to_dict(),
                'delegati': [d.to_dict() for d in zona.delegati if d.attivo],
                'comune': comune,
                'scuola': school_info
            }

    return {
        'found': False,
        'message': f'Nessuna zona trovata per il comune {comune}',
        'comune': comune,
        'scuola': school_info
    }
