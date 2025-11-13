"""
Client Google Drive per upload allegati
"""

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import os
import pickle
import logging
from typing import Optional, Dict

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Scopes necessari
SCOPES = ['https://www.googleapis.com/auth/drive.file']


class GoogleDriveClient:
    """Client Google Drive"""

    def __init__(self):
        self.creds = None
        self.service = None
        self._authenticate()

    def _authenticate(self):
        """Autenticazione OAuth2"""

        token_file = settings.GOOGLE_TOKEN_FILE
        creds_file = settings.GOOGLE_CREDENTIALS_FILE

        # Carica token se esiste
        if os.path.exists(token_file):
            with open(token_file, 'rb') as token:
                self.creds = pickle.load(token)

        # Se non valido, refresh o new auth
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                # Nuova autenticazione (richiede interazione utente)
                if not os.path.exists(creds_file):
                    logger.error(f"File credenziali non trovato: {creds_file}")
                    raise FileNotFoundError(f"Credenziali Google non trovate: {creds_file}")

                flow = InstalledAppFlow.from_client_secrets_file(creds_file, SCOPES)
                self.creds = flow.run_local_server(port=0)

            # Salva token
            with open(token_file, 'wb') as token:
                pickle.dump(self.creds, token)

        # Build service
        self.service = build('drive', 'v3', credentials=self.creds)
        logger.info("Autenticato su Google Drive")

    def get_or_create_folder(self, folder_path: str) -> str:
        """
        Ottieni o crea cartella (path gerarchico)

        Args:
            folder_path: Path tipo "UST_USR/2024/11"

        Returns:
            ID cartella
        """
        parts = folder_path.split('/')
        parent_id = 'root'

        for part in parts:
            # Cerca cartella
            query = f"name='{part}' and '{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)'
            ).execute()

            folders = results.get('files', [])

            if folders:
                parent_id = folders[0]['id']
            else:
                # Crea cartella
                folder_metadata = {
                    'name': part,
                    'mimeType': 'application/vnd.google-apps.folder',
                    'parents': [parent_id]
                }
                folder = self.service.files().create(
                    body=folder_metadata,
                    fields='id'
                ).execute()
                parent_id = folder['id']
                logger.info(f"Creata cartella: {part}")

        return parent_id

    def upload_file(self, filepath: str, folder_path: str,
                   metadata: Optional[Dict] = None) -> Optional[str]:
        """
        Upload file su Drive

        Args:
            filepath: Path locale file
            folder_path: Path cartella destinazione
            metadata: Metadati aggiuntivi

        Returns:
            ID file uploadato o None se errore
        """
        try:
            if not os.path.exists(filepath):
                logger.error(f"File non trovato: {filepath}")
                return None

            # Ottieni folder ID
            folder_id = self.get_or_create_folder(folder_path)

            # Metadati file
            filename = os.path.basename(filepath)
            file_metadata = {
                'name': filename,
                'parents': [folder_id]
            }

            # Aggiungi metadati custom (come properties)
            if metadata:
                file_metadata['properties'] = metadata

            # Media
            media = MediaFileUpload(filepath, resumable=True)

            # Upload
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink'
            ).execute()

            file_id = file.get('id')
            web_link = file.get('webViewLink')

            logger.info(f"File uploadato: {filename} (ID: {file_id})")
            return file_id

        except Exception as e:
            logger.error(f"Errore upload file {filepath}: {e}")
            return None

    def share_file(self, file_id: str, email: str, role: str = 'reader'):
        """
        Condividi file con utente

        Args:
            file_id: ID file
            email: Email utente
            role: reader/writer/commenter
        """
        try:
            permission = {
                'type': 'user',
                'role': role,
                'emailAddress': email
            }

            self.service.permissions().create(
                fileId=file_id,
                body=permission,
                sendNotificationEmail=False
            ).execute()

            logger.info(f"File {file_id} condiviso con {email}")

        except Exception as e:
            logger.error(f"Errore condivisione file: {e}")
