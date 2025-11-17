"""
API Routes per gestione Settings e Test Connessioni Email.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional
import os
from pathlib import Path

from app.services.email_ingest import EmailNormalClient, EmailPECClient
from app.config import get_settings

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsResponse(BaseModel):
    """Response con tutte le configurazioni"""
    # Email Normal
    email_normal_pop3_host: str
    email_normal_pop3_port: int
    email_normal_pop3_user: str
    email_normal_pop3_password: str
    email_normal_smtp_host: str
    email_normal_smtp_port: int
    email_normal_smtp_user: str
    email_normal_smtp_password: str

    # Email PEC
    email_pec_pop3_host: str
    email_pec_pop3_port: int
    email_pec_pop3_user: str
    email_pec_pop3_password: str
    email_pec_smtp_host: str
    email_pec_smtp_port: int
    email_pec_smtp_user: str
    email_pec_smtp_password: str

    # LLM
    llm_provider: str
    ollama_base_url: str
    ollama_model_categorization: str
    ollama_model_interpretation: str
    ollama_model_generation: str
    openai_api_key: str
    openai_model: str

    # Google
    google_credentials_file: str
    google_calendar_id: str
    google_drive_folder_ust: str
    google_drive_folder_snals: str

    # System
    email_poll_interval: int
    daily_summary_hour: int
    email_mark_as_read: bool
    email_delete_from_server: bool
    email_fetch_limit: int
    debug: bool
    log_level: str


class SettingsUpdateRequest(BaseModel):
    """Request per aggiornamento configurazioni"""
    # Tutti i campi sono opzionali per permettere aggiornamenti parziali
    email_normal_pop3_host: Optional[str] = None
    email_normal_pop3_port: Optional[int] = None
    email_normal_pop3_user: Optional[str] = None
    email_normal_pop3_password: Optional[str] = None
    email_normal_smtp_host: Optional[str] = None
    email_normal_smtp_port: Optional[int] = None
    email_normal_smtp_user: Optional[str] = None
    email_normal_smtp_password: Optional[str] = None

    email_pec_pop3_host: Optional[str] = None
    email_pec_pop3_port: Optional[int] = None
    email_pec_pop3_user: Optional[str] = None
    email_pec_pop3_password: Optional[str] = None
    email_pec_smtp_host: Optional[str] = None
    email_pec_smtp_port: Optional[int] = None
    email_pec_smtp_user: Optional[str] = None
    email_pec_smtp_password: Optional[str] = None

    llm_provider: Optional[str] = None
    ollama_base_url: Optional[str] = None
    ollama_model_categorization: Optional[str] = None
    ollama_model_interpretation: Optional[str] = None
    ollama_model_generation: Optional[str] = None
    openai_api_key: Optional[str] = None
    openai_model: Optional[str] = None

    google_credentials_file: Optional[str] = None
    google_calendar_id: Optional[str] = None
    google_drive_folder_ust: Optional[str] = None
    google_drive_folder_snals: Optional[str] = None

    email_poll_interval: Optional[int] = None
    daily_summary_hour: Optional[int] = None
    email_mark_as_read: Optional[bool] = None
    email_delete_from_server: Optional[bool] = None
    email_fetch_limit: Optional[int] = None
    debug: Optional[bool] = None
    log_level: Optional[str] = None


class TestEmailResponse(BaseModel):
    """Response del test email"""
    pop3: Dict
    smtp: Dict
    overall_success: bool


@router.get("/", response_model=SettingsResponse)
async def get_settings_endpoint():
    """
    Recupera tutte le configurazioni correnti.
    """
    settings = get_settings()

    return SettingsResponse(
        # Email Normal
        email_normal_pop3_host=settings.EMAIL_NORMAL_POP3_HOST,
        email_normal_pop3_port=settings.EMAIL_NORMAL_POP3_PORT,
        email_normal_pop3_user=settings.EMAIL_NORMAL_POP3_USER,
        email_normal_pop3_password=settings.EMAIL_NORMAL_POP3_PASSWORD,
        email_normal_smtp_host=settings.EMAIL_NORMAL_SMTP_HOST,
        email_normal_smtp_port=settings.EMAIL_NORMAL_SMTP_PORT,
        email_normal_smtp_user=settings.EMAIL_NORMAL_SMTP_USER,
        email_normal_smtp_password=settings.EMAIL_NORMAL_SMTP_PASSWORD,

        # Email PEC
        email_pec_pop3_host=settings.EMAIL_PEC_POP3_HOST,
        email_pec_pop3_port=settings.EMAIL_PEC_POP3_PORT,
        email_pec_pop3_user=settings.EMAIL_PEC_POP3_USER,
        email_pec_pop3_password=settings.EMAIL_PEC_POP3_PASSWORD,
        email_pec_smtp_host=settings.EMAIL_PEC_SMTP_HOST,
        email_pec_smtp_port=settings.EMAIL_PEC_SMTP_PORT,
        email_pec_smtp_user=settings.EMAIL_PEC_SMTP_USER,
        email_pec_smtp_password=settings.EMAIL_PEC_SMTP_PASSWORD,

        # LLM
        llm_provider=settings.LLM_PROVIDER,
        ollama_base_url=settings.OLLAMA_BASE_URL,
        ollama_model_categorization=settings.OLLAMA_MODEL_CATEGORIZATION,
        ollama_model_interpretation=settings.OLLAMA_MODEL_INTERPRETATION,
        ollama_model_generation=settings.OLLAMA_MODEL_GENERATION,
        openai_api_key=settings.OPENAI_API_KEY,
        openai_model=settings.OPENAI_MODEL,

        # Google
        google_credentials_file=settings.GOOGLE_CREDENTIALS_FILE,
        google_calendar_id=settings.GOOGLE_CALENDAR_ID,
        google_drive_folder_ust=settings.GOOGLE_DRIVE_FOLDER_UST,
        google_drive_folder_snals=settings.GOOGLE_DRIVE_FOLDER_SNALS,

        # System
        email_poll_interval=settings.EMAIL_POLL_INTERVAL,
        daily_summary_hour=settings.DAILY_SUMMARY_HOUR,
        email_mark_as_read=settings.EMAIL_MARK_AS_READ,
        email_delete_from_server=settings.EMAIL_DELETE_FROM_SERVER,
        email_fetch_limit=settings.EMAIL_FETCH_LIMIT,
        debug=settings.DEBUG,
        log_level=settings.LOG_LEVEL,
    )


@router.put("/")
async def update_settings(data: SettingsUpdateRequest):
    """
    Aggiorna le configurazioni nel file .env

    NOTA: Dopo l'aggiornamento è necessario riavviare i servizi per applicare le modifiche.
    """
    try:
        env_file_path = Path("/app/.env")

        # Leggi il file .env esistente
        env_lines = []
        if env_file_path.exists():
            with open(env_file_path, 'r') as f:
                env_lines = f.readlines()

        # Crea un dizionario con le variabili esistenti
        env_dict = {}
        for line in env_lines:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_dict[key] = value

        # Mappa i campi dal request ai nomi delle variabili d'ambiente
        field_mapping = {
            'email_normal_pop3_host': 'EMAIL_NORMAL_POP3_HOST',
            'email_normal_pop3_port': 'EMAIL_NORMAL_POP3_PORT',
            'email_normal_pop3_user': 'EMAIL_NORMAL_POP3_USER',
            'email_normal_pop3_password': 'EMAIL_NORMAL_POP3_PASSWORD',
            'email_normal_smtp_host': 'EMAIL_NORMAL_SMTP_HOST',
            'email_normal_smtp_port': 'EMAIL_NORMAL_SMTP_PORT',
            'email_normal_smtp_user': 'EMAIL_NORMAL_SMTP_USER',
            'email_normal_smtp_password': 'EMAIL_NORMAL_SMTP_PASSWORD',

            'email_pec_pop3_host': 'EMAIL_PEC_POP3_HOST',
            'email_pec_pop3_port': 'EMAIL_PEC_POP3_PORT',
            'email_pec_pop3_user': 'EMAIL_PEC_POP3_USER',
            'email_pec_pop3_password': 'EMAIL_PEC_POP3_PASSWORD',
            'email_pec_smtp_host': 'EMAIL_PEC_SMTP_HOST',
            'email_pec_smtp_port': 'EMAIL_PEC_SMTP_PORT',
            'email_pec_smtp_user': 'EMAIL_PEC_SMTP_USER',
            'email_pec_smtp_password': 'EMAIL_PEC_SMTP_PASSWORD',

            'llm_provider': 'LLM_PROVIDER',
            'ollama_base_url': 'OLLAMA_BASE_URL',
            'ollama_model_categorization': 'OLLAMA_MODEL_CATEGORIZATION',
            'ollama_model_interpretation': 'OLLAMA_MODEL_INTERPRETATION',
            'ollama_model_generation': 'OLLAMA_MODEL_GENERATION',
            'openai_api_key': 'OPENAI_API_KEY',
            'openai_model': 'OPENAI_MODEL',

            'google_credentials_file': 'GOOGLE_CREDENTIALS_FILE',
            'google_calendar_id': 'GOOGLE_CALENDAR_ID',
            'google_drive_folder_ust': 'GOOGLE_DRIVE_FOLDER_UST',
            'google_drive_folder_snals': 'GOOGLE_DRIVE_FOLDER_SNALS',

            'email_poll_interval': 'EMAIL_POLL_INTERVAL',
            'daily_summary_hour': 'DAILY_SUMMARY_HOUR',
            'email_mark_as_read': 'EMAIL_MARK_AS_READ',
            'email_delete_from_server': 'EMAIL_DELETE_FROM_SERVER',
            'email_fetch_limit': 'EMAIL_FETCH_LIMIT',
            'debug': 'DEBUG',
            'log_level': 'LOG_LEVEL',
        }

        # Aggiorna solo i campi forniti
        for field_name, env_var_name in field_mapping.items():
            value = getattr(data, field_name)
            if value is not None:
                # Converti booleani in lowercase string
                if isinstance(value, bool):
                    value = str(value).lower()
                env_dict[env_var_name] = str(value)

        # Riscrivi il file .env
        with open(env_file_path, 'w') as f:
            # Scrivi commenti e sezioni
            f.write("# Database (Docker internal network)\n")
            if 'DATABASE_URL' in env_dict:
                f.write(f"DATABASE_URL={env_dict['DATABASE_URL']}\n")
            f.write("\n")

            f.write("# Redis (Docker internal network)\n")
            if 'REDIS_URL' in env_dict:
                f.write(f"REDIS_URL={env_dict['REDIS_URL']}\n")
            f.write("\n")

            f.write("# LLM (Docker internal network)\n")
            for key in ['LLM_PROVIDER', 'OLLAMA_BASE_URL', 'OLLAMA_MODEL_CATEGORIZATION',
                       'OLLAMA_MODEL_INTERPRETATION', 'OLLAMA_MODEL_GENERATION']:
                if key in env_dict:
                    f.write(f"{key}={env_dict[key]}\n")
            f.write("\n")

            f.write("# Email Account Normale\n")
            for key in ['EMAIL_NORMAL_POP3_HOST', 'EMAIL_NORMAL_POP3_PORT', 'EMAIL_NORMAL_POP3_USER',
                       'EMAIL_NORMAL_POP3_PASSWORD', 'EMAIL_NORMAL_SMTP_HOST', 'EMAIL_NORMAL_SMTP_PORT',
                       'EMAIL_NORMAL_SMTP_USER', 'EMAIL_NORMAL_SMTP_PASSWORD']:
                if key in env_dict:
                    f.write(f"{key}={env_dict[key]}\n")
            f.write("\n")

            f.write("# Email Account PEC\n")
            for key in ['EMAIL_PEC_POP3_HOST', 'EMAIL_PEC_POP3_PORT', 'EMAIL_PEC_POP3_USER',
                       'EMAIL_PEC_POP3_PASSWORD', 'EMAIL_PEC_SMTP_HOST', 'EMAIL_PEC_SMTP_PORT',
                       'EMAIL_PEC_SMTP_USER', 'EMAIL_PEC_SMTP_PASSWORD']:
                if key in env_dict:
                    f.write(f"{key}={env_dict[key]}\n")
            f.write("\n")

            f.write("# Webmail IMAP\n")
            for key in ['WEBMAIL_IMAP_HOST', 'WEBMAIL_IMAP_PORT', 'WEBMAIL_IMAP_USER', 'WEBMAIL_IMAP_PASSWORD']:
                if key in env_dict:
                    f.write(f"{key}={env_dict[key]}\n")
            f.write("\n")

            f.write("# Security\n")
            if 'SECRET_KEY' in env_dict:
                f.write(f"SECRET_KEY={env_dict['SECRET_KEY']}\n")
            f.write("\n")

            f.write("# App\n")
            for key in ['DEBUG', 'LOG_LEVEL', 'API_HOST', 'API_PORT']:
                if key in env_dict:
                    f.write(f"{key}={env_dict[key]}\n")
            f.write("\n")

            f.write("# Storage\n")
            for key in ['STORAGE_PATH', 'ATTACHMENTS_PATH', 'REPOSITORY_PATH']:
                if key in env_dict:
                    f.write(f"{key}={env_dict[key]}\n")
            f.write("\n")

            f.write("# Scheduling\n")
            for key in ['EMAIL_POLL_INTERVAL', 'DAILY_SUMMARY_HOUR']:
                if key in env_dict:
                    f.write(f"{key}={env_dict[key]}\n")
            f.write("\n")

            f.write("# Email Behavior\n")
            for key in ['EMAIL_MARK_AS_READ', 'EMAIL_DELETE_FROM_SERVER', 'EMAIL_FETCH_LIMIT']:
                if key in env_dict:
                    f.write(f"{key}={env_dict[key]}\n")

        return {
            "success": True,
            "message": "Configurazioni aggiornate con successo. Riavvia i servizi per applicare le modifiche.",
            "restart_command": "docker-compose restart backend celery-worker celery-beat"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Errore durante l'aggiornamento delle configurazioni: {str(e)}"
        )


@router.post("/test-email-normal", response_model=TestEmailResponse)
async def test_email_normal():
    """
    Test della configurazione email NORMALE:
    - Test POP3: connessione e lettura prima email
    - Test SMTP: invio email di test a se stesso
    """
    try:
        client = EmailNormalClient()
        results = client.test_connection()
        return results
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Errore durante il test: {str(e)}"
        )


@router.post("/test-email-pec", response_model=TestEmailResponse)
async def test_email_pec():
    """
    Test della configurazione email PEC:
    - Test POP3: connessione e lettura prima email
    - Test SMTP: invio email di test a se stesso
    """
    try:
        client = EmailPECClient()
        results = client.test_connection()
        return results
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Errore durante il test: {str(e)}"
        )
