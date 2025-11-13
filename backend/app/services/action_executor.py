"""
Motore esecuzione azioni automatiche
"""

from typing import Dict, List
import logging
from datetime import datetime

from app.database import SessionLocal
from app.models.email import Email, EmailStatus
from app.models.interpretazione import Interpretazione
from app.models.azione import Azione, TipoAzione, StatoAzione
from app.models.evento import EventoCalendario
from app.services.email_ingest import EmailNormalClient
from app.integrations.llm_client import LLMClient
from app.integrations.webmail_imap import WebmailIMAPClient
from app.integrations.google_drive import GoogleDriveClient
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ActionExecutor:
    """Esecutore azioni automatiche"""

    def __init__(self):
        self.llm_client = LLMClient()
        self.email_client = EmailNormalClient()
        self.webmail_client = WebmailIMAPClient()
        self.drive_client = GoogleDriveClient()

    def execute_actions_for_email(self, email_id: int):
        """
        Esegue azioni appropriate per email in base a categoria
        """
        db = SessionLocal()

        try:
            email = db.query(Email).filter(Email.id == email_id).first()
            if not email:
                logger.error(f"Email {email_id} non trovata")
                return

            interpretazione = db.query(Interpretazione).filter(
                Interpretazione.email_id == email_id
            ).first()

            if not interpretazione:
                logger.warning(f"Nessuna interpretazione per email {email_id}")
                return

            categoria = email.categoria
            interp_data = interpretazione.interpretazione_json

            # Dispatch azione per categoria
            if categoria.value == "info_generiche":
                self._azione_info_generiche(email, interp_data, db)

            elif categoria.value == "richiesta_appuntamento":
                self._azione_appuntamento(email, interp_data, db)

            elif categoria.value == "richiesta_tesseramento":
                self._azione_tesseramento(email, interp_data, db)

            elif categoria.value == "convocazione_scuola":
                self._azione_convocazione(email, interp_data, db)

            elif categoria.value == "comunicazione_ust_usr":
                self._azione_ust_usr(email, interp_data, db)

            elif categoria.value == "comunicazione_snals_centrale":
                self._azione_snals_centrale(email, interp_data, db)

            elif categoria.value == "comunicazione_scuola":
                self._azione_scuola(email, interp_data, db)

            # Aggiorna stato email
            email.stato = EmailStatus.AZIONE_ESEGUITA
            db.commit()

            logger.info(f"Azioni eseguite per email {email_id}")

        except Exception as e:
            logger.error(f"Errore esecuzione azioni per email {email_id}: {e}")
            db.rollback()
        finally:
            db.close()

    def _azione_info_generiche(self, email: Email, interp_data: Dict, db):
        """Genera bozza risposta con LLM"""

        prompt = f"""Scrivi una risposta professionale e cortese per il sindacato SNALS a questa richiesta di informazioni.

RICHIESTA ORIGINALE:
Da: {email.mittente}
Oggetto: {email.oggetto}
Contenuto:
{email.corpo[:1000]}

CONTESTO INTERPRETAZIONE:
- Argomento principale: {interp_data.get('argomento_principale', 'non specificato')}
- Domande specifiche: {', '.join(interp_data.get('domande_specifiche', []))}

ISTRUZIONI:
- Saluta cordialmente il mittente
- Rispondi in modo professionale e competente
- Se non hai informazioni precise, invita a contattare la sede per dettagli
- Fornisci contatti utili se pertinente
- Chiudi cordialmente con firma "Il team SNALS [Sede]"
- Mantieni un tono formale ma cordiale

RISPOSTA:
"""

        try:
            # Genera risposta
            risposta = self.llm_client.generate(
                prompt=prompt,
                model_type="generation",
                temperature=0.7
            )

            # Salva bozza in webmail
            success = self.webmail_client.save_draft(
                to=email.mittente,
                subject=f"Re: {email.oggetto}",
                body=risposta,
                in_reply_to=email.message_id
            )

            # Registra azione
            azione = Azione(
                email_id=email.id,
                tipo=TipoAzione.BOZZA_RISPOSTA,
                stato=StatoAzione.COMPLETATA if success else StatoAzione.FALLITA,
                dettagli={"prompt_used": "info_generiche"},
                risultato={"bozza_salvata": success, "preview": risposta[:200]},
                timestamp_fine=datetime.utcnow()
            )
            db.add(azione)

            logger.info(f"Bozza risposta generata per email {email.id}")

        except Exception as e:
            logger.error(f"Errore generazione bozza info_generiche: {e}")
            azione = Azione(
                email_id=email.id,
                tipo=TipoAzione.BOZZA_RISPOSTA,
                stato=StatoAzione.FALLITA,
                errore=str(e)
            )
            db.add(azione)

    def _azione_appuntamento(self, email: Email, interp_data: Dict, db):
        """Genera bozza con link piattaforma prenotazione"""

        # URL piattaforma (configurabile)
        url_prenotazione = "https://prenotazioni.snals.it"  # TODO: da config

        template = f"""Gentile {email.mittente.split('@')[0].title()},

grazie per averci contattato.

Per fissare un appuntamento, la invitiamo a utilizzare la nostra piattaforma di prenotazione online:

{url_prenotazione}

Potrà scegliere data e orario che preferisce tra le disponibilità.

Se preferisce essere ricontattato telefonicamente, può indicarlo nella piattaforma o rispondere a questa email con i suoi riferimenti.

Cordiali saluti,
Il team SNALS
"""

        try:
            success = self.webmail_client.save_draft(
                to=email.mittente,
                subject=f"Re: {email.oggetto}",
                body=template,
                in_reply_to=email.message_id
            )

            azione = Azione(
                email_id=email.id,
                tipo=TipoAzione.BOZZA_APPUNTAMENTO,
                stato=StatoAzione.COMPLETATA if success else StatoAzione.FALLITA,
                risultato={"bozza_salvata": success},
                timestamp_fine=datetime.utcnow()
            )
            db.add(azione)

            logger.info(f"Bozza appuntamento per email {email.id}")

        except Exception as e:
            logger.error(f"Errore bozza appuntamento: {e}")

    def _azione_tesseramento(self, email: Email, interp_data: Dict, db):
        """Genera bozza con allegati da repository"""

        import os

        # Path repository tesseramento
        repo_path = os.path.join(settings.REPOSITORY_PATH, "tesseramento")

        # Trova file da allegare
        allegati = []
        if os.path.exists(repo_path):
            for filename in os.listdir(repo_path):
                filepath = os.path.join(repo_path, filename)
                if os.path.isfile(filepath):
                    allegati.append(filepath)

        template = f"""Gentile {email.mittente.split('@')[0].title()},

grazie per il suo interesse nel tesseramento SNALS.

In allegato trova tutta la documentazione necessaria per l'iscrizione:
- Modulo di iscrizione
- Informativa privacy
- Modalità di pagamento

Per qualsiasi chiarimento, non esiti a contattarci.

Cordiali saluti,
Il team SNALS
"""

        try:
            success = self.webmail_client.save_draft(
                to=email.mittente,
                subject=f"Re: {email.oggetto}",
                body=template,
                in_reply_to=email.message_id,
                attachments=allegati
            )

            azione = Azione(
                email_id=email.id,
                tipo=TipoAzione.BOZZA_TESSERAMENTO,
                stato=StatoAzione.COMPLETATA if success else StatoAzione.FALLITA,
                dettagli={"num_allegati": len(allegati)},
                risultato={"bozza_salvata": success},
                timestamp_fine=datetime.utcnow()
            )
            db.add(azione)

            logger.info(f"Bozza tesseramento per email {email.id} con {len(allegati)} allegati")

        except Exception as e:
            logger.error(f"Errore bozza tesseramento: {e}")

    def _azione_convocazione(self, email: Email, interp_data: Dict, db):
        """Crea evento calendario"""

        from dateutil import parser as date_parser

        try:
            # Parse data/ora
            data_riunione_str = interp_data.get('data_riunione')
            if not data_riunione_str:
                logger.warning(f"Data riunione non trovata per email {email.id}")
                return

            data_inizio = date_parser.parse(data_riunione_str)

            # Ora fine (se presente, altrimenti +2 ore)
            ora_fine_str = interp_data.get('ora_fine')
            if ora_fine_str:
                # Combina data con ora fine
                from datetime import datetime, timedelta
                ora_fine = datetime.strptime(ora_fine_str, "%H:%M").time()
                data_fine = datetime.combine(data_inizio.date(), ora_fine)
            else:
                from datetime import timedelta
                data_fine = data_inizio + timedelta(hours=2)

            # Crea evento
            evento = EventoCalendario(
                email_id=email.id,
                titolo=interp_data.get('oggetto_riunione', email.oggetto),
                descrizione=self._format_evento_description(email, interp_data),
                data_inizio=data_inizio,
                data_fine=data_fine,
                luogo=interp_data.get('luogo', ''),
                link_videocall=interp_data.get('link_videocall'),
                scuola=interp_data.get('scuola', ''),
                tipo_convocazione=interp_data.get('tipo_convocazione', ''),
                allegati=email.allegati_path,
                sincronizzato=False  # Sincronizzerà task apposito
            )

            db.add(evento)

            # Registra azione
            azione = Azione(
                email_id=email.id,
                tipo=TipoAzione.EVENTO_CALENDARIO,
                stato=StatoAzione.COMPLETATA,
                dettagli={"scuola": interp_data.get('scuola')},
                risultato={"evento_id": evento.id},
                timestamp_fine=datetime.utcnow()
            )
            db.add(azione)

            logger.info(f"Evento calendario creato per email {email.id}")

        except Exception as e:
            logger.error(f"Errore creazione evento: {e}")

    def _format_evento_description(self, email: Email, interp_data: Dict) -> str:
        """Formatta descrizione evento da interpretazione"""

        desc = f"Convocazione da: {email.mittente}\n\n"

        if interp_data.get('oggetto_riunione'):
            desc += f"Oggetto: {interp_data['oggetto_riunione']}\n\n"

        if interp_data.get('ordine_del_giorno'):
            desc += "Ordine del giorno:\n"
            for i, punto in enumerate(interp_data['ordine_del_giorno'], 1):
                desc += f"{i}. {punto}\n"
            desc += "\n"

        if interp_data.get('note_particolari'):
            desc += f"Note: {interp_data['note_particolari']}\n"

        return desc

    def _azione_ust_usr(self, email: Email, interp_data: Dict, db):
        """Upload allegati su Google Drive + eventuale sintesi"""

        if not email.allegati_path:
            logger.info(f"Nessun allegato da uploadare per email {email.id}")
            return

        try:
            # Upload su Drive
            folder_name = f"UST_USR/{datetime.now().year}/{datetime.now().month:02d}"

            uploaded_files = []
            for filepath in email.allegati_path:
                file_id = self.drive_client.upload_file(
                    filepath,
                    folder_name,
                    metadata={
                        "mittente": email.mittente,
                        "oggetto": email.oggetto,
                        "data": email.data_ricezione.isoformat()
                    }
                )
                if file_id:
                    uploaded_files.append(file_id)

            # Registra azione
            azione = Azione(
                email_id=email.id,
                tipo=TipoAzione.UPLOAD_DRIVE,
                stato=StatoAzione.COMPLETATA if uploaded_files else StatoAzione.FALLITA,
                dettagli={"folder": folder_name, "num_files": len(email.allegati_path)},
                risultato={"uploaded_files": uploaded_files},
                timestamp_fine=datetime.utcnow()
            )
            db.add(azione)

            logger.info(f"Upload Drive per email {email.id}: {len(uploaded_files)} file")

        except Exception as e:
            logger.error(f"Errore upload Drive: {e}")

    def _azione_snals_centrale(self, email: Email, interp_data: Dict, db):
        """Upload allegati SNALS centrale su Google Drive"""

        if not email.allegati_path:
            return

        try:
            folder_name = f"SNALS_Centrale/{datetime.now().year}/{datetime.now().month:02d}"

            uploaded_files = []
            for filepath in email.allegati_path:
                file_id = self.drive_client.upload_file(
                    filepath,
                    folder_name,
                    metadata={
                        "tipo_comunicazione": interp_data.get('tipo_comunicazione', ''),
                        "numero_circolare": interp_data.get('numero_circolare', ''),
                        "data": email.data_ricezione.isoformat()
                    }
                )
                if file_id:
                    uploaded_files.append(file_id)

            azione = Azione(
                email_id=email.id,
                tipo=TipoAzione.UPLOAD_DRIVE,
                stato=StatoAzione.COMPLETATA if uploaded_files else StatoAzione.FALLITA,
                dettagli={"folder": folder_name},
                risultato={"uploaded_files": uploaded_files},
                timestamp_fine=datetime.utcnow()
            )
            db.add(azione)

            logger.info(f"Upload Drive SNALS centrale: {len(uploaded_files)} file")

        except Exception as e:
            logger.error(f"Errore upload Drive SNALS: {e}")

    def _azione_scuola(self, email: Email, interp_data: Dict, db):
        """Salva interpretazione per sintesi (azione leggera)"""

        # Per comunicazioni scuole, principalmente loggiamo l'interpretazione
        # Sintesi aggregate verranno generate da task periodico se richiesto

        azione = Azione(
            email_id=email.id,
            tipo=TipoAzione.SINTESI,
            stato=StatoAzione.COMPLETATA,
            dettagli={"tipo": "comunicazione_scuola"},
            risultato={"interpretazione_salvata": True},
            timestamp_fine=datetime.utcnow()
        )
        db.add(azione)
