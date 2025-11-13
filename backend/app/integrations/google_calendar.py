"""
Client Google Calendar
"""

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os
import pickle
import logging
from typing import Optional, Dict
from datetime import datetime

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

SCOPES = ['https://www.googleapis.com/auth/calendar']


class GoogleCalendarClient:
    """Client Google Calendar"""

    def __init__(self):
        self.creds = None
        self.service = None
        self._authenticate()

    def _authenticate(self):
        """Autenticazione OAuth2 (condivide token con Drive)"""

        token_file = settings.GOOGLE_TOKEN_FILE
        creds_file = settings.GOOGLE_CREDENTIALS_FILE

        if os.path.exists(token_file):
            with open(token_file, 'rb') as token:
                self.creds = pickle.load(token)

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                if not os.path.exists(creds_file):
                    raise FileNotFoundError(f"Credenziali non trovate: {creds_file}")

                flow = InstalledAppFlow.from_client_secrets_file(creds_file, SCOPES)
                self.creds = flow.run_local_server(port=0)

            with open(token_file, 'wb') as token:
                pickle.dump(self.creds, token)

        self.service = build('calendar', 'v3', credentials=self.creds)
        logger.info("Autenticato su Google Calendar")

    def create_event(self, summary: str, description: str,
                    start_datetime: datetime, end_datetime: datetime,
                    location: Optional[str] = None,
                    attendees: Optional[list] = None) -> Optional[str]:
        """
        Crea evento su Google Calendar

        Returns:
            Event ID se successo
        """
        try:
            event = {
                'summary': summary,
                'description': description,
                'start': {
                    'dateTime': start_datetime.isoformat(),
                    'timeZone': 'Europe/Rome',
                },
                'end': {
                    'dateTime': end_datetime.isoformat(),
                    'timeZone': 'Europe/Rome',
                },
            }

            if location:
                event['location'] = location

            if attendees:
                event['attendees'] = [{'email': email} for email in attendees]

            result = self.service.events().insert(
                calendarId=settings.GOOGLE_CALENDAR_ID,
                body=event
            ).execute()

            event_id = result['id']
            logger.info(f"Evento creato: {summary} (ID: {event_id})")
            return event_id

        except Exception as e:
            logger.error(f"Errore creazione evento: {e}")
            return None

    def update_event(self, event_id: str, **kwargs) -> bool:
        """Aggiorna evento esistente"""
        try:
            event = self.service.events().get(
                calendarId=settings.GOOGLE_CALENDAR_ID,
                eventId=event_id
            ).execute()

            # Aggiorna campi
            for key, value in kwargs.items():
                event[key] = value

            self.service.events().update(
                calendarId=settings.GOOGLE_CALENDAR_ID,
                eventId=event_id,
                body=event
            ).execute()

            logger.info(f"Evento aggiornato: {event_id}")
            return True

        except Exception as e:
            logger.error(f"Errore aggiornamento evento: {e}")
            return False

    def delete_event(self, event_id: str) -> bool:
        """Elimina evento"""
        try:
            self.service.events().delete(
                calendarId=settings.GOOGLE_CALENDAR_ID,
                eventId=event_id
            ).execute()

            logger.info(f"Evento eliminato: {event_id}")
            return True

        except Exception as e:
            logger.error(f"Errore eliminazione evento: {e}")
            return False
