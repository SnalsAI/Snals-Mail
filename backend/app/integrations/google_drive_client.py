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
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Scopes necessari per Google Drive
# drive.file: Solo file creati dall'app (limitato)
# drive: Accesso completo inclusi Shared Drives
SCOPES = ['https://www.googleapis.com/auth/drive']


class GoogleDriveClient:
    """Client per interagire con Google Drive API."""

    def __init__(self):
        """Inizializza il client Google Drive."""
        self.credentials = None
        self.service = None

    def authenticate(self) -> bool:
        """
        Autentica con Google Drive usando OAuth2.

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
            self.service = build('drive', 'v3', credentials=creds)
            logger.info("✅ Autenticazione Google Drive riuscita")
            return True

        except Exception as e:
            logger.error(f"❌ Errore autenticazione Google Drive: {e}")
            import traceback
            logger.error(traceback.format_exc())
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
                fields='id',
                supportsAllDrives=True
            ).execute()

            folder_id = folder.get('id')
            logger.info(f"✅ Cartella creata: {folder_name} (ID: {folder_id})")

            # Condividi automaticamente con l'utente configurato
            share_email = settings.GOOGLE_DRIVE_SHARE_EMAIL
            if share_email and share_email != "":
                self.share_with_user(folder_id, share_email, role='writer')

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
                fields='id, name, webViewLink, mimeType, size',
                supportsAllDrives=True
            ).execute()

            logger.info(f"✅ File caricato: {filename} (ID: {file.get('id')})")

            # Condividi automaticamente con l'utente configurato
            share_email = settings.GOOGLE_DRIVE_SHARE_EMAIL
            if share_email and share_email != "":
                self.share_with_user(file.get('id'), share_email, role='writer')

            return file

        except HttpError as e:
            logger.error(f"❌ Errore upload file: {e}")
            return None

    def download_file(self, file_id: str) -> Optional[bytes]:
        """
        Scarica un file da Google Drive.

        Args:
            file_id: ID del file da scaricare

        Returns:
            bytes: Contenuto del file
        """
        if not self.service:
            if not self.authenticate():
                return None

        try:
            request = self.service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)

            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    logger.info(f"📥 Download progress: {int(status.progress() * 100)}%")

            content = fh.getvalue()
            logger.info(f"✅ File scaricato: {len(content)} bytes")
            return content

        except HttpError as e:
            logger.error(f"❌ Errore download file: {e}")
            return None

    def upload_attachments(
        self,
        attachments: List[tuple],
        email_subject: str,
        base_folder_id: Optional[str] = None,
        categoria: Optional[str] = None,
        sottocategoria: Optional[str] = None
    ) -> List[Dict]:
        """
        Carica tutti gli allegati di una email su Drive.

        Struttura cartelle: Base/Categoria/Sottocategoria/YYYYMMDD_Oggetto/

        Args:
            attachments: Lista di tuple (filename, content, mimetype)
            email_subject: Oggetto email (per nome cartella)
            base_folder_id: ID cartella base (opzionale)
            categoria: Categoria email (opzionale)
            sottocategoria: Sottocategoria email (opzionale)

        Returns:
            Lista di dict con info file caricati
        """
        if not attachments:
            return []

        # Determina la cartella parent basata su categoria/sottocategoria
        parent_folder_id = base_folder_id

        if categoria:
            # Usa struttura categoria/sottocategoria
            category_folder_id = self.get_or_create_category_folder(
                categoria=categoria,
                sottocategoria=sottocategoria,
                base_folder_id=base_folder_id
            )
            if category_folder_id:
                parent_folder_id = category_folder_id
            else:
                logger.warning(f"⚠️ Impossibile creare cartella categoria, uso base folder")

        # Crea cartella per questa email specifica
        folder_name = f"{datetime.now().strftime('%Y%m%d')}_{email_subject[:50]}"
        folder_id = self.create_folder(folder_name, parent_folder_id)

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
                fields='files(id, name)',
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
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

    def get_or_create_category_folder(
        self,
        categoria: str,
        sottocategoria: Optional[str] = None,
        base_folder_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Ottieni o crea cartella per categoria/sottocategoria.

        Struttura: Base/Categoria/Sottocategoria/

        Args:
            categoria: Nome categoria (es. "COMUNICAZIONE_UST_USR")
            sottocategoria: Nome sottocategoria opzionale (es. "Interpello")
            base_folder_id: ID cartella base (opzionale)

        Returns:
            str: ID della cartella categoria/sottocategoria
        """
        if not self.service:
            if not self.authenticate():
                return None

        try:
            # Usa base folder se fornito, altrimenti ottieni/crea il principale
            if not base_folder_id:
                base_folder_id = self.get_or_create_base_folder()
                if not base_folder_id:
                    return None

            # Cerca/crea cartella categoria
            categoria_clean = categoria.replace('_', ' ').title()
            categoria_folder_id = self._find_or_create_subfolder(
                folder_name=categoria_clean,
                parent_id=base_folder_id
            )

            if not categoria_folder_id:
                return None

            # Se c'è sottocategoria, cerca/crea anche quella
            if sottocategoria:
                sottocategoria_clean = sottocategoria.replace('_', ' ').title()
                sottocategoria_folder_id = self._find_or_create_subfolder(
                    folder_name=sottocategoria_clean,
                    parent_id=categoria_folder_id
                )
                return sottocategoria_folder_id

            return categoria_folder_id

        except Exception as e:
            logger.error(f"❌ Errore creazione cartella categoria: {e}")
            return None

    def _find_or_create_subfolder(self, folder_name: str, parent_id: str) -> Optional[str]:
        """
        Cerca una sottocartella, se non esiste la crea.

        Args:
            folder_name: Nome cartella da cercare/creare
            parent_id: ID cartella parent

        Returns:
            str: ID della cartella trovata/creata
        """
        if not self.service:
            return None

        try:
            # Cerca cartella esistente
            query = f"name='{folder_name}' and '{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
            response = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)',
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()

            files = response.get('files', [])

            if files:
                folder_id = files[0]['id']
                logger.info(f"✅ Cartella trovata: {folder_name} (ID: {folder_id})")
                return folder_id
            else:
                # Crea nuova cartella
                folder_id = self.create_folder(folder_name, parent_id)
                logger.info(f"✅ Cartella creata: {folder_name} (ID: {folder_id})")
                return folder_id

        except HttpError as e:
            logger.error(f"❌ Errore ricerca/creazione sottocartella {folder_name}: {e}")
            return None

    def share_with_user(self, file_id: str, email: str, role: str = 'writer') -> bool:
        """
        Condividi un file o cartella con un utente specifico.

        Args:
            file_id: ID del file/cartella da condividere
            email: Email dell'utente con cui condividere
            role: Ruolo ('reader', 'writer', 'owner')

        Returns:
            bool: True se condivisione riuscita
        """
        if not self.service:
            if not self.authenticate():
                return False

        try:
            permission = {
                'type': 'user',
                'role': role,
                'emailAddress': email
            }

            self.service.permissions().create(
                fileId=file_id,
                body=permission,
                fields='id',
                sendNotificationEmail=False,  # Non inviare email di notifica
                supportsAllDrives=True
            ).execute()

            logger.info(f"✅ File/cartella {file_id} condiviso con {email} ({role})")
            return True

        except HttpError as e:
            logger.error(f"❌ Errore condivisione con {email}: {e}")
            return False
