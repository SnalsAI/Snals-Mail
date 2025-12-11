"""
Celery Tasks per parsing interpelli in background.

Questi task permettono l'analisi approfondita degli interpelli con timeout lunghi,
utilizzando Ollama in modo asincrono senza bloccare il sistema.
"""
import logging
from datetime import datetime
from sqlalchemy.orm import Session

from app.tasks import celery_app
from app.database import SessionLocal
from app.services.interpello_parser import InterpelloParser
from app.models.email import Email
from app.models.interpello import Interpello
from app.models.azione import Azione, StatoAzione

logger = logging.getLogger(__name__)


@celery_app.task(
    name='app.tasks.interpello_tasks.parse_interpello',
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # 5 minuti tra i retry
    time_limit=600,  # 10 minuti massimo per task
    soft_time_limit=540  # Warning dopo 9 minuti
)
def parse_interpello(self, email_id: int, azione_id: int = None):
    """
    Task per parsing interpello da email in background.

    Args:
        email_id: ID dell'email da analizzare
        azione_id: ID dell'azione associata (opzionale)

    Returns:
        dict con risultato del parsing
    """
    db = SessionLocal()

    try:
        logger.info(f"📋 Inizio parsing interpello per email {email_id}")

        # Recupera email
        email = db.query(Email).filter(Email.id == email_id).first()
        if not email:
            logger.error(f"Email {email_id} non trovata")
            if azione_id:
                _update_azione_failed(db, azione_id, "Email non trovata")
            return {'status': 'error', 'error': 'Email non trovata'}

        # Aggiorna stato azione se presente
        if azione_id:
            azione = db.query(Azione).filter(Azione.id == azione_id).first()
            if azione:
                azione.stato = StatoAzione.IN_ESECUZIONE
                db.commit()

        # Inizializza parser con db session
        parser = InterpelloParser(db_session=db)

        # Estrai dati dall'email (con timeout lungo configurato nel parser)
        dati = parser.extract_from_email(
            corpo=email.corpo or "",
            allegati_path=email.allegati_path,
            allegati_nomi=email.allegati_nomi,
            allegati_testo=email.allegati_testo,
            oggetto=email.oggetto  # Passa oggetto per estrazione scadenza
        )

        if not dati:
            logger.warning(f"⏭️ Impossibile estrarre dati dall'email {email_id}")
            if azione_id:
                _update_azione_completed(db, azione_id, {
                    'status': 'skipped',
                    'reason': 'Impossibile estrarre dati dall\'interpello'
                })
            return {
                'status': 'skipped',
                'reason': 'Impossibile estrarre dati',
                'email_id': email_id
            }

        # Verifica se esiste già un interpello per questa email
        existing = db.query(Interpello).filter(Interpello.email_id == email_id).first()

        # Determina stato
        stato = "aperto"
        if dati.get('data_scadenza') and dati['data_scadenza'] < datetime.utcnow():
            stato = "scaduto"

        if existing:
            # Aggiorna esistente
            logger.info(f"Aggiornamento interpello esistente ID={existing.id}")
            for key, value in dati.items():
                if hasattr(existing, key) and key != 'testo_completo':
                    setattr(existing, key, value)
            existing.stato = stato
            existing.data_aggiornamento = datetime.utcnow()
            existing.metadata_estrazione = {
                "updated_at": datetime.utcnow().isoformat(),
                "task_id": str(self.request.id)
            }
            db.commit()

            result = {
                'status': 'updated',
                'interpello_id': existing.id,
                'classe_concorso': existing.classe_concorso,
                'provincia': existing.provincia,
                'email_id': email_id
            }

            if azione_id:
                _update_azione_completed(db, azione_id, result)

            logger.info(f"✅ Interpello aggiornato: ID={existing.id}, Classe={existing.classe_concorso}")
            return result

        else:
            # Crea nuovo interpello
            logger.info(f"Creazione nuovo interpello per email {email_id}")

            # Helper to convert dict/list to string safely
            def safe_str(value):
                if value is None:
                    return None
                if isinstance(value, (dict, list)):
                    import json
                    return json.dumps(value)
                return str(value) if value else None

            interpello = Interpello(
                email_id=email_id,
                classe_concorso=dati.get('classe_concorso'),
                numero_posti=dati.get('numero_posti'),
                ore_settimanali=dati.get('ore_settimanali'),
                data_scadenza=dati.get('data_scadenza'),
                data_inizio_servizio=dati.get('data_inizio_servizio'),
                data_fine_contratto=dati.get('data_fine_contratto'),
                provincia=dati.get('provincia'),
                citta=dati.get('citta'),
                istituto=safe_str(dati.get('istituto')),
                indirizzo=safe_str(dati.get('indirizzo')),
                tipo_contratto=safe_str(dati.get('tipo_contratto')),
                orario_giorni=safe_str(dati.get('orario_giorni')),
                link_candidatura=safe_str(dati.get('link_candidatura')),
                link_titoli_accesso=safe_str(dati.get('link_titoli_accesso')),
                testo_completo=dati.get('testo_completo'),
                stato=stato,
                data_pubblicazione=dati.get('data_pubblicazione') or email.data_ricezione,
                metadata_estrazione={
                    "created_at": datetime.utcnow().isoformat(),
                    "task_id": str(self.request.id)
                }
            )
            db.add(interpello)
            db.commit()
            db.refresh(interpello)

            result = {
                'status': 'created',
                'interpello_id': interpello.id,
                'classe_concorso': interpello.classe_concorso,
                'provincia': interpello.provincia,
                'numero_posti': interpello.numero_posti,
                'email_id': email_id
            }

            if azione_id:
                _update_azione_completed(db, azione_id, result)

            logger.info(
                f"✅ Nuovo interpello creato: ID={interpello.id}, "
                f"Classe={interpello.classe_concorso}, "
                f"Provincia={interpello.provincia}"
            )
            return result

    except Exception as e:
        logger.error(f"❌ Errore parsing interpello email {email_id}: {e}", exc_info=True)

        if azione_id:
            _update_azione_failed(db, azione_id, str(e))

        # Retry automatico per errori temporanei
        if self.request.retries < self.max_retries:
            logger.info(f"Retry {self.request.retries + 1}/{self.max_retries} tra 5 minuti...")
            raise self.retry(exc=e)

        return {
            'status': 'error',
            'error': str(e),
            'email_id': email_id
        }

    finally:
        db.close()


def _update_azione_completed(db: Session, azione_id: int, result: dict):
    """Aggiorna azione come completata"""
    try:
        azione = db.query(Azione).filter(Azione.id == azione_id).first()
        if azione:
            azione.stato = StatoAzione.COMPLETATA
            azione.risultato = result
            azione.timestamp_fine = datetime.utcnow()
            db.commit()
    except Exception as e:
        logger.error(f"Errore aggiornamento azione {azione_id}: {e}")


def _update_azione_failed(db: Session, azione_id: int, error_msg: str):
    """Aggiorna azione come fallita"""
    try:
        azione = db.query(Azione).filter(Azione.id == azione_id).first()
        if azione:
            azione.stato = StatoAzione.FALLITA
            azione.errore = error_msg
            azione.risultato = {'error': error_msg}
            azione.timestamp_fine = datetime.utcnow()
            db.commit()
    except Exception as e:
        logger.error(f"Errore aggiornamento azione {azione_id}: {e}")


@celery_app.task(
    name='app.tasks.interpello_tasks.check_expired_interpelli',
    bind=True
)
def check_expired_interpelli(self):
    """
    Task periodico per verificare interpelli scaduti e aggiornare lo stato.

    Eseguito automaticamente ogni giorno.
    """
    db = SessionLocal()

    try:
        logger.info("🔍 Verifica interpelli scaduti...")

        # Trova interpelli aperti con scadenza passata
        now = datetime.utcnow()
        expired = db.query(Interpello).filter(
            Interpello.stato == "aperto",
            Interpello.data_scadenza < now
        ).all()

        if not expired:
            logger.info("✅ Nessun interpello scaduto")
            return {'status': 'success', 'expired_count': 0}

        # Aggiorna stato
        count = 0
        for interpello in expired:
            interpello.stato = "scaduto"
            interpello.data_aggiornamento = datetime.utcnow()
            count += 1

        db.commit()

        logger.info(f"✅ Aggiornati {count} interpelli scaduti")
        return {'status': 'success', 'expired_count': count}

    except Exception as e:
        logger.error(f"❌ Errore verifica interpelli scaduti: {e}")
        return {'status': 'error', 'error': str(e)}

    finally:
        db.close()
