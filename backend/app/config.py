"""
Configurazione applicazione SNALS Email Agent
Carica variabili da .env e fornisce accesso centralizzato
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Configurazioni applicazione"""
    
    # App
    APP_NAME: str = "SNALS Email Agent"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    
    # Server
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8001
    
    # Database
    DATABASE_URL: str
    DB_ECHO: bool = False
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Email Accounts - Normale
    EMAIL_NORMAL_POP3_HOST: str
    EMAIL_NORMAL_POP3_PORT: int = 995
    EMAIL_NORMAL_POP3_USER: str
    EMAIL_NORMAL_POP3_PASSWORD: str
    EMAIL_NORMAL_SMTP_HOST: str
    EMAIL_NORMAL_SMTP_PORT: int = 587
    EMAIL_NORMAL_SMTP_USER: str
    EMAIL_NORMAL_SMTP_PASSWORD: str
    
    # Email Accounts - PEC
    EMAIL_PEC_POP3_HOST: str
    EMAIL_PEC_POP3_PORT: int = 995
    EMAIL_PEC_POP3_USER: str
    EMAIL_PEC_POP3_PASSWORD: str
    EMAIL_PEC_SMTP_HOST: str
    EMAIL_PEC_SMTP_PORT: int = 587
    EMAIL_PEC_SMTP_USER: str
    EMAIL_PEC_SMTP_PASSWORD: str
    
    # Webmail IMAP
    WEBMAIL_IMAP_HOST: str
    WEBMAIL_IMAP_PORT: int = 993
    WEBMAIL_IMAP_USER: str
    WEBMAIL_IMAP_PASSWORD: str
    
    # LLM
    LLM_PROVIDER: str = "ollama"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL_CATEGORIZATION: str = "llama3.2:1b"
    OLLAMA_MODEL_INTERPRETATION: str = "llama3.2:3b"  # Modello di qualità
    OLLAMA_MODEL_GENERATION: str = "llama3.2:1b"
    OLLAMA_MODEL_GEMMA: str = "gemma2:2b"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_DAILY_LIMIT_EUR: float = 1.0  # Budget massimo giornaliero OpenAI
    ANTHROPIC_API_KEY: str = ""  # API key per Claude Code (bug fixing)

    # Interpello Parsing Strategy
    # Options: regex, openai, ollama, smart, hybrid, nlp, unified
    # - regex: Solo pattern regex (veloce, affidabile per dati strutturati)
    # - nlp: spaCy + BERT NER
    # - hybrid: Regex + validazione Ollama
    # - smart: SmartInterpelloExtractor (estrattore intelligente)
    # - unified: Pipeline completa Regex → NLP → LLM → ChatGPT (raccomandato)
    INTERPELLO_PARSER_STRATEGY: str = "unified"
    
    # Google APIs
    GOOGLE_CREDENTIALS_FILE: str = "config/google_credentials.json"
    GOOGLE_TOKEN_FILE: str = "config/google_token.json"
    GOOGLE_CALENDAR_ID: str = "892fbfd969f36ae3efecf1ccbddaea91e5148b6a2d640f8a9e79556225356f49@group.calendar.google.com"  # SNALS Taranto - Convocazioni (condiviso con snalstaranto@gmail.com)
    GOOGLE_DRIVE_FOLDER_UST: str = ""
    GOOGLE_DRIVE_FOLDER_SNALS: str = ""
    GOOGLE_DRIVE_SHARE_EMAIL: str = "snalstaranto@gmail.com"  # Email per condivisione automatica file
    
    # Storage
    STORAGE_PATH: str = "storage"
    ATTACHMENTS_PATH: str = "storage/attachments"
    REPOSITORY_PATH: str = "storage/repository"
    
    # Timezone
    TIMEZONE: str = "Europe/Rome"  # Fuso orario di Taranto

    # Scheduling
    EMAIL_POLL_INTERVAL: int = 120
    DAILY_SUMMARY_HOUR: int = 18

    # Email Behavior
    EMAIL_MARK_AS_READ: bool = False  # Se True, marca le email come lette sul server (richiede IMAP)
    EMAIL_DELETE_FROM_SERVER: bool = False  # Se True, elimina le email dal server dopo il download
    EMAIL_FETCH_LIMIT: int = 3  # Numero massimo di email da scaricare per polling (ridotto per evitare timeout Ollama)
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
