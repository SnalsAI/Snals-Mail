"""
Servizi ingest email - Connessione POP3/SMTP
"""

import poplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.utils import parseaddr
from typing import List, Dict, Optional
from datetime import datetime
import logging
import os

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class EmailIngestClient:
    """Client base per ingest email"""
    
    def __init__(self, pop3_host: str, pop3_port: int, pop3_user: str, pop3_password: str,
                 smtp_host: str, smtp_port: int, smtp_user: str, smtp_password: str,
                 account_type: str):
        self.pop3_host = pop3_host
        self.pop3_port = pop3_port
        self.pop3_user = pop3_user
        self.pop3_password = pop3_password
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.account_type = account_type
        
    def connect_pop3(self) -> poplib.POP3_SSL:
        """Connessione POP3 SSL"""
        try:
            conn = poplib.POP3_SSL(self.pop3_host, self.pop3_port, timeout=30)
            conn.user(self.pop3_user)
            conn.pass_(self.pop3_password)
            logger.info(f"Connesso a POP3 {self.account_type}: {self.pop3_host}")
            return conn
        except Exception as e:
            logger.error(f"Errore connessione POP3 {self.account_type}: {e}")
            raise

    def fetch_emails(self, limit: int = 50) -> List[Dict]:
        """
        Scarica email dal server POP3 in modo SICURO.

        COMPORTAMENTO SICURO:
        - Usa solo RETR (retrieve) che NON modifica lo stato delle email
        - NON usa DELE (delete) - le email rimangono sul server
        - NON marca come lette - POP3 non supporta questo concetto
        - Le email rimangono esattamente come sono sul server

        Args:
            limit: Numero massimo di email da scaricare (default 50)

        Returns:
            Lista di dict con dati email
        """
        emails_data = []
        conn = None

        try:
            conn = self.connect_pop3()

            # Ottieni numero messaggi
            num_messages = len(conn.list()[1])
            logger.info(f"Trovati {num_messages} messaggi sul server {self.account_type}")

            if num_messages == 0:
                return emails_data

            # Limita il numero di email da processare
            messages_to_fetch = min(num_messages, limit)

            # Scarica le ultime N email (più recenti)
            start_index = max(1, num_messages - messages_to_fetch + 1)

            for i in range(start_index, num_messages + 1):
                try:
                    # RETR scarica il messaggio SENZA modificare il suo stato
                    # Le email rimangono sul server esattamente come sono
                    response, lines, octets = conn.retr(i)

                    # Parse email
                    raw_email = b'\n'.join(lines)
                    msg = email.message_from_bytes(raw_email)

                    # Estrai informazioni
                    message_id = msg.get('Message-ID', f'<generated-{i}@local>')
                    subject = self._decode_header(msg.get('Subject', ''))
                    from_addr = self._decode_header(msg.get('From', ''))
                    to_addr = self._decode_header(msg.get('To', ''))
                    date_str = msg.get('Date', '')

                    # Parse data
                    try:
                        from email.utils import parsedate_to_datetime
                        date_received = parsedate_to_datetime(date_str)
                    except:
                        date_received = datetime.now()

                    # Estrai corpo
                    body = self._extract_body(msg)

                    # Estrai allegati (nomi e path)
                    attachments = self._extract_attachments(msg, message_id)

                    email_data = {
                        'message_id': message_id,
                        'mittente': from_addr,
                        'destinatario': to_addr,
                        'oggetto': subject,
                        'corpo': body,
                        'data_ricezione': date_received,
                        'allegati_nomi': [att['filename'] for att in attachments],
                        'allegati_path': [att['path'] for att in attachments],
                    }

                    emails_data.append(email_data)
                    logger.debug(f"Scaricata email {i}/{num_messages}: {subject[:50]}")

                except Exception as e:
                    logger.error(f"Errore scaricamento email {i}: {e}")
                    continue

            logger.info(f"Scaricate {len(emails_data)} email da {self.account_type}")

            # IMPORTANTE: NON chiamiamo DELE - le email rimangono sul server
            # Se in futuro si vuole eliminare, usare settings.EMAIL_DELETE_FROM_SERVER

        except Exception as e:
            logger.error(f"Errore fetch emails {self.account_type}: {e}")
        finally:
            if conn:
                try:
                    conn.quit()
                except:
                    pass

        return emails_data

    def _decode_header(self, header_value: str) -> str:
        """Decodifica header email"""
        if not header_value:
            return ''

        from email.header import decode_header
        decoded_parts = decode_header(header_value)

        result = []
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                try:
                    result.append(part.decode(encoding or 'utf-8'))
                except:
                    result.append(part.decode('utf-8', errors='ignore'))
            else:
                result.append(part)

        return ' '.join(result)

    def _extract_body(self, msg) -> str:
        """Estrae il corpo del messaggio"""
        body = ""

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))

                # Cerca il corpo in text/plain o text/html
                if content_type == "text/plain" and "attachment" not in content_disposition:
                    try:
                        body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        break
                    except:
                        pass
                elif content_type == "text/html" and not body and "attachment" not in content_disposition:
                    try:
                        body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    except:
                        pass
        else:
            try:
                body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
            except:
                body = str(msg.get_payload())

        return body.strip()

    def _extract_attachments(self, msg, message_id: str) -> List[Dict]:
        """Estrae allegati e li salva"""
        attachments = []

        if not msg.is_multipart():
            return attachments

        # Crea directory per allegati se non esiste
        attachments_dir = os.path.join(settings.ATTACHMENTS_PATH, message_id.strip('<>'))
        os.makedirs(attachments_dir, exist_ok=True)

        for part in msg.walk():
            content_disposition = str(part.get("Content-Disposition"))

            if "attachment" in content_disposition:
                filename = part.get_filename()

                if filename:
                    # Decodifica nome file
                    filename = self._decode_header(filename)

                    # Salva allegato
                    filepath = os.path.join(attachments_dir, filename)

                    try:
                        with open(filepath, 'wb') as f:
                            f.write(part.get_payload(decode=True))

                        attachments.append({
                            'filename': filename,
                            'path': filepath
                        })

                        logger.debug(f"Salvato allegato: {filename}")
                    except Exception as e:
                        logger.error(f"Errore salvataggio allegato {filename}: {e}")

        return attachments


class EmailNormalClient(EmailIngestClient):
    """Client per account email normale"""
    
    def __init__(self):
        super().__init__(
            pop3_host=settings.EMAIL_NORMAL_POP3_HOST,
            pop3_port=settings.EMAIL_NORMAL_POP3_PORT,
            pop3_user=settings.EMAIL_NORMAL_POP3_USER,
            pop3_password=settings.EMAIL_NORMAL_POP3_PASSWORD,
            smtp_host=settings.EMAIL_NORMAL_SMTP_HOST,
            smtp_port=settings.EMAIL_NORMAL_SMTP_PORT,
            smtp_user=settings.EMAIL_NORMAL_SMTP_USER,
            smtp_password=settings.EMAIL_NORMAL_SMTP_PASSWORD,
            account_type="normale"
        )


class EmailPECClient(EmailIngestClient):
    """Client per account PEC"""
    
    def __init__(self):
        super().__init__(
            pop3_host=settings.EMAIL_PEC_POP3_HOST,
            pop3_port=settings.EMAIL_PEC_POP3_PORT,
            pop3_user=settings.EMAIL_PEC_POP3_USER,
            pop3_password=settings.EMAIL_PEC_POP3_PASSWORD,
            smtp_host=settings.EMAIL_PEC_SMTP_HOST,
            smtp_port=settings.EMAIL_PEC_SMTP_PORT,
            smtp_user=settings.EMAIL_PEC_SMTP_USER,
            smtp_password=settings.EMAIL_PEC_SMTP_PASSWORD,
            account_type="pec"
        )
