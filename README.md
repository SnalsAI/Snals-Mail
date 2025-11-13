# SNALS Email Agent

Sistema automatico di gestione email per sindacato scuola SNALS con analisi LLM.

## 📋 Stato Progetto

### ✅ FASE 1: Setup Iniziale (Completata)
- [x] Struttura progetto completa
- [x] Database models (7 tabelle)
- [x] FastAPI base
- [x] Alembic migrations
- [x] Configurazione con Pydantic Settings

### ✅ FASE 2: Ingest Email (Completata)
- [x] Client POP3/SMTP per email normale
- [x] Client POP3/SMTP per PEC
- [x] Celery tasks con beat scheduler
- [x] Polling periodico automatico

### ✅ FASE 3: Categorizzazione & Interpretazione LLM (Completata)
- [x] Client LLM unificato (Ollama + OpenAI)
- [x] Categorizzatore automatico (8 categorie)
- [x] Interpretatore con estrazione dati strutturati
- [x] Integrazione completa nel flusso

### 🔲 FASE 4-8: Da Implementare
- [ ] Azioni automatiche (bozze risposte, eventi calendario)
- [ ] Frontend React con UI completa
- [ ] Integrazioni Google (Calendar, Drive)
- [ ] Sistema regole personalizzabili
- [ ] Testing e deployment

## 🚀 Quick Start

### Prerequisiti
- Python 3.10+
- PostgreSQL
- Redis
- Ollama con modelli: `llama3.2:3b`, `mistral:7b`

### Installazione

```bash
# 1. Setup backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Configurazione
cp .env.example .env
# Modifica .env con le tue credenziali

# 3. Database
# Crea database PostgreSQL: snals_email_agent
alembic upgrade head

# 4. Avvia servizi
# Terminal 1 - Backend API
python main.py

# Terminal 2 - Celery Worker
celery -A app.tasks worker --loglevel=info

# Terminal 3 - Celery Beat (scheduler)
celery -A app.tasks beat --loglevel=info
```

### Verifica

```bash
curl http://localhost:8001/health
# Output: {"status":"healthy",...}
```

## 📊 Architettura

```
┌─────────────────┐
│   Email Server  │
│   (POP3/SMTP)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐
│  Celery Tasks   │─────▶│  PostgreSQL  │
│  (Polling)      │      │   Database   │
└────────┬────────┘      └──────────────┘
         │
         ▼
┌─────────────────┐
│  LLM Analysis   │
│  (Ollama/OAI)   │
│                 │
│ • Categorize    │
│ • Interpret     │
│ • Generate      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  FastAPI REST   │
│  API (8001)     │
└─────────────────┘
```

## 🗂️ Struttura Progetto

```
backend/
├── main.py                 # FastAPI entry point
├── requirements.txt        # Python dependencies
├── .env                    # Configuration (create from .env.example)
│
├── app/
│   ├── config.py          # Settings
│   ├── database.py        # SQLAlchemy setup
│   │
│   ├── models/            # Database models
│   │   ├── email.py       # Email model
│   │   ├── interpretazione.py
│   │   ├── azione.py
│   │   └── ...
│   │
│   ├── services/          # Business logic
│   │   ├── email_ingest.py    # POP3/SMTP clients
│   │   ├── categorizer.py     # LLM categorization
│   │   └── interpreter.py     # LLM interpretation
│   │
│   ├── integrations/      # External integrations
│   │   └── llm_client.py      # Ollama/OpenAI client
│   │
│   └── tasks/             # Celery tasks
│       ├── __init__.py        # Celery app + schedule
│       └── email_polling.py   # Polling tasks
│
├── alembic/               # Database migrations
│
├── storage/               # File storage
│   └── attachments/       # Email attachments
│
docs/                      # Documentation
├── DEVELOPMENT_LOG.md     # Development log
├── ARCHITECTURE.md        # System architecture
└── API_DOCUMENTATION.md   # API docs
```

## ⚙️ Configurazione

### Variabili Ambiente (.env)

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/snals_email_agent

# Email Accounts
EMAIL_NORMAL_POP3_HOST=pop.example.com
EMAIL_NORMAL_POP3_USER=your@email.com
EMAIL_NORMAL_POP3_PASSWORD=yourpassword
# ... (similmente per PEC)

# LLM
LLM_PROVIDER=ollama  # o "openai"
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL_CATEGORIZATION=llama3.2:3b
OLLAMA_MODEL_INTERPRETATION=mistral:7b

# Security
SECRET_KEY=your-secret-key-here

# App
DEBUG=false
API_PORT=8001
```

## 📚 Documentazione

- [Development Log](docs/DEVELOPMENT_LOG.md) - Diario sviluppo dettagliato
- [Architecture](docs/ARCHITECTURE.md) - Architettura sistema
- [API Documentation](docs/API_DOCUMENTATION.md) - API reference
- [Resume Guide](docs/RESUME_GUIDE.md) - Come riprendere sviluppo

## 🔧 Stack Tecnologico

**Backend:**
- FastAPI 0.104 - Web framework
- SQLAlchemy 2.0 - ORM
- Alembic - Database migrations
- Celery 5.3 - Task queue
- Redis - Message broker

**LLM:**
- Ollama - Local LLM inference
- OpenAI API - Alternative LLM provider

**Database:**
- PostgreSQL - Primary database

**Frontend (da implementare):**
- React 18 + Vite
- TailwindCSS

## 📝 Categorie Email

Il sistema categorizza automaticamente le email in:

1. **info_generiche** - Richieste informazioni generiche
2. **richiesta_appuntamento** - Richieste appuntamenti
3. **richiesta_tesseramento** - Richieste iscrizione
4. **convocazione_scuola** - Convocazioni OO.SS.
5. **comunicazione_ust_usr** - Comunicazioni enti pubblici
6. **comunicazione_scuola** - Comunicazioni scuole
7. **comunicazione_snals_centrale** - Comunicazioni SNALS
8. **varie** - Altro

## 🤝 Contributing

Progetto in sviluppo attivo. Per contribuire:

1. Leggi [DEVELOPMENT_LOG.md](docs/DEVELOPMENT_LOG.md)
2. Segui le convenzioni del progetto
3. Testa accuratamente le modifiche

## 📄 Licenza

[Specificare licenza]

## 🔗 Links

- [Documentazione Ollama](https://ollama.ai/docs)
- [FastAPI Docs](https://fastapi.tiangolo.com)
- [Celery Docs](https://docs.celeryq.dev)

---

**Versione:** 0.1.0  
**Ultima modifica:** 2025-11-13  
**Status:** 🟢 In sviluppo attivo
