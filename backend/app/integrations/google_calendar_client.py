"""
Google Calendar Client per gestione eventi calendario.

FASE 6: API Complete per Frontend
"""
import logging
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

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

        Supporta due modalità:
        1. Service Account (per applicazioni server)
        2. OAuth2 con token salvato (per test manuali)

        Returns:
            bool: True se autenticazione riuscita
        """
        try:
            from pathlib import Path
            import json
            from google.oauth2 import service_account

            creds = None
            credentials_path = settings.GOOGLE_CREDENTIALS_FILE

            if not credentials_path or credentials_path == "path/to/credentials.json":
                logger.error("❌ GOOGLE_CREDENTIALS_FILE non configurato")
                return False

            # Verifica se il file esiste
            if not Path(credentials_path).exists():
                logger.error(f"❌ File credentials non trovato: {credentials_path}")
                return False

            # Leggi il file per determinare il tipo
            with open(credentials_path, 'r') as f:
                cred_data = json.load(f)

            # Verifica se è un Service Account
            if cred_data.get('type') == 'service_account':
                logger.info("📝 Utilizzo Service Account per autenticazione")
                creds = service_account.Credentials.from_service_account_file(
                    credentials_path,
                    scopes=SCOPES
                )
                # Service Account non richiede validazione del token
            else:
                # OAuth2 - cerca token salvato
                token_path = credentials_path.replace('.json', '_token.json')

                if Path(token_path).exists():
                    try:
                        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
                        logger.info("📝 Token OAuth2 caricato")
                    except Exception as e:
                        logger.warning(f"Token non valido: {e}")

                # Refresh token se scaduto
                if creds and creds.expired and creds.refresh_token:
                    logger.info("🔄 Refresh token OAuth2...")
                    creds.refresh(Request())
                    # Salva token aggiornato
                    with open(token_path, 'w') as token:
                        token.write(creds.to_json())
                elif not creds or not creds.valid:
                    logger.error("❌ Autenticazione OAuth2 richiesta manualmente")
                    logger.error("💡 Per Service Account, usa un file con 'type': 'service_account'")
                    return False

            if not creds:
                return False

            self.credentials = creds
            self.service = build('calendar', 'v3', credentials=creds)
            logger.info("✅ Autenticazione Google Calendar riuscita")
            return True

        except Exception as e:
            logger.error(f"❌ Errore autenticazione Google Calendar: {e}")
            import traceback
            logger.error(traceback.format_exc())
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

            event_id = created_event.get('id')
            logger.info(f"✅ Evento creato: {summary} (ID: {event_id})")
            return event_id  # Ritorna solo l'ID, non il dict completo

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

    def sync_db_event_to_google(
        self,
        db_event,
        calendar_id: str = None
    ) -> Optional[str]:
        """
        Sincronizza un evento dal DB a Google Calendar.
        Se l'evento ha già un google_event_id, lo aggiorna.
        Altrimenti, crea un nuovo evento.

        Args:
            db_event: EventoCalendario dal database (modello SQLAlchemy)
            calendar_id: ID calendario (default da settings)

        Returns:
            str: Google Event ID se successo, None altrimenti
        """
        if not calendar_id:
            calendar_id = settings.GOOGLE_CALENDAR_ID

        if not self.service:
            if not self.authenticate():
                return None

        try:
            rome_tz = ZoneInfo('Europe/Rome')

            # Prepara datetime con timezone esplicito
            start_dt = db_event.data_inizio
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=rome_tz)

            # Calcola data fine - default 1h se non specificato o se end < start
            if db_event.data_fine:
                end_dt = db_event.data_fine
                if end_dt.tzinfo is None:
                    end_dt = end_dt.replace(tzinfo=rome_tz)
                # Se end < start (errore), usa start + 1h
                if end_dt <= start_dt:
                    logger.warning(f"⚠️ Evento {db_event.id}: data_fine ({end_dt}) <= data_inizio ({start_dt}), uso +1h")
                    end_dt = start_dt + timedelta(hours=1)
            else:
                end_dt = start_dt + timedelta(hours=1)

            # Costruisci evento Google
            event_body = {
                'summary': db_event.titolo,
                'start': {'dateTime': start_dt.isoformat(), 'timeZone': 'Europe/Rome'},
                'end': {'dateTime': end_dt.isoformat(), 'timeZone': 'Europe/Rome'},
            }

            if db_event.descrizione:
                event_body['description'] = db_event.descrizione

            if db_event.luogo:
                event_body['location'] = db_event.luogo

            # Se ha già un google_event_id, aggiorna
            if db_event.google_event_id:
                try:
                    updated = self.service.events().update(
                        calendarId=calendar_id,
                        eventId=db_event.google_event_id,
                        body=event_body
                    ).execute()
                    logger.info(f"✅ Evento Google aggiornato: {db_event.google_event_id}")
                    return updated.get('id')
                except HttpError as e:
                    if e.resp.status == 404:
                        # Evento non trovato, creane uno nuovo
                        logger.warning(f"⚠️ Evento Google {db_event.google_event_id} non trovato, creo nuovo")
                    else:
                        raise

            # Crea nuovo evento
            created = self.service.events().insert(
                calendarId=calendar_id,
                body=event_body
            ).execute()

            new_id = created.get('id')
            logger.info(f"✅ Evento Google creato: {new_id} (DB ID: {db_event.id})")
            return new_id

        except HttpError as e:
            logger.error(f"❌ Errore sync evento {db_event.id} a Google: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Errore generico sync evento {db_event.id}: {e}")
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
        end: Optional[str] = None,
        default_duration_hours: float = 1.0
    ) -> tuple:
        """
        Converte stringhe datetime in formato Google Calendar.

        Args:
            start: Data/ora inizio
            end: Data/ora fine (opzionale)
            default_duration_hours: Durata default in ore se end non specificato (default 1h)

        Returns:
            tuple: (start_dict, end_dict) per Google Calendar API
        """
        rome_tz = ZoneInfo('Europe/Rome')

        # Prova a parsare come datetime ISO
        try:
            start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
            # Se è timezone-naive, interpretalo come Europe/Rome
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=rome_tz)
            is_all_day = False
        except:
            # Prova come data semplice YYYY-MM-DD
            try:
                start_dt = datetime.strptime(start, '%Y-%m-%d')
                start_dt = start_dt.replace(tzinfo=rome_tz)
                is_all_day = True
            except:
                # Default: oggi in Europe/Rome timezone
                start_dt = datetime.now(rome_tz)
                is_all_day = False
                logger.warning(f"⚠️ Parsing datetime fallito per '{start}', uso datetime.now()")

        # Calcola end_dt
        if end:
            try:
                end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
                # Se è timezone-naive, interpretalo come Europe/Rome
                if end_dt.tzinfo is None:
                    end_dt = end_dt.replace(tzinfo=rome_tz)
            except:
                end_dt = start_dt + timedelta(hours=default_duration_hours)
        else:
            if is_all_day:
                end_dt = start_dt + timedelta(days=1)
            else:
                end_dt = start_dt + timedelta(hours=default_duration_hours)

        # Formato per Google Calendar - usa formato con offset esplicito
        if is_all_day:
            start_dict = {'date': start_dt.strftime('%Y-%m-%d')}
            end_dict = {'date': end_dt.strftime('%Y-%m-%d')}
        else:
            # Usa isoformat che include l'offset timezone (+01:00 o +02:00)
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

    def share_calendar(
        self,
        email: str,
        role: str = 'reader',
        calendar_id: str = 'primary'
    ) -> bool:
        """
        Condivide il calendario con un utente.

        Args:
            email: Email dell'utente con cui condividere
            role: Ruolo ('reader', 'writer', 'owner')
            calendar_id: ID calendario (default: primary)

        Returns:
            bool: True se condivisione riuscita
        """
        if not self.service:
            if not self.authenticate():
                return False

        try:
            rule = {
                'scope': {
                    'type': 'user',
                    'value': email
                },
                'role': role
            }

            created_rule = self.service.acl().insert(
                calendarId=calendar_id,
                body=rule
            ).execute()

            logger.info(f"✅ Calendario condiviso con {email} (ruolo: {role})")
            return True

        except HttpError as e:
            logger.error(f"❌ Errore condivisione calendario: {e}")
            return False
