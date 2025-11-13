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
