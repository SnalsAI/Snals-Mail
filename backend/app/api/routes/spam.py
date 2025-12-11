"""
API Routes per gestione Spam.
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
import re
import logging

from app.database import get_db
from app.models.email import Email
from app.services.email_deletion import get_deletion_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/spam", tags=["spam"])


class SpamPatternSuggestion(BaseModel):
    """Suggerimento per pattern spam"""
    pattern: str
    type: str  # "sender", "subject", "body"
    description: str


class MarkAsSpamResponse(BaseModel):
    """Risposta per mark as spam"""
    message: str
    email_id: int
    suggestions: List[SpamPatternSuggestion]


def _generate_spam_suggestions(email: Email) -> List[dict]:
    """
    Genera suggerimenti per pattern spam basati sull'email.
    Analizza mittente, oggetto e corpo per estrarre pattern utili.
    """
    suggestions = []

    mittente = (email.mittente or "").lower()
    oggetto = (email.oggetto or "").lower()
    corpo = (email.corpo_testo or email.corpo or "").lower()

    # 1. Pattern mittente - dominio
    if '@' in mittente:
        domain_match = re.search(r'@([\w.-]+)', mittente)
        if domain_match:
            domain = domain_match.group(1)
            # Evita domini comuni
            common_domains = ['gmail.com', 'outlook.com', 'istruzione.it', 'pec.istruzione.it', 'yahoo.com']
            if domain not in common_domains:
                suggestions.append({
                    "pattern": f"r'{re.escape(domain)}'",
                    "type": "sender",
                    "description": f"Blocca tutte le email dal dominio {domain}"
                })

    # 2. Pattern mittente - nome specifico
    name_match = re.match(r'^([^<@]+)', mittente.strip())
    if name_match and len(name_match.group(1).strip()) > 3:
        name = name_match.group(1).strip()
        # Solo se contiene parole significative
        words = name.split()
        for word in words:
            if len(word) > 4 and word not in ['info', 'mail', 'email', 'noreply']:
                suggestions.append({
                    "pattern": f"r'\\b{re.escape(word)}\\b'",
                    "type": "sender",
                    "description": f"Blocca email con '{word}' nel mittente"
                })
                break

    # 3. Pattern oggetto - keywords specifiche
    # Cerca parole distintive nell'oggetto
    oggetto_words = re.findall(r'\b[a-z]{5,}\b', oggetto)
    spam_indicative_words = []

    for word in oggetto_words:
        # Evita parole comuni
        if word not in ['della', 'delle', 'degli', 'nella', 'nelle', 'questo', 'questa',
                        'questi', 'queste', 'essere', 'state', 'stati', 'sono', 'siamo',
                        'nostro', 'nostra', 'vostro', 'vostra', 'email', 'posta']:
            spam_indicative_words.append(word)

    for word in spam_indicative_words[:3]:  # Max 3 suggerimenti
        suggestions.append({
            "pattern": f"r'\\b{word}\\b'",
            "type": "subject",
            "description": f"Blocca email con '{word}' nell'oggetto"
        })

    # 4. Pattern corpo - URL o domini sospetti
    urls = re.findall(r'https?://([^\s/]+)', corpo)
    for url in urls[:2]:
        if 'istruzione.it' not in url and 'snals' not in url:
            suggestions.append({
                "pattern": f"r'{re.escape(url)}'",
                "type": "body",
                "description": f"Blocca email con link a {url}"
            })

    # 5. Pattern corpo - unsubscribe/newsletter
    if 'unsubscribe' in corpo or 'cancella iscrizione' in corpo or 'list-manage' in corpo:
        suggestions.append({
            "pattern": "r'unsubscribe|cancella iscrizione|list-manage'",
            "type": "body",
            "description": "Blocca newsletter commerciali"
        })

    return suggestions


@router.post("/{email_id}/mark")
def mark_email_as_spam(
    email_id: int,
    db: Session = Depends(get_db)
) -> MarkAsSpamResponse:
    """
    Marca un'email come spam e genera suggerimenti per migliorare il classificatore.

    Questa API:
    1. Cambia la categoria dell'email a 'spam'
    2. Analizza l'email e genera pattern suggeriti per bloccare email simili
    3. Restituisce i suggerimenti da aggiungere manualmente al classificatore
    """
    email = db.query(Email).filter(Email.id == email_id).first()

    if not email:
        raise HTTPException(status_code=404, detail="Email non trovata")

    # Marca come spam
    old_categoria = email.categoria
    email.categoria = "spam"
    email.categoria_confidence = 1.0  # Manuale = 100% confidence

    db.commit()
    db.refresh(email)

    logger.info(f"🚫 Email {email_id} marcata come spam (era: {old_categoria})")

    # Genera suggerimenti per pattern
    suggestions = _generate_spam_suggestions(email)

    return MarkAsSpamResponse(
        message=f"Email marcata come spam. {len(suggestions)} suggerimenti generati per migliorare il classificatore.",
        email_id=email_id,
        suggestions=[SpamPatternSuggestion(**s) for s in suggestions]
    )


@router.post("/{email_id}/unmark")
def unmark_email_as_spam(
    email_id: int,
    new_categoria: Optional[str] = Query("altro", description="Nuova categoria da assegnare"),
    db: Session = Depends(get_db)
):
    """
    Rimuove un'email dalla categoria spam e la sposta in un'altra categoria.

    L'email torna visibile nelle email normali con la categoria specificata.
    Default: 'altro'
    """
    email = db.query(Email).filter(Email.id == email_id).first()

    if not email:
        raise HTTPException(status_code=404, detail="Email non trovata")

    if email.categoria != "spam":
        raise HTTPException(
            status_code=400,
            detail="Email non è categorizzata come spam"
        )

    # Categorie valide
    valid_categories = ['interpello', 'convocazione_scuola', 'comunicazione_scuola',
                       'sindacale', 'amministrativa', 'urgente', 'altro']

    if new_categoria not in valid_categories:
        new_categoria = 'altro'

    # Aggiorna categoria
    email.categoria = new_categoria
    email.categoria_confidence = 0.5  # Confidence media perché classificazione manuale

    db.commit()
    db.refresh(email)

    logger.info(f"✅ Email {email_id} rimossa da spam -> {new_categoria}")

    return {
        "message": f"Email rimossa da spam e spostata in '{new_categoria}'",
        "email_id": email_id,
        "new_categoria": new_categoria
    }


@router.get("/")
def list_spam_emails(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Lista email categorizzate come spam (non ancora eliminate dal server).
    """
    query = db.query(Email).filter(
        Email.categoria == "spam",
        Email.eliminata_dal_server == False
    )

    total = query.count()

    emails = query.order_by(desc(Email.data_ricezione)).offset(skip).limit(limit).all()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "emails": [email.to_dict() for email in emails]
    }


@router.get("/deleted")
def list_deleted_spam_emails(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Lista email spam eliminate dal server (storico).
    """
    query = db.query(Email).filter(
        Email.categoria == "spam",
        Email.eliminata_dal_server == True
    )

    total = query.count()

    emails = query.order_by(desc(Email.data_eliminazione)).offset(skip).limit(limit).all()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "emails": [{
            **email.to_dict(),
            "data_eliminazione": email.data_eliminazione.isoformat() if email.data_eliminazione else None
        } for email in emails]
    }


@router.get("/stats")
def get_spam_stats(db: Session = Depends(get_db)):
    """
    Statistiche spam.
    """
    total_spam = db.query(Email).filter(
        Email.categoria == "spam",
        Email.eliminata_dal_server == False
    ).count()

    total_deleted = db.query(Email).filter(
        Email.categoria == "spam",
        Email.eliminata_dal_server == True
    ).count()

    return {
        "total_spam": total_spam,
        "total_deleted": total_deleted
    }


# IMPORTANTE: La route bulk DEVE venire PRIMA della route con {email_id}
# altrimenti FastAPI tenta di parsare "bulk" come integer
@router.delete("/bulk/from-server")
def delete_all_spam_from_server(
    confirm: bool = Query(False, description="Conferma eliminazione"),
    db: Session = Depends(get_db)
):
    """
    Elimina TUTTE le email spam dal server IMAP e marca come eliminate (soft-delete).
    Le email rimangono nel database per lo storico.
    """
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Devi confermare l'eliminazione passando confirm=true"
        )

    # Recupera tutte le email spam non ancora eliminate
    spam_emails = db.query(Email).filter(
        Email.categoria == "spam",
        Email.eliminata_dal_server == False
    ).all()

    if not spam_emails:
        return {
            "message": "Nessuna email spam da eliminare",
            "total": 0,
            "deleted_from_server": 0,
            "marked_deleted": 0
        }

    # Elimina dal server
    deletion_service = get_deletion_service(db)
    results = deletion_service.delete_multiple_from_server(spam_emails)

    # Marca come eliminate (soft-delete)
    marked_count = 0
    now = datetime.now()
    for email in spam_emails:
        email.eliminata_dal_server = True
        email.data_eliminazione = now
        marked_count += 1

    db.commit()

    return {
        "message": f"{marked_count} email spam eliminate dal server",
        "total": results['total'],
        "deleted_from_server": results['success'],
        "marked_deleted": marked_count,
        "server_errors": results['errors']
    }


@router.delete("/{email_id}/from-server")
def delete_spam_from_server(
    email_id: int,
    db: Session = Depends(get_db)
):
    """
    Elimina email spam dal server IMAP e marca come eliminata nel database (soft-delete).
    L'email rimane nel database per lo storico.
    """
    email = db.query(Email).filter(Email.id == email_id).first()

    if not email:
        raise HTTPException(status_code=404, detail="Email non trovata")

    if email.categoria != "spam":
        raise HTTPException(
            status_code=400,
            detail="Email non è categorizzata come spam"
        )

    if email.eliminata_dal_server:
        raise HTTPException(
            status_code=400,
            detail="Email già eliminata dal server"
        )

    # Elimina dal server
    deletion_service = get_deletion_service(db)
    server_deleted = deletion_service.delete_from_server(email)

    # Marca come eliminata (soft-delete) invece di cancellare
    email.eliminata_dal_server = True
    email.data_eliminazione = datetime.now()
    db.commit()

    return {
        "message": "Email eliminata dal server",
        "deleted_from_server": server_deleted,
        "email_id": email_id
    }


@router.delete("/{email_id}/local-only")
def delete_spam_local_only(
    email_id: int,
    db: Session = Depends(get_db)
):
    """
    Elimina email spam solo dal database locale (non dal server).
    """
    email = db.query(Email).filter(Email.id == email_id).first()

    if not email:
        raise HTTPException(status_code=404, detail="Email non trovata")

    if email.categoria != "spam":
        raise HTTPException(
            status_code=400,
            detail="Email non è categorizzata come spam"
        )

    db.delete(email)
    db.commit()

    return {
        "message": "Email eliminata dal database locale",
        "email_id": email_id
    }
