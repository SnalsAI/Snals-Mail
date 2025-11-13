"""
Webmail Client IMAP per salvare bozze email.

FASE 4: Azioni Automatiche
"""
import logging
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from imaplib import IMAP4_SSL
from typing import Optional

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class WebmailClient:
    """Client IMAP per gestire bozze email."""

    def __init__(self, account_type: str = "normal"):
        """
        Inizializza il client webmail.

        Args:
            account_type: "normal" o "pec"
        """
        self.account_type = account_type

        if account_type == "pec":
            self.imap_host = settings.EMAIL_PEC_IMAP_HOST
            self.imap_port = settings.EMAIL_PEC_IMAP_PORT
            self.imap_user = settings.EMAIL_PEC_IMAP_USER
            self.imap_password = settings.EMAIL_PEC_IMAP_PASSWORD
            self.smtp_host = settings.EMAIL_PEC_SMTP_HOST
            self.smtp_port = settings.EMAIL_PEC_SMTP_PORT
        else:
            self.imap_host = settings.EMAIL_NORMAL_IMAP_HOST
            self.imap_port = settings.EMAIL_NORMAL_IMAP_PORT
            self.imap_user = settings.EMAIL_NORMAL_IMAP_USER
            self.imap_password = settings.EMAIL_NORMAL_IMAP_PASSWORD
            self.smtp_host = settings.EMAIL_NORMAL_SMTP_HOST
            self.smtp_port = settings.EMAIL_NORMAL_SMTP_PORT

    def connect_imap(self) -> Optional[IMAP4_SSL]:
        """
        Connette al server IMAP.

        Returns:
            IMAP4_SSL: Connessione IMAP
        """
        try:
            conn = IMAP4_SSL(self.imap_host, self.imap_port)
            conn.login(self.imap_user, self.imap_password)
            logger.info(f"✅ Connesso a IMAP {self.account_type}: {self.imap_host}")
            return conn
        except Exception as e:
            logger.error(f"❌ Errore connessione IMAP {self.account_type}: {e}")
            return None

    def save_draft(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[str] = None,
        bcc: Optional[str] = None,
        reply_to: Optional[str] = None
    ) -> bool:
        """
        Salva una bozza email nella cartella Drafts.

        Args:
            to: Destinatario
            subject: Oggetto
            body: Corpo email (HTML o text)
            cc: CC (opzionale)
            bcc: BCC (opzionale)
            reply_to: Reply-To / In-Reply-To message ID (opzionale)

        Returns:
            bool: True se salvata con successo
        """
        conn = self.connect_imap()
        if not conn:
            return False

        try:
            # Crea messaggio MIME
            msg = MIMEMultipart('alternative')
            msg['From'] = self.imap_user
            msg['To'] = to
            msg['Subject'] = subject

            if cc:
                msg['Cc'] = cc
            if bcc:
                msg['Bcc'] = bcc
            if reply_to:
                msg['In-Reply-To'] = reply_to
                msg['References'] = reply_to

            # Determina se è HTML o testo
            if '<html>' in body.lower() or '<p>' in body.lower():
                msg.attach(MIMEText(body, 'html', 'utf-8'))
            else:
                msg.attach(MIMEText(body, 'plain', 'utf-8'))

            # Converti in stringa
            message_str = msg.as_string()

            # Salva nella cartella Drafts
            # Nota: Il nome della cartella può variare (Drafts, Bozze, [Gmail]/Drafts, ecc.)
            draft_folders = ['Drafts', 'Bozze', '[Gmail]/Drafts', 'INBOX.Drafts']

            saved = False
            for folder in draft_folders:
                try:
                    # Seleziona cartella Drafts
                    status, _ = conn.select(folder)

                    if status == 'OK':
                        # Append messaggio alla cartella
                        conn.append(
                            folder,
                            '\\Draft',
                            None,
                            message_str.encode('utf-8')
                        )
                        logger.info(f"✅ Bozza salvata in {folder}: {subject}")
                        saved = True
                        break
                except Exception as e:
                    logger.debug(f"Cartella {folder} non disponibile: {e}")
                    continue

            if not saved:
                logger.warning(f"⚠️ Nessuna cartella Drafts trovata. Tentativo salvataggio in INBOX")
                conn.select('INBOX')
                conn.append(
                    'INBOX',
                    '\\Draft',
                    None,
                    message_str.encode('utf-8')
                )
                logger.info(f"✅ Bozza salvata in INBOX: {subject}")

            conn.close()
            conn.logout()
            return True

        except Exception as e:
            logger.error(f"❌ Errore salvataggio bozza: {e}")
            try:
                conn.close()
                conn.logout()
            except:
                pass
            return False

    def list_drafts(self, limit: int = 10) -> list:
        """
        Lista le bozze presenti.

        Args:
            limit: Numero massimo bozze da recuperare

        Returns:
            list: Lista di dict con info bozze
        """
        conn = self.connect_imap()
        if not conn:
            return []

        try:
            # Cerca cartella Drafts
            draft_folders = ['Drafts', 'Bozze', '[Gmail]/Drafts', 'INBOX.Drafts']

            for folder in draft_folders:
                try:
                    status, _ = conn.select(folder, readonly=True)
                    if status == 'OK':
                        break
                except:
                    continue
            else:
                logger.warning("Nessuna cartella Drafts trovata")
                return []

            # Cerca messaggi con flag \Draft
            status, messages = conn.search(None, 'ALL')

            if status != 'OK':
                return []

            message_ids = messages[0].split()
            drafts = []

            # Prendi solo gli ultimi N
            for msg_id in message_ids[-limit:]:
                status, msg_data = conn.fetch(msg_id, '(RFC822)')

                if status != 'OK':
                    continue

                raw_email = msg_data[0][1]
                email_message = email.message_from_bytes(raw_email)

                drafts.append({
                    'id': msg_id.decode(),
                    'to': email_message.get('To'),
                    'subject': email_message.get('Subject'),
                    'date': email_message.get('Date')
                })

            conn.close()
            conn.logout()

            logger.info(f"✅ Trovate {len(drafts)} bozze")
            return drafts

        except Exception as e:
            logger.error(f"❌ Errore recupero bozze: {e}")
            try:
                conn.close()
                conn.logout()
            except:
                pass
            return []
