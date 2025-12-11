"""
Servizio per eliminare email dal server IMAP.
"""
import logging
import os
from typing import Optional
from imaplib import IMAP4_SSL
from sqlalchemy.orm import Session

from app.models.email import Email
from app.config import get_settings

settings = get_settings()

logger = logging.getLogger(__name__)


class EmailDeletionService:
    """Servizio per eliminare email dal server IMAP."""

    def __init__(self, db: Session):
        self.db = db

    def _derive_imap_from_pop3(self, pop_host: str) -> str:
        """
        Deriva il server IMAP dal server POP3.

        Gestisce vari formati:
        - pop3s.pec.aruba.it -> imaps.pec.aruba.it
        - pop.example.com -> imap.example.com
        - pop3.example.com -> imap.example.com
        - mail.truemail.it -> imap.truemail.it (sostituisce mail. con imap.)
        """
        if not pop_host:
            return pop_host

        # Normalizza a lowercase per il matching
        host_lower = pop_host.lower()

        # Mappatura specifica per provider noti
        # TrueMail usa lo stesso server per POP3 e IMAP
        imap_mappings = {
            'pop3s.pec.aruba.it': 'imaps.pec.aruba.it',
            'pop.pec.aruba.it': 'imap.pec.aruba.it',
            'mail.truemail.it': 'mail.truemail.it',  # Stesso server per POP3 e IMAP
        }

        if host_lower in imap_mappings:
            return imap_mappings[host_lower]

        # Derivazione generica
        if host_lower.startswith('pop3s.'):
            return pop_host.replace('pop3s.', 'imaps.', 1)
        elif host_lower.startswith('pop3.'):
            return pop_host.replace('pop3.', 'imap.', 1)
        elif host_lower.startswith('pop.'):
            return pop_host.replace('pop.', 'imap.', 1)
        elif host_lower.startswith('mail.'):
            return pop_host.replace('mail.', 'imap.', 1)

        # Fallback: prependi imap.
        return f"imap.{pop_host}"

    def delete_from_server(self, email: Email) -> bool:
        """
        Elimina email dal server IMAP.

        Args:
            email: Email da eliminare

        Returns:
            bool: True se eliminazione riuscita, False altrimenti
        """
        if not email.message_id:
            logger.warning(f"Email {email.id} non ha message_id, impossibile eliminare dal server")
            return False

        # Determina account da cui eliminare
        # Usa le stesse credenziali POP3 ma con server IMAP (stesso provider, stesso account)
        if email.account_type == 'pec':
            # Per PEC Aruba: pop3s.pec.aruba.it -> imaps.pec.aruba.it
            pop_host = settings.EMAIL_PEC_POP3_HOST
            imap_server = self._derive_imap_from_pop3(pop_host)
            imap_user = settings.EMAIL_PEC_POP3_USER
            imap_password = settings.EMAIL_PEC_POP3_PASSWORD
        else:
            # Per email normale: mail.truemail.it -> imap.truemail.it
            pop_host = settings.EMAIL_NORMAL_POP3_HOST
            imap_server = self._derive_imap_from_pop3(pop_host)
            imap_user = settings.EMAIL_NORMAL_POP3_USER
            imap_password = settings.EMAIL_NORMAL_POP3_PASSWORD

        # Fallback: usa WEBMAIL_IMAP se configurato
        if not imap_user or not imap_password:
            imap_server = settings.WEBMAIL_IMAP_HOST
            imap_port = settings.WEBMAIL_IMAP_PORT
            imap_user = settings.WEBMAIL_IMAP_USER
            imap_password = settings.WEBMAIL_IMAP_PASSWORD
        else:
            imap_port = 993  # Porta standard IMAP SSL

        if not imap_user or not imap_password:
            logger.error(f"❌ Credenziali IMAP non configurate per eliminare email {email.id}")
            return False

        try:
            # Connessione IMAP
            logger.info(f"📧 Connessione a {imap_server}:{imap_port} per eliminare email {email.id} (account: {email.account_type})")
            mail = IMAP4_SSL(imap_server, imap_port)
            mail.login(imap_user, imap_password)
            logger.info(f"✅ Login IMAP riuscito come {imap_user}")

            # Seleziona INBOX
            mail.select('INBOX')

            # Cerca email per Message-ID
            message_id_clean = email.message_id.strip().strip('<>')
            search_criteria = f'HEADER Message-ID "{message_id_clean}"'

            logger.info(f"🔍 Ricerca email con Message-ID: {message_id_clean}")
            status, messages = mail.search(None, search_criteria)

            if status != 'OK':
                logger.error(f"❌ Errore nella ricerca: {status}")
                mail.logout()
                return False

            message_ids = messages[0].split()

            if not message_ids:
                logger.warning(f"⚠️ Email non trovata sul server con Message-ID: {message_id_clean}")
                mail.logout()
                return False

            # Elimina tutte le occorrenze trovate
            deleted_count = 0
            for msg_id in message_ids:
                # Marca come eliminata
                mail.store(msg_id, '+FLAGS', '\\Deleted')
                deleted_count += 1
                logger.info(f"🗑️ Email {msg_id.decode()} marcata per eliminazione")

            # Espunge (elimina definitivamente)
            mail.expunge()
            mail.logout()

            logger.info(f"✅ {deleted_count} email eliminate dal server per email {email.id}")
            return True

        except Exception as e:
            logger.error(f"❌ Errore eliminazione email {email.id} dal server: {e}", exc_info=True)
            return False

    def delete_multiple_from_server(self, emails: list[Email]) -> dict:
        """
        Elimina multiple email dal server.

        Args:
            emails: Lista di email da eliminare

        Returns:
            dict: Statistiche eliminazione
        """
        results = {
            'total': len(emails),
            'success': 0,
            'failed': 0,
            'errors': []
        }

        for email in emails:
            try:
                if self.delete_from_server(email):
                    results['success'] += 1
                else:
                    results['failed'] += 1
                    results['errors'].append({
                        'email_id': email.id,
                        'error': 'Eliminazione fallita'
                    })
            except Exception as e:
                results['failed'] += 1
                results['errors'].append({
                    'email_id': email.id,
                    'error': str(e)
                })

        logger.info(
            f"📊 Eliminazione multipla completata: "
            f"{results['success']}/{results['total']} successi, "
            f"{results['failed']} fallimenti"
        )

        return results


def get_deletion_service(db: Session) -> EmailDeletionService:
    """Factory per EmailDeletionService."""
    return EmailDeletionService(db)
