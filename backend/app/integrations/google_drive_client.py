"""
Google Drive Client per upload automatico allegati.

FASE 4: Azioni Automatiche
"""
import io
import logging
from typing import Optional, List, Dict
from datetime import datetime

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.errors import HttpError

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Scopes necessari per Google Drive
SCOPES = ['https://www.googleapis.com/auth/drive.file']


class GoogleDriveClient:
    """Client per interagire con Google Drive API."""

    def __init__(self):
        """Inizializza il client Google Drive."""
        self.credentials = None
        self.service = None

    def authenticate(self) -> bool:
        """
        Autentica con Google Drive usando OAuth2.

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
                    # In produzione, questo dovrebbe essere gestito diversamente
                    # (es. salvare token in database, usare service account, ecc.)
                    logger.warning("Autenticazione Google Drive richiesta ma non disponibile in modalità automatica")
                    return False

                # Salva credenziali per la prossima volta
                if settings.GOOGLE_CREDENTIALS_FILE:
                    with open(settings.GOOGLE_CREDENTIALS_FILE, 'w') as token:
                        token.write(creds.to_json())

            self.credentials = creds
            self.service = build('drive', 'v3', credentials=creds)
            logger.info("✅ Autenticazione Google Drive riuscita")
            return True

        except Exception as e:
            logger.error(f"❌ Errore autenticazione Google Drive: {e}")
            return False

    def create_folder(self, folder_name: str, parent_folder_id: Optional[str] = None) -> Optional[str]:
        """
        Crea una cartella su Google Drive.

        Args:
            folder_name: Nome della cartella
            parent_folder_id: ID cartella parent (opzionale)

        Returns:
            str: ID della cartella creata
        """
        if not self.service:
            if not self.authenticate():
                return None

        try:
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }

            if parent_folder_id:
                file_metadata['parents'] = [parent_folder_id]

            folder = self.service.files().create(
                body=file_metadata,
                fields='id'
            ).execute()

            folder_id = folder.get('id')
            logger.info(f"✅ Cartella creata: {folder_name} (ID: {folder_id})")
            return folder_id

        except HttpError as e:
            logger.error(f"❌ Errore creazione cartella: {e}")
            return None

    def upload_file(
        self,
        file_content: bytes,
        filename: str,
        mimetype: str,
        folder_id: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Carica un file su Google Drive.

        Args:
            file_content: Contenuto del file in bytes
            filename: Nome del file
            mimetype: MIME type del file
            folder_id: ID cartella destinazione (opzionale)

        Returns:
            Dict con info file caricato (id, name, webViewLink)
        """
        if not self.service:
            if not self.authenticate():
                return None

        try:
            file_metadata = {'name': filename}

            if folder_id:
                file_metadata['parents'] = [folder_id]

            media = MediaIoBaseUpload(
                io.BytesIO(file_content),
                mimetype=mimetype,
                resumable=True
            )

            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, webViewLink, mimeType, size'
            ).execute()

            logger.info(f"✅ File caricato: {filename} (ID: {file.get('id')})")
            return file

        except HttpError as e:
            logger.error(f"❌ Errore upload file: {e}")
            return None

    def upload_attachments(
        self,
        attachments: List[tuple],
        email_subject: str,
        base_folder_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Carica tutti gli allegati di una email su Drive.

        Args:
            attachments: Lista di tuple (filename, content, mimetype)
            email_subject: Oggetto email (per nome cartella)
            base_folder_id: ID cartella base (opzionale)

        Returns:
            Lista di dict con info file caricati
        """
        if not attachments:
            return []

        # Crea cartella per questa email
        folder_name = f"{datetime.now().strftime('%Y%m%d')}_{email_subject[:50]}"
        folder_id = self.create_folder(folder_name, base_folder_id)

        if not folder_id:
            logger.error("Impossibile creare cartella per allegati")
            return []

        uploaded_files = []
        for filename, content, mimetype in attachments:
            file_info = self.upload_file(content, filename, mimetype, folder_id)
            if file_info:
                uploaded_files.append(file_info)

        logger.info(f"✅ Caricati {len(uploaded_files)}/{len(attachments)} allegati")
        return uploaded_files

    def get_or_create_base_folder(self, folder_name: str = "SNALS Email Attachments") -> Optional[str]:
        """
        Ottieni o crea la cartella base per gli allegati.

        Args:
            folder_name: Nome cartella base

        Returns:
            str: ID cartella base
        """
        if not self.service:
            if not self.authenticate():
                return None

        try:
            # Cerca cartella esistente
            response = self.service.files().list(
                q=f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
                spaces='drive',
                fields='files(id, name)'
            ).execute()

            files = response.get('files', [])

            if files:
                folder_id = files[0]['id']
                logger.info(f"✅ Cartella base trovata: {folder_name} (ID: {folder_id})")
                return folder_id
            else:
                # Crea nuova cartella
                return self.create_folder(folder_name)

        except HttpError as e:
            logger.error(f"❌ Errore ricerca cartella: {e}")
            return None
