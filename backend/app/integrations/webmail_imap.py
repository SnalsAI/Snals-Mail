"""
Client IMAP per salvare bozze in webmail
"""

import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import logging
import os
from typing import List, Optional

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class WebmailIMAPClient:
    """Client IMAP per webmail SNALS"""

    def __init__(self):
        self.host = settings.WEBMAIL_IMAP_HOST
        self.port = settings.WEBMAIL_IMAP_PORT
        self.user = settings.WEBMAIL_IMAP_USER
        self.password = settings.WEBMAIL_IMAP_PASSWORD

    def connect(self) -> imaplib.IMAP4_SSL:
        """Connessione IMAP SSL"""
        try:
            conn = imaplib.IMAP4_SSL(self.host, self.port)
            conn.login(self.user, self.password)
            logger.info(f"Connesso a IMAP webmail: {self.host}")
            return conn
        except Exception as e:
            logger.error(f"Errore connessione IMAP: {e}")
            raise

    def save_draft(self, to: str, subject: str, body: str,
                   in_reply_to: Optional[str] = None,
                   attachments: Optional[List[str]] = None) -> bool:
        """
        Salva bozza email

        Args:
            to: Destinatario
            subject: Oggetto
            body: Corpo email
            in_reply_to: Message-ID email originale (per threading)
            attachments: Lista path file da allegare

        Returns:
            True se successo
        """
        try:
            # Crea messaggio
            msg = MIMEMultipart()
            msg['From'] = self.user
            msg['To'] = to
            msg['Subject'] = subject

            # Threading
            if in_reply_to:
                msg['In-Reply-To'] = in_reply_to
                msg['References'] = in_reply_to

            # Corpo
            msg.attach(MIMEText(body, 'plain', 'utf-8'))

            # Allegati
            if attachments:
                for filepath in attachments:
                    if not os.path.exists(filepath):
                        logger.warning(f"Allegato non trovato: {filepath}")
                        continue

                    try:
                        with open(filepath, 'rb') as f:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(f.read())
                            encoders.encode_base64(part)
                            filename = os.path.basename(filepath)
                            part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
                            msg.attach(part)
                    except Exception as e:
                        logger.error(f"Errore allegato {filepath}: {e}")

            # Connetti e salva in Drafts
            imap = self.connect()

            # Seleziona cartella Drafts
            # Nota: nome cartella può variare (Drafts, Bozze, Draft, etc)
            # Prova varie opzioni
            drafts_folder = None
            for folder_name in ['Drafts', 'Bozze', '[Gmail]/Drafts', 'INBOX.Drafts']:
                try:
                    result = imap.select(folder_name)
                    if result[0] == 'OK':
                        drafts_folder = folder_name
                        break
                except:
                    continue

            if not drafts_folder:
                logger.error("Cartella Drafts non trovata")
                imap.logout()
                return False

            # Append messaggio
            imap.append(
                drafts_folder,
                '\\Draft',  # Flag Draft
                None,  # Internal date (None = now)
                msg.as_bytes()
            )

            imap.logout()
            logger.info(f"Bozza salvata: {subject[:50]}")
            return True

        except Exception as e:
            logger.error(f"Errore salvataggio bozza: {e}")
            return False
