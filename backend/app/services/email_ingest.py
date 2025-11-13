"""
Email Ingest Service (stub)
"""

import logging

logger = logging.getLogger(__name__)


class EmailNormalClient:
    """Client per gestione email normale (SMTP/IMAP)"""

    def send_email(self, to: str, subject: str, body: str):
        """
        Invia email via SMTP

        Args:
            to: Destinatario
            subject: Oggetto
            body: Corpo email
        """
        logger.info(f"Invio email a {to}: {subject}")
        # TODO: Implementare invio SMTP reale
        pass
