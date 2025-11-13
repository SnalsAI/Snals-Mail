"""
Google Calendar Client per gestione eventi calendario.

FASE 6: API Complete per Frontend
"""
import logging
from typing import Optional, List, Dict
from datetime import datetime, timedelta

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Scopes necessari per Google Calendar
SCOPES = ['https://www.googleapis.com/auth/calendar']


class GoogleCalendarClient:
    """Client per interagire con Google Calendar API."""

    def __init__(self):
        """Inizializza il client Google Calendar."""
        self.credentials = None
        self.service = None

    def authenticate(self) -> bool:
        """
        Autentica con Google Calendar usando OAuth2.

        Returns:
            bool: True se autenticazione riuscita
        """
        try:
            creds = None

            # Carica credenziali salvate se esistono
            if settings.GOOGLE_CREDENTIALS_FILE and settings.GOOGLE_CREDENTIALS_FILE != "path/to/credentials.json":
                try:
                    creds = Credentials.from_authorized_user_file(
                        settings.GOOGLE_CREDENTIALS_FILE, SCOPES
                    )
                except Exception as e:
                    logger.warning(f"Impossibile caricare credenziali salvate: {e}")

            # Se non ci sono credenziali valide, richiedi autenticazione
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    logger.warning("Autenticazione Google Calendar richiesta ma non disponibile in modalità automatica")
                    return False

                # Salva credenziali per la prossima volta
                if settings.GOOGLE_CREDENTIALS_FILE:
                    with open(settings.GOOGLE_CREDENTIALS_FILE, 'w') as token:
                        token.write(creds.to_json())

            self.credentials = creds
            self.service = build('calendar', 'v3', credentials=creds)
            logger.info("✅ Autenticazione Google Calendar riuscita")
            return True

        except Exception as e:
            logger.error(f"❌ Errore autenticazione Google Calendar: {e}")
            return False

    def create_event(
        self,
        summary: str,
        start_datetime: str,
        end_datetime: Optional[str] = None,
        location: Optional[str] = None,
        description: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        calendar_id: str = 'primary'
    ) -> Optional[Dict]:
        """
        Crea un nuovo evento su Google Calendar.

        Args:
            summary: Titolo evento
            start_datetime: Data/ora inizio (ISO format o YYYY-MM-DD)
            end_datetime: Data/ora fine (opzionale, default +1h)
            location: Luogo evento
            description: Descrizione
            attendees: Lista email partecipanti
            calendar_id: ID calendario (default: primary)

        Returns:
            Dict: Evento creato
        """
        if not self.service:
            if not self.authenticate():
                return None

        try:
            # Prepara date/ore
            start_dt, end_dt = self._parse_datetime(start_datetime, end_datetime)

            # Costruisci evento
            event = {
                'summary': summary,
                'start': start_dt,
                'end': end_dt,
            }

            if location:
                event['location'] = location

            if description:
                event['description'] = description

            if attendees:
                event['attendees'] = [{'email': email} for email in attendees]

            # Crea evento
            created_event = self.service.events().insert(
                calendarId=calendar_id,
                body=event,
                sendUpdates='all' if attendees else 'none'
            ).execute()

            logger.info(f"✅ Evento creato: {summary} ({created_event.get('id')})")
            return created_event

        except HttpError as e:
            logger.error(f"❌ Errore creazione evento: {e}")
            return None

    def list_events(
        self,
        max_results: int = 10,
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None,
        calendar_id: str = 'primary'
    ) -> List[Dict]:
        """
        Lista eventi da Google Calendar.

        Args:
            max_results: Numero massimo eventi
            time_min: Data inizio ricerca
            time_max: Data fine ricerca
            calendar_id: ID calendario

        Returns:
            List[Dict]: Lista eventi
        """
        if not self.service:
            if not self.authenticate():
                return []

        try:
            # Default: eventi da oggi in poi
            if not time_min:
                time_min = datetime.now()

            time_min_iso = time_min.isoformat() + 'Z'
            time_max_iso = time_max.isoformat() + 'Z' if time_max else None

            # Recupera eventi
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=time_min_iso,
                timeMax=time_max_iso,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])
            logger.info(f"✅ Recuperati {len(events)} eventi")
            return events

        except HttpError as e:
            logger.error(f"❌ Errore recupero eventi: {e}")
            return []

    def update_event(
        self,
        event_id: str,
        updates: Dict,
        calendar_id: str = 'primary'
    ) -> Optional[Dict]:
        """
        Aggiorna un evento esistente.

        Args:
            event_id: ID evento da aggiornare
            updates: Dict con campi da aggiornare
            calendar_id: ID calendario

        Returns:
            Dict: Evento aggiornato
        """
        if not self.service:
            if not self.authenticate():
                return None

        try:
            # Recupera evento corrente
            event = self.service.events().get(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()

            # Applica modifiche
            for key, value in updates.items():
                event[key] = value

            # Aggiorna evento
            updated_event = self.service.events().update(
                calendarId=calendar_id,
                eventId=event_id,
                body=event
            ).execute()

            logger.info(f"✅ Evento aggiornato: {event_id}")
            return updated_event

        except HttpError as e:
            logger.error(f"❌ Errore aggiornamento evento: {e}")
            return None

    def delete_event(
        self,
        event_id: str,
        calendar_id: str = 'primary'
    ) -> bool:
        """
        Elimina un evento.

        Args:
            event_id: ID evento da eliminare
            calendar_id: ID calendario

        Returns:
            bool: True se eliminato con successo
        """
        if not self.service:
            if not self.authenticate():
                return False

        try:
            self.service.events().delete(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()

            logger.info(f"✅ Evento eliminato: {event_id}")
            return True

        except HttpError as e:
            logger.error(f"❌ Errore eliminazione evento: {e}")
            return False

    def _parse_datetime(
        self,
        start: str,
        end: Optional[str] = None
    ) -> tuple:
        """
        Converte stringhe datetime in formato Google Calendar.

        Args:
            start: Data/ora inizio
            end: Data/ora fine (opzionale)

        Returns:
            tuple: (start_dict, end_dict) per Google Calendar API
        """
        # Prova a parsare come datetime ISO
        try:
            start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
            is_all_day = False
        except:
            # Prova come data semplice YYYY-MM-DD
            try:
                start_dt = datetime.strptime(start, '%Y-%m-%d')
                is_all_day = True
            except:
                # Default: oggi
                start_dt = datetime.now()
                is_all_day = False

        # Calcola end_dt
        if end:
            try:
                end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
            except:
                end_dt = start_dt + timedelta(hours=1)
        else:
            if is_all_day:
                end_dt = start_dt + timedelta(days=1)
            else:
                end_dt = start_dt + timedelta(hours=1)

        # Formato per Google Calendar
        if is_all_day:
            start_dict = {'date': start_dt.strftime('%Y-%m-%d')}
            end_dict = {'date': end_dt.strftime('%Y-%m-%d')}
        else:
            start_dict = {'dateTime': start_dt.isoformat(), 'timeZone': 'Europe/Rome'}
            end_dict = {'dateTime': end_dt.isoformat(), 'timeZone': 'Europe/Rome'}

        return start_dict, end_dict

    def get_calendar_list(self) -> List[Dict]:
        """
        Lista tutti i calendari disponibili.

        Returns:
            List[Dict]: Lista calendari
        """
        if not self.service:
            if not self.authenticate():
                return []

        try:
            calendar_list = self.service.calendarList().list().execute()
            calendars = calendar_list.get('items', [])

            logger.info(f"✅ Recuperati {len(calendars)} calendari")
            return calendars

        except HttpError as e:
            logger.error(f"❌ Errore recupero calendari: {e}")
            return []
