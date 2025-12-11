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

    def test_connection(self) -> Dict:
        """
        Test completo della configurazione email:
        1. Test POP3: connessione e lettura prima email
        2. Test SMTP: invio email di test a se stesso

        Returns:
            Dict con risultati dettagliati del test
        """
        results = {
            'pop3': {'success': False, 'message': '', 'details': {}},
            'smtp': {'success': False, 'message': '', 'details': {}},
            'overall_success': False
        }

        # TEST POP3
        logger.info(f"Inizio test POP3 per account {self.account_type}")
        try:
            conn = self.connect_pop3()

            # Ottieni numero messaggi
            num_messages = len(conn.list()[1])
            results['pop3']['details']['num_messages'] = num_messages

            if num_messages > 0:
                # Leggi solo l'header della prima email (più veloce)
                response, lines, octets = conn.top(1, 0)  # top(msg_num, num_lines_body)

                # Parse header
                raw_header = b'\n'.join(lines)
                msg = email.message_from_bytes(raw_header)

                subject = self._decode_header(msg.get('Subject', '(nessun oggetto)'))
                from_addr = self._decode_header(msg.get('From', ''))

                results['pop3']['details']['first_email_subject'] = subject[:100]
                results['pop3']['details']['first_email_from'] = from_addr
                results['pop3']['success'] = True
                results['pop3']['message'] = f"✅ Connessione POP3 riuscita! Trovate {num_messages} email."
            else:
                results['pop3']['success'] = True
                results['pop3']['message'] = "✅ Connessione POP3 riuscita! Nessuna email presente nella casella."

            conn.quit()
            logger.info(f"Test POP3 completato con successo per {self.account_type}")

        except Exception as e:
            results['pop3']['success'] = False
            results['pop3']['message'] = f"❌ Errore POP3: {str(e)}"
            logger.error(f"Test POP3 fallito per {self.account_type}: {e}")

        # TEST SMTP
        logger.info(f"Inizio test SMTP per account {self.account_type}")
        try:
            # Crea messaggio di test
            msg = MIMEMultipart()
            msg['From'] = f"Segreteria Provinciale SNALS di Taranto <{self.smtp_user}>"
            msg['To'] = self.smtp_user  # Invia a se stesso
            msg['Subject'] = f"Test SNALS Email Agent - {self.account_type.upper()}"

            body = f"""
Questo è un messaggio di test automatico generato da SNALS Email Agent.

Account: {self.account_type.upper()}
Server SMTP: {self.smtp_host}:{self.smtp_port}
Data/Ora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Se ricevi questo messaggio, la configurazione SMTP è corretta! ✅

---
SNALS Email Agent - Sistema di gestione email automatizzato
            """.strip()

            msg.attach(MIMEText(body, 'plain', 'utf-8'))

            # Connessione SMTP - usa SSL diretto per porta 465, STARTTLS per altre porte
            if self.smtp_port == 465:
                # SSL/TLS diretto (SMTPS)
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=30)
                results['smtp']['details']['ssl'] = True
                results['smtp']['details']['starttls'] = False
            else:
                # STARTTLS per porte 587/25
                server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30)
                server.ehlo()
                if server.has_extn('STARTTLS'):
                    server.starttls()
                    server.ehlo()
                    results['smtp']['details']['starttls'] = True
                else:
                    results['smtp']['details']['starttls'] = False
                results['smtp']['details']['ssl'] = False

            # Login
            server.login(self.smtp_user, self.smtp_password)
            results['smtp']['details']['auth'] = True

            # Invia email
            server.send_message(msg)
            server.quit()

            results['smtp']['success'] = True
            results['smtp']['message'] = f"✅ Email di test inviata con successo a {self.smtp_user}"
            results['smtp']['details']['recipient'] = self.smtp_user
            logger.info(f"Test SMTP completato con successo per {self.account_type}")

        except Exception as e:
            results['smtp']['success'] = False
            results['smtp']['message'] = f"❌ Errore SMTP: {str(e)}"
            logger.error(f"Test SMTP fallito per {self.account_type}: {e}")

        # Verifica successo complessivo
        results['overall_success'] = results['pop3']['success'] and results['smtp']['success']

        return results

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
        # Skip silenziosamente se le credenziali sono quelle di default/example
        if 'example.com' in self.pop3_host or self.pop3_password == 'changeme':
            logger.debug(f"Skip polling {self.account_type}: credenziali non configurate")
            return []
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
                        from zoneinfo import ZoneInfo
                        date_received = parsedate_to_datetime(date_str)
                        # Convert to local timezone (Europe/Rome) before storing
                        # This ensures the time is correct when read back
                        if date_received.tzinfo is not None:
                            date_received = date_received.astimezone(ZoneInfo('Europe/Rome')).replace(tzinfo=None)
                    except:
                        date_received = datetime.now()

                    # Estrai corpo (text e html separati)
                    corpo_text, corpo_html = self._extract_body(msg)

                    # Estrai allegati (nomi, path e testo PDF)
                    attachments, allegati_testo = self._extract_attachments(msg, message_id)

                    # Ora gli attachments includono TUTTI i file (PDF + altri)
                    # allegati_testo contiene solo il testo estratto dai PDF
                    email_data = {
                        'message_id': message_id,
                        'mittente': from_addr,
                        'destinatario': to_addr,
                        'oggetto': subject,
                        'corpo': corpo_text,
                        'corpo_html': corpo_html,
                        'data_ricezione': date_received,
                        'allegati_nomi': [att['filename'] for att in attachments],
                        'allegati_path': [att['path'] for att in attachments],
                        'allegati_testo': allegati_testo,
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

    def _extract_body(self, msg) -> tuple:
        """Estrae il corpo del messaggio in formato text e html.

        Returns:
            tuple: (corpo_text, corpo_html) - entrambi possono essere None
        """
        corpo_text = None
        corpo_html = None

        def extract_from_part(part):
            """Estrae contenuto da una singola parte."""
            nonlocal corpo_text, corpo_html
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition") or "")

            if "attachment" in content_disposition:
                return

            # Prova diverse codifiche
            def decode_payload(p):
                payload = p.get_payload(decode=True)
                if payload is None:
                    return None
                for encoding in ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']:
                    try:
                        return payload.decode(encoding)
                    except:
                        continue
                return payload.decode('utf-8', errors='ignore')

            if content_type == "text/plain" and not corpo_text:
                try:
                    corpo_text = decode_payload(part)
                except Exception as e:
                    logger.warning(f"Errore estrazione text/plain: {e}")
            elif content_type == "text/html" and not corpo_html:
                try:
                    corpo_html = decode_payload(part)
                except Exception as e:
                    logger.warning(f"Errore estrazione text/html: {e}")

        if msg.is_multipart():
            # Itera ricorsivamente su tutte le parti
            for part in msg.walk():
                if part.is_multipart():
                    continue  # Salta i container multipart
                extract_from_part(part)
        else:
            # Messaggio non-multipart
            content_type = msg.get_content_type()
            try:
                payload = msg.get_payload(decode=True)
                if payload:
                    decoded = payload.decode('utf-8', errors='ignore')
                    if content_type == "text/html":
                        corpo_html = decoded
                    else:
                        corpo_text = decoded
            except Exception as e:
                logger.warning(f"Errore estrazione corpo non-multipart: {e}")
                corpo_text = str(msg.get_payload())

        # Fallback: se abbiamo solo HTML, estrai testo da HTML
        if not corpo_text and corpo_html:
            try:
                import re
                from html import unescape
                # Rimuovi script, style e head
                text = re.sub(r'<script[^>]*>.*?</script>', '', corpo_html, flags=re.DOTALL | re.IGNORECASE)
                text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
                text = re.sub(r'<head[^>]*>.*?</head>', '', text, flags=re.DOTALL | re.IGNORECASE)
                # Rimuovi tutti i tag HTML
                text = re.sub(r'<[^>]+>', ' ', text)
                # Decodifica entità HTML
                text = unescape(text)
                # Normalizza spazi
                text = re.sub(r'\s+', ' ', text).strip()
                corpo_text = text
            except Exception as e:
                logger.warning(f"Errore conversione HTML->text: {e}")
                corpo_text = corpo_html  # Fallback: usa HTML grezzo

        # Cleanup
        if corpo_text:
            corpo_text = corpo_text.strip()
        if corpo_html:
            corpo_html = corpo_html.strip()

        return (corpo_text or "", corpo_html)

    def _extract_attachments(self, msg, message_id: str) -> tuple:
        """
        Estrae allegati e il testo dai PDF.

        Returns:
            tuple: (attachments_list, allegati_testo_dict)
                - attachments_list: Lista di dict con filename e path (solo per allegati non-PDF)
                - allegati_testo_dict: Dict con {filename: testo_estratto} per PDF
        """
        attachments = []
        allegati_testo = {}

        if not msg.is_multipart():
            return (attachments, allegati_testo)

        # Crea directory per allegati se non esiste
        # Sanitize message_id: rimuovi newlines, tabs e caratteri invalidi per path
        clean_message_id = message_id.strip().strip('<>').replace('\n', '').replace('\r', '').replace('\t', '').replace('/', '_').replace('\\', '_')
        attachments_dir = os.path.join(settings.ATTACHMENTS_PATH, clean_message_id)
        os.makedirs(attachments_dir, exist_ok=True)

        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))

            # Estrai allegati standard (con "attachment" in disposition)
            is_attachment = "attachment" in content_disposition

            # Estrai anche messaggi email allegati (buste PEC)
            # Content-Type: message/rfc822 o message/*
            is_email_attachment = content_type.startswith('message/')

            if is_attachment or is_email_attachment:
                filename = part.get_filename()

                # Se non ha filename ma è un messaggio allegato, genera uno
                if not filename and is_email_attachment:
                    filename = "messaggio.eml"

                if filename:
                    # Decodifica nome file
                    filename = self._decode_header(filename)

                    # Salva allegato
                    filepath = os.path.join(attachments_dir, filename)

                    try:
                        # Per messaggi RFC822, ottieni il payload come bytes
                        if is_email_attachment and not is_attachment:
                            # Messaggio allegato (busta PEC)
                            payload = part.as_bytes()
                        else:
                            # Allegato standard
                            payload = part.get_payload(decode=True)

                        if payload is not None:
                            # Determina se è un PDF
                            is_pdf = (
                                content_type == 'application/pdf' or
                                filename.lower().endswith('.pdf')
                            )

                            if is_pdf:
                                # Per PDF: salva temporaneamente, estrai testo, elimina file
                                with open(filepath, 'wb') as f:
                                    f.write(payload)

                                try:
                                    # Estrai testo dal PDF
                                    import pdfplumber
                                    with pdfplumber.open(filepath) as pdf:
                                        text = ""
                                        for page in pdf.pages:
                                            page_text = page.extract_text()
                                            if page_text:
                                                text += page_text + "\n"

                                    # Salva testo estratto
                                    allegati_testo[filename] = text.strip()
                                    logger.info(f"📄 Estratto testo da PDF {filename}: {len(text)} caratteri")

                                    # Mantieni il PDF su disco E aggiungilo agli attachments
                                    # (serve per Drive upload e RAG indexing!)
                                    attachments.append({
                                        'filename': filename,
                                        'path': filepath
                                    })
                                    logger.debug(f"✅ PDF {filename} conservato su disco per upload/RAG")

                                except Exception as pdf_error:
                                    logger.error(f"Errore estrazione testo da PDF {filename}: {pdf_error}")
                                    # In caso di errore, salva comunque il PDF per permettere upload/RAG
                                    attachments.append({
                                        'filename': filename,
                                        'path': filepath
                                    })

                            elif filename.lower().endswith('.zip') or content_type == 'application/zip':
                                # Per ZIP: estrai e leggi PDF/Word contenuti
                                import zipfile
                                import tempfile

                                with open(filepath, 'wb') as f:
                                    f.write(payload)

                                try:
                                    with zipfile.ZipFile(filepath, 'r') as zip_ref:
                                        # Crea directory temporanea per estrazione
                                        extract_dir = os.path.join(attachments_dir, f"zip_{filename}")
                                        os.makedirs(extract_dir, exist_ok=True)
                                        zip_ref.extractall(extract_dir)

                                        # Processa ogni file estratto
                                        for root, dirs, files in os.walk(extract_dir):
                                            for extracted_file in files:
                                                extracted_path = os.path.join(root, extracted_file)
                                                extracted_lower = extracted_file.lower()

                                                if extracted_lower.endswith('.pdf'):
                                                    # Estrai testo da PDF
                                                    try:
                                                        import pdfplumber
                                                        with pdfplumber.open(extracted_path) as pdf:
                                                            text = ""
                                                            for page in pdf.pages:
                                                                page_text = page.extract_text()
                                                                if page_text:
                                                                    text += page_text + "\n"
                                                        if text.strip():
                                                            allegati_testo[f"{filename}/{extracted_file}"] = text.strip()
                                                            logger.info(f"📄 Estratto testo da ZIP/{extracted_file}: {len(text)} caratteri")
                                                    except Exception as pdf_err:
                                                        logger.warning(f"Errore PDF in ZIP {extracted_file}: {pdf_err}")

                                                elif extracted_lower.endswith('.docx'):
                                                    # Estrai testo da Word
                                                    try:
                                                        from docx import Document
                                                        doc = Document(extracted_path)
                                                        text = "\n".join([p.text for p in doc.paragraphs if p.text])
                                                        if text.strip():
                                                            allegati_testo[f"{filename}/{extracted_file}"] = text.strip()
                                                            logger.info(f"📄 Estratto testo da ZIP/{extracted_file}: {len(text)} caratteri")
                                                    except Exception as docx_err:
                                                        logger.warning(f"Errore DOCX in ZIP {extracted_file}: {docx_err}")

                                                elif extracted_lower.endswith('.doc'):
                                                    # File .doc legacy - logga avviso
                                                    logger.warning(f"⚠️ File .doc in ZIP non supportato: {extracted_file}")

                                        # Pulisci directory estratta
                                        import shutil
                                        shutil.rmtree(extract_dir, ignore_errors=True)

                                    attachments.append({
                                        'filename': filename,
                                        'path': filepath
                                    })
                                    logger.info(f"📦 Processato ZIP {filename}")

                                except zipfile.BadZipFile:
                                    logger.warning(f"⚠️ File ZIP corrotto: {filename}")
                                except Exception as zip_err:
                                    logger.error(f"Errore elaborazione ZIP {filename}: {zip_err}")

                            elif filename.lower().endswith('.docx'):
                                # Per DOCX: estrai testo
                                with open(filepath, 'wb') as f:
                                    f.write(payload)

                                try:
                                    from docx import Document
                                    doc = Document(filepath)
                                    text = "\n".join([p.text for p in doc.paragraphs if p.text])
                                    if text.strip():
                                        allegati_testo[filename] = text.strip()
                                        logger.info(f"📄 Estratto testo da DOCX {filename}: {len(text)} caratteri")
                                except Exception as docx_err:
                                    logger.warning(f"Errore DOCX {filename}: {docx_err}")

                                attachments.append({
                                    'filename': filename,
                                    'path': filepath
                                })

                            else:
                                # Per altri allegati: salva normalmente
                                with open(filepath, 'wb') as f:
                                    f.write(payload)

                                attachments.append({
                                    'filename': filename,
                                    'path': filepath
                                })

                                logger.debug(f"Salvato allegato: {filename} (tipo: {content_type})")
                        else:
                            logger.warning(f"Allegato {filename} ha payload vuoto, saltato")
                    except Exception as e:
                        logger.error(f"Errore salvataggio allegato {filename}: {e}")

        return (attachments, allegati_testo)


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
    """Client per account PEC con gestione speciale delle buste EML"""

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

    def _extract_from_eml_envelope(self, eml_path: str) -> Dict:
        """
        Estrae dati dalla busta EML interna di una PEC.

        Args:
            eml_path: Path al file .eml salvato

        Returns:
            Dict con oggetto, mittente, corpo e allegati estratti dalla busta
        """
        try:
            with open(eml_path, 'rb') as f:
                content = f.read()

            # Il file .eml potrebbe avere un header wrapper (es. Content-Type: message/rfc822)
            # In quel caso, il messaggio vero inizia dopo la prima riga vuota
            inner_msg = email.message_from_bytes(content)

            # Se l'header 'Subject' è vuoto ma il content-type è message/rfc822,
            # il messaggio reale è nel payload
            if not inner_msg.get('Subject') and inner_msg.get_content_type() == 'message/rfc822':
                payload = inner_msg.get_payload(decode=True)
                if payload:
                    inner_msg = email.message_from_bytes(payload)
                else:
                    # Prova a splittare manualmente
                    parts = content.split(b'\n\n', 1)
                    if len(parts) > 1:
                        inner_msg = email.message_from_bytes(parts[1])

            # Estrai dati dalla busta interna
            inner_subject = self._decode_header(inner_msg.get('Subject', ''))
            inner_from = self._decode_header(inner_msg.get('From', ''))
            inner_to = self._decode_header(inner_msg.get('To', ''))
            inner_corpo_text, inner_corpo_html = self._extract_body(inner_msg)

            # Estrai allegati dalla busta interna
            # Generiamo un message_id temporaneo per salvare gli allegati
            import hashlib
            temp_id = hashlib.md5(eml_path.encode()).hexdigest()
            inner_attachments, inner_allegati_testo = self._extract_attachments(inner_msg, f"<inner-{temp_id}>")

            return {
                'oggetto': inner_subject,
                'mittente': inner_from,
                'destinatario': inner_to,
                'corpo': inner_corpo_text,
                'corpo_html': inner_corpo_html,
                'allegati': inner_attachments,
                'allegati_testo': inner_allegati_testo,
                'has_envelope': True
            }
        except Exception as e:
            logger.error(f"Errore estrazione dati da busta EML {eml_path}: {e}")
            return {'has_envelope': False}

    def fetch_emails(self, limit: int = 50) -> List[Dict]:
        """
        Override per PEC: estrae dati dalla busta EML interna.

        Le email PEC hanno questa struttura:
        - Email esterna (container PEC) con oggetto generico
        - Allegato postacert.eml (busta di trasporto)
        - Allegato messaggio.eml o daticert.xml.p7m (dati reali)

        Questa funzione estrae i dati VERI dalla busta interna.
        """
        # Prima ottieni le email con il metodo base
        emails_data = super().fetch_emails(limit)

        # Poi per ogni email PEC, cerca e processa la busta EML
        for email_data in emails_data:
            # Cerca file .eml negli allegati
            all_eml_attachments = [
                att_path for att_path in email_data.get('allegati_path', [])
                if att_path.endswith('.eml')
            ]

            # Prima prova a trovare EML che NON siano postacert.eml
            eml_attachments = [
                att_path for att_path in all_eml_attachments
                if 'postacert' not in att_path.lower()
            ]

            # Se non ci sono altri EML, usa postacert.eml (contiene comunque il messaggio)
            if not eml_attachments and all_eml_attachments:
                eml_attachments = all_eml_attachments
                logger.info("Usando postacert.eml come fonte del messaggio (nessun altro EML trovato)")

            if eml_attachments:
                # Usa il primo .eml trovato (dovrebbe essercene uno solo)
                eml_path = eml_attachments[0]
                logger.info(f"Trovata busta EML in email PEC: {eml_path}")

                # Estrai dati dalla busta
                envelope_data = self._extract_from_eml_envelope(eml_path)

                if envelope_data.get('has_envelope'):
                    # Sostituisci i dati dell'email esterna con quelli della busta
                    logger.info(f"Sostituzione dati PEC: '{email_data['oggetto']}' -> '{envelope_data['oggetto']}'")

                    email_data['oggetto'] = envelope_data['oggetto']
                    email_data['mittente'] = envelope_data['mittente']
                    email_data['destinatario'] = envelope_data.get('destinatario', email_data['destinatario'])
                    email_data['corpo'] = envelope_data['corpo']
                    email_data['corpo_html'] = envelope_data.get('corpo_html')

                    # Aggiungi gli allegati della busta a quelli esistenti
                    # (mantenendo anche postacert.eml e daticert.xml.p7m per tracciabilità)
                    inner_attachments = envelope_data.get('allegati', [])
                    inner_allegati_testo = envelope_data.get('allegati_testo', {})

                    # Ora inner_attachments include TUTTI i file (PDF + altri)
                    if inner_attachments:
                        email_data['allegati_nomi'].extend([att['filename'] for att in inner_attachments])
                        email_data['allegati_path'].extend([att['path'] for att in inner_attachments])

                    # Merge allegati_testo (solo testo estratto dai PDF)
                    if inner_allegati_testo:
                        if 'allegati_testo' in email_data:
                            email_data['allegati_testo'].update(inner_allegati_testo)
                        else:
                            email_data['allegati_testo'] = inner_allegati_testo

                    # Flag per indicare che questa email PEC è stata processata
                    email_data['pec_envelope_extracted'] = True

                    total_attachments = len(inner_attachments)
                    logger.info(f"Email PEC processata: {total_attachments} allegati reali estratti dalla busta")

        return emails_data
