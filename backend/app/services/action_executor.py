"""
Action Executor - Esegue azioni automatiche sulle email.

FASE 4: Azioni Automatiche
"""
import logging
from typing import Optional, Dict, List
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.azione import Azione, TipoAzione, StatoAzione
from app.models.email import Email
from app.models.interpretazione import Interpretazione
from app.integrations.llm_client import LLMClient
from app.integrations.google_drive_client import GoogleDriveClient
from app.integrations.webmail_client import WebmailClient
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class ActionExecutor:
    """Esecutore di azioni automatiche sulle email."""

    def __init__(self, db: Session):
        """
        Inizializza l'action executor.

        Args:
            db: Sessione database
        """
        self.db = db
        self.llm_client = LLMClient()
        self.drive_client = GoogleDriveClient()

    def execute_actions_for_email(self, email_id: int) -> List[Azione]:
        """
        Esegue tutte le azioni necessarie per una email.

        Args:
            email_id: ID dell'email

        Returns:
            List[Azione]: Lista azioni create
        """
        email = self.db.query(Email).filter(Email.id == email_id).first()

        if not email:
            logger.error(f"Email {email_id} non trovata")
            return []

        if not email.interpretazione:
            logger.warning(f"Email {email_id} non ha interpretazione, skip azioni")
            return []

        azioni = []

        # Determina azioni da eseguire in base alla categoria
        if email.categoria.value == 'richiesta_appuntamento':
            azioni.append(self._create_draft_response(email))
            azioni.append(self._create_calendar_event(email))

        elif email.categoria.value == 'convocazione_scuola':
            azioni.append(self._create_calendar_event(email))
            if email.allegati:
                azioni.append(self._upload_attachments_to_drive(email))

        elif email.categoria.value == 'comunicazione_ust_usr':
            if email.allegati:
                azioni.append(self._upload_attachments_to_drive(email))

        elif email.categoria.value == 'comunicazione_scuola':
            if email.allegati:
                azioni.append(self._upload_attachments_to_drive(email))

        elif email.categoria.value == 'richiesta_tesseramento':
            azioni.append(self._create_draft_response(email))
            if email.allegati:
                azioni.append(self._upload_attachments_to_drive(email))

        # Salva azioni nel database
        for azione in azioni:
            if azione:
                self.db.add(azione)

        self.db.commit()

        logger.info(f"✅ Create {len([a for a in azioni if a])} azioni per email {email_id}")
        return [a for a in azioni if a]

    def _create_draft_response(self, email: Email) -> Optional[Azione]:
        """
        Crea una bozza di risposta usando LLM.

        Args:
            email: Email da cui generare risposta

        Returns:
            Azione: Azione creata
        """
        try:
            interpretazione_data = email.interpretazione.dati_estratti if email.interpretazione else {}

            # Genera risposta con LLM
            prompt = self._build_response_prompt(email, interpretazione_data)
            risposta = self.llm_client.generate(prompt, model_type="generation")

            # Crea azione
            azione = Azione(
                email_id=email.id,
                tipo_azione=TipoAzione.BOZZA_RISPOSTA,
                stato=StatoAzione.PENDING,
                parametri={
                    'to': email.mittente,
                    'subject': f"Re: {email.oggetto}",
                    'body': risposta,
                    'reply_to': email.message_id
                },
                eseguita_at=None
            )

            logger.info(f"✅ Bozza risposta creata per email {email.id}")
            return azione

        except Exception as e:
            logger.error(f"❌ Errore creazione bozza risposta: {e}")
            return None

    def _create_calendar_event(self, email: Email) -> Optional[Azione]:
        """
        Crea un evento calendario dai dati interpretati.

        Args:
            email: Email con dati evento

        Returns:
            Azione: Azione creata
        """
        try:
            if not email.interpretazione:
                return None

            dati = email.interpretazione.dati_estratti

            # Estrai info evento
            data_evento = dati.get('data_evento') or dati.get('data_convocazione')
            ora_evento = dati.get('ora_evento') or dati.get('ora_convocazione')
            luogo = dati.get('luogo') or dati.get('sede')
            descrizione = dati.get('descrizione') or email.corpo_testo[:500]

            if not data_evento:
                logger.warning(f"Nessuna data evento trovata per email {email.id}")
                return None

            # Crea azione
            azione = Azione(
                email_id=email.id,
                tipo_azione=TipoAzione.CREA_EVENTO_CALENDARIO,
                stato=StatoAzione.PENDING,
                parametri={
                    'summary': email.oggetto,
                    'date': data_evento,
                    'time': ora_evento,
                    'location': luogo,
                    'description': descrizione,
                    'attendees': [email.mittente]
                },
                eseguita_at=None
            )

            logger.info(f"✅ Evento calendario creato per email {email.id}")
            return azione

        except Exception as e:
            logger.error(f"❌ Errore creazione evento calendario: {e}")
            return None

    def _upload_attachments_to_drive(self, email: Email) -> Optional[Azione]:
        """
        Carica allegati su Google Drive.

        Args:
            email: Email con allegati

        Returns:
            Azione: Azione creata
        """
        try:
            if not email.allegati:
                return None

            # Crea azione (verrà eseguita dal task)
            azione = Azione(
                email_id=email.id,
                tipo_azione=TipoAzione.CARICA_SU_DRIVE,
                stato=StatoAzione.PENDING,
                parametri={
                    'attachments_count': len(email.allegati),
                    'email_subject': email.oggetto,
                    'email_date': email.data_ricezione.isoformat()
                },
                eseguita_at=None
            )

            logger.info(f"✅ Azione upload Drive creata per email {email.id}")
            return azione

        except Exception as e:
            logger.error(f"❌ Errore creazione azione Drive: {e}")
            return None

    def execute_action(self, azione_id: int) -> bool:
        """
        Esegue una singola azione.

        Args:
            azione_id: ID dell'azione

        Returns:
            bool: True se eseguita con successo
        """
        azione = self.db.query(Azione).filter(Azione.id == azione_id).first()

        if not azione:
            logger.error(f"Azione {azione_id} non trovata")
            return False

        if azione.stato == StatoAzione.COMPLETATA:
            logger.info(f"Azione {azione_id} già completata")
            return True

        try:
            azione.stato = StatoAzione.IN_ESECUZIONE
            self.db.commit()

            success = False

            if azione.tipo_azione == TipoAzione.BOZZA_RISPOSTA:
                success = self._execute_draft_response(azione)

            elif azione.tipo_azione == TipoAzione.CREA_EVENTO_CALENDARIO:
                success = self._execute_calendar_event(azione)

            elif azione.tipo_azione == TipoAzione.CARICA_SU_DRIVE:
                success = self._execute_drive_upload(azione)

            if success:
                azione.stato = StatoAzione.COMPLETATA
                azione.eseguita_at = datetime.now()
                azione.errore = None
            else:
                azione.stato = StatoAzione.FALLITA
                azione.errore = "Esecuzione fallita"

            self.db.commit()
            return success

        except Exception as e:
            logger.error(f"❌ Errore esecuzione azione {azione_id}: {e}")
            azione.stato = StatoAzione.FALLITA
            azione.errore = str(e)
            self.db.commit()
            return False

    def _execute_draft_response(self, azione: Azione) -> bool:
        """Esegue creazione bozza risposta."""
        try:
            params = azione.parametri
            webmail = WebmailClient(azione.email.account_type.value)

            success = webmail.save_draft(
                to=params['to'],
                subject=params['subject'],
                body=params['body'],
                reply_to=params.get('reply_to')
            )

            if success:
                azione.risultato = {'status': 'saved', 'location': 'Drafts folder'}

            return success

        except Exception as e:
            logger.error(f"Errore salvataggio bozza: {e}")
            return False

    def _execute_calendar_event(self, azione: Azione) -> bool:
        """Esegue creazione evento calendario."""
        try:
            # Questa parte verrà implementata nella Fase 6 con Google Calendar API
            # Per ora segniamo come completata e salviamo i parametri
            azione.risultato = {
                'status': 'pending_google_calendar_integration',
                'event_data': azione.parametri
            }
            logger.info(f"⚠️ Evento calendario preparato (Google Calendar API da integrare)")
            return True

        except Exception as e:
            logger.error(f"Errore creazione evento: {e}")
            return False

    def _execute_drive_upload(self, azione: Azione) -> bool:
        """Esegue upload allegati su Drive."""
        try:
            email = azione.email

            if not email.allegati:
                return False

            # Prepara allegati per upload
            attachments = []
            for allegato in email.allegati:
                # Qui dovresti caricare il contenuto reale dall'allegato
                # Per ora usiamo un placeholder
                attachments.append((
                    allegato.get('filename', 'unknown'),
                    b'',  # Contenuto allegato (da implementare storage)
                    allegato.get('content_type', 'application/octet-stream')
                ))

            # Upload su Drive
            base_folder_id = self.drive_client.get_or_create_base_folder()
            uploaded_files = self.drive_client.upload_attachments(
                attachments,
                email.oggetto,
                base_folder_id
            )

            azione.risultato = {
                'uploaded_files': uploaded_files,
                'folder_id': base_folder_id
            }

            return len(uploaded_files) > 0

        except Exception as e:
            logger.error(f"Errore upload Drive: {e}")
            return False

    def _build_response_prompt(self, email: Email, interpretazione: Dict) -> str:
        """Costruisce prompt per generare risposta."""

        prompt = f"""Sei un assistente di una sede sindacale SNALS.

Genera una risposta professionale e cortese per la seguente email:

**Da:** {email.mittente}
**Oggetto:** {email.oggetto}
**Corpo:**
{email.corpo_testo[:1000]}

**Categoria email:** {email.categoria.value}

**Informazioni estratte:**
{interpretazione}

**Istruzioni:**
1. Rispondi in modo professionale e cortese
2. Fai riferimento alle informazioni specifiche nell'email
3. Se è una richiesta appuntamento, conferma disponibilità e chiedi eventuali preferenze
4. Se è richiesta tesseramento, fornisci info su documenti necessari e procedura
5. Firma come "Segreteria SNALS"
6. Usa formato HTML con paragrafi ben formattati

Genera solo la risposta, senza soggetto.
"""
        return prompt
