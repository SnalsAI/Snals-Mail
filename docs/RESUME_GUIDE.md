# Guida Ripresa Sviluppo - SNALS Email Agent

## 🎯 Stato Attuale: FASI 1-3 COMPLETE

### ✅ Cosa È Stato Fatto

**FASE 1: Setup Iniziale**
- Struttura progetto completa con tutte le directory
- Virtual environment Python + dipendenze installate
- Configurazione con Pydantic Settings (.env)
- 7 database models definiti con SQLAlchemy 2.0
- Alembic configurato per migrations
- FastAPI base con endpoints `/` e `/health`

**FASE 2: Ingest Email**
- Client POP3/SMTP per email normale e PEC
- Celery app configurato con Redis
- Beat schedule per polling periodico (ogni 120s)
- Task `poll_email_normal` e `poll_email_pec`

**FASE 3: LLM Categorizzazione/Interpretazione**
- Client LLM unificato (supporta Ollama e OpenAI)
- Servizio categorizzazione (8 categorie)
- Servizio interpretazione con estrazione dati
- Integrazione completa nei task di polling

### 📁 File Chiave Creati

```
backend/
├── main.py                                # FastAPI entry point
├── requirements.txt                       # Dipendenze
├── .env                                   # Config (da personalizzare)
├── app/
│   ├── config.py                         # Settings
│   ├── database.py                       # DB setup
│   ├── models/                           # 7 models (email, interpretazione, etc)
│   ├── services/
│   │   ├── email_ingest.py              # POP3/SMTP clients ✓
│   │   ├── categorizer.py               # Categorizzazione LLM ✓
│   │   └── interpreter.py               # Interpretazione LLM ✓
│   ├── integrations/
│   │   └── llm_client.py                # Client Ollama/OpenAI ✓
│   └── tasks/
│       ├── __init__.py                   # Celery setup ✓
│       └── email_polling.py             # Task polling ✓
├── alembic/                              # Migrations (configurato)
└── docs/                                 # Documentazione completa
```

---

## 🚀 Come Riprendere

### 1. Verifica Sistema

```bash
# Naviga al progetto
cd /home/user/Snals-Mail

# Verifica branch
git status
git log --oneline -5

# Verifica file chiave
ls -la backend/
ls -la backend/app/services/
ls -la backend/app/models/
```

### 2. Setup Ambiente

```bash
cd backend

# Attiva virtual environment
source venv/bin/activate

# Verifica dipendenze
pip list | grep -E 'fastapi|sqlalchemy|celery|openai'

# Verifica config
cat .env | head -20
```

### 3. Verifica Servizi Esterni

**PostgreSQL:**
```bash
# Verifica connessione
psql -U snals_user -d snals_email_agent -c "\dt"

# Se non esiste, crea:
createdb snals_email_agent -O snals_user

# Applica migrations
alembic upgrade head
```

**Redis:**
```bash
# Verifica Redis
redis-cli ping
# Output: PONG
```

**Ollama:**
```bash
# Verifica Ollama
curl http://localhost:11434/api/tags

# Scarica modelli se necessario
ollama pull llama3.2:3b
ollama pull mistral:7b
```

### 4. Avvia Applicazione

```bash
# Terminal 1 - Backend API
cd backend
source venv/bin/activate
python main.py
# Output: Uvicorn running on http://0.0.0.0:8001

# Terminal 2 - Celery Worker
cd backend
source venv/bin/activate
celery -A app.tasks worker --loglevel=info

# Terminal 3 - Celery Beat
cd backend
source venv/bin/activate
celery -A app.tasks beat --loglevel=info
```

### 5. Test Funzionamento

```bash
# Test health check
curl http://localhost:8001/
# Output: {"app":"SNALS Email Agent","version":"0.1.0","status":"running"}

curl http://localhost:8001/health
# Output: {"status":"healthy",...}

# Test manuale task (opzionale)
cd backend
source venv/bin/activate
python << EOF
from app.tasks.email_polling import poll_email_normal
poll_email_normal()
