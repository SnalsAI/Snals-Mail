# SNALS Email Agent - Quick Reference

Riferimento rapido per sviluppatori.

---

## 🚀 Comandi Principali

```bash
# Setup iniziale (5 minuti)
make setup              # Build + start + migrations + init Ollama

# Gestione servizi
make up                 # Start tutti i servizi
make down               # Stop tutti i servizi
make restart            # Restart tutti i servizi
make ps                 # Status servizi

# Development
make logs               # View logs tutti i servizi
make logs-backend       # Logs solo backend
make logs-celery        # Logs celery worker
make logs-beat          # Logs celery beat

# Database
make init-db            # Run migrations
make shell-db           # PostgreSQL shell
alembic upgrade head    # Apply migrations
alembic revision -m ""  # Create migration

# Testing
make test               # Run test sistema
make shell-backend      # Backend container shell

# Cleanup
make clean              # Stop e remove containers
make clean-all          # Remove anche volumes

# Ollama
make init-ollama        # Download modelli LLM
```

---

## 📁 File Importanti

```
backend/
├── main.py                          # Entry point FastAPI
├── .env                             # Config (NON committare!)
├── requirements.txt                 # Dipendenze Python
│
├── app/
│   ├── config.py                    # Settings centrali
│   ├── database.py                  # DB setup
│   │
│   ├── models/                      # 7 SQLAlchemy models
│   │   ├── email.py                 # Email principale
│   │   ├── interpretazione.py       # Dati LLM
│   │   ├── azione.py                # Azioni auto
│   │   ├── evento.py                # Calendario
│   │   └── regola.py                # Rules engine
│   │
│   ├── api/routes/                  # 30+ endpoints REST
│   │   ├── emails.py                # CRUD email
│   │   ├── azioni.py                # CRUD azioni
│   │   ├── regole.py                # CRUD regole
│   │   └── calendario.py            # CRUD eventi
│   │
│   ├── services/                    # Business logic
│   │   ├── email_ingest.py          # POP3/SMTP client
│   │   ├── categorizer.py           # LLM categorizer
│   │   ├── interpreter.py           # LLM interpreter
│   │   ├── action_executor.py       # Executor azioni
│   │   └── rules_engine.py          # Motore regole
│   │
│   ├── integrations/                # External services
│   │   ├── llm_client.py            # Ollama/OpenAI
│   │   ├── google_drive_client.py   # Drive API
│   │   ├── google_calendar_client.py # Calendar API
│   │   └── webmail_client.py        # IMAP client
│   │
│   └── tasks/                       # Celery tasks
│       ├── email_polling.py         # Poll email (120s)
│       └── action_tasks.py          # Execute actions (60s)
│
└── scripts/
    ├── test_system.py               # Test automatici
    └── init_ollama.sh               # Init LLM models
```

---

## 🌐 API Endpoints

Base URL: `http://localhost:8001`

### Email
```bash
GET    /api/emails                   # Lista (filtri: categoria, stato, search)
GET    /api/emails/{id}              # Dettagli
PUT    /api/emails/{id}              # Aggiorna
DELETE /api/emails/{id}              # Elimina
GET    /api/emails/{id}/interpretazione  # Dati LLM
POST   /api/emails/{id}/reprocess    # Riprocessa
```

### Azioni
```bash
GET    /api/azioni                   # Lista
GET    /api/azioni/{id}              # Dettagli
POST   /api/azioni/{id}/execute      # Esegui
POST   /api/azioni/{id}/retry        # Ritenta
GET    /api/azioni/stats/summary     # Statistiche
```

### Regole
```bash
GET    /api/regole                   # Lista
POST   /api/regole                   # Crea
GET    /api/regole/{id}              # Dettagli
PUT    /api/regole/{id}              # Aggiorna
POST   /api/regole/{id}/toggle       # Attiva/disattiva
POST   /api/regole/{id}/test         # Test su email
POST   /api/regole/test-conditions   # Test condizioni
```

### Calendario
```bash
GET    /api/calendario               # Lista eventi
POST   /api/calendario               # Crea evento
GET    /api/calendario/{id}          # Dettagli
PUT    /api/calendario/{id}          # Aggiorna
POST   /api/calendario/sync-google   # Import da Google
```

### Swagger Docs
```
http://localhost:8001/docs           # Interactive API docs
http://localhost:8001/redoc          # ReDoc documentation
```

---

## 🗄️ Database

```bash
# Connessione diretta
psql postgresql://snals_user:snals_password@localhost:5432/snals_email_agent

# Query utili
SELECT COUNT(*) FROM emails;
SELECT categoria, COUNT(*) FROM emails GROUP BY categoria;
SELECT COUNT(*) FROM azioni WHERE stato = 'PENDING';

# Reset database (ATTENZIONE: distruttivo!)
docker-compose down -v
make init-db
```

---

## 🤖 LLM (Ollama)

```bash
# Modelli usati
llama3.2:3b      # Categorizzazione (veloce)
mistral:7b       # Interpretazione (accurato)

# Comandi Ollama
ollama list                          # Lista modelli installati
ollama pull llama3.2:3b              # Download modello
ollama run mistral:7b "test"         # Test modello
curl http://localhost:11434/api/tags # API status

# Cambia modello in .env
LLM_MODEL_CATEGORIZATION=llama3.2:3b
LLM_MODEL_INTERPRETATION=mistral:7b
```

---

## ⚙️ Celery

```bash
# Worker
celery -A app.tasks worker --loglevel=info

# Beat (scheduler)
celery -A app.tasks beat --loglevel=info

# Monitor tasks
celery -A app.tasks inspect active       # Tasks attivi
celery -A app.tasks inspect scheduled    # Tasks schedulati
celery -A app.tasks inspect stats        # Statistiche

# Flower (web UI)
pip install flower
celery -A app.tasks flower               # http://localhost:5555
```

---

## 📝 Configurazione (.env)

```bash
# App
APP_NAME=SNALS Email Agent
DEBUG=True
API_HOST=0.0.0.0
API_PORT=8001

# Database
DATABASE_URL=postgresql://snals_user:snals_password@postgres:5432/snals_email_agent

# Redis
REDIS_URL=redis://redis:6379/0

# Email Normale
EMAIL_NORMAL_POP3_HOST=pop.gmail.com
EMAIL_NORMAL_POP3_PORT=995
EMAIL_NORMAL_POP3_USER=your@email.com
EMAIL_NORMAL_POP3_PASSWORD=your_password

# Email PEC
EMAIL_PEC_POP3_HOST=pop.pec.provider.it
EMAIL_PEC_POP3_PORT=995
EMAIL_PEC_POP3_USER=your@pec.it
EMAIL_PEC_POP3_PASSWORD=your_password

# LLM
LLM_PROVIDER=ollama                      # o "openai"
OLLAMA_BASE_URL=http://ollama:11434
LLM_MODEL_CATEGORIZATION=llama3.2:3b
LLM_MODEL_INTERPRETATION=mistral:7b

# Google (OAuth2 - opzionale)
GOOGLE_CREDENTIALS_FILE=/path/to/credentials.json
```

---

## 🧪 Testing Rapido

```bash
# 1. Health check
curl http://localhost:8001/health

# 2. Test API
curl http://localhost:8001/api/emails/ | jq

# 3. Test database
docker exec -it snals-postgres psql -U snals_user -d snals_email_agent -c "SELECT COUNT(*) FROM emails;"

# 4. Test LLM
curl http://localhost:11434/api/tags

# 5. Test Celery
docker exec -it snals-celery-worker celery -A app.tasks inspect active

# 6. Test completo automatico
python backend/scripts/test_system.py
```

---

## 🐛 Debug

```bash
# Logs in tempo reale
docker-compose logs -f backend
docker-compose logs -f celery-worker
docker-compose logs -f celery-beat

# Shell backend
docker exec -it snals-backend bash
python
>>> from app.database import SessionLocal
>>> db = SessionLocal()
>>> db.query(Email).count()

# Shell database
docker exec -it snals-postgres psql -U snals_user snals_email_agent

# Restart singolo servizio
docker-compose restart backend
docker-compose restart celery-worker
```

---

## 🔧 Development Workflow

```bash
# 1. Modifica codice
vim backend/app/api/routes/emails.py

# 2. Il backend si ricarica automaticamente (--reload)
# Oppure restart manuale:
docker-compose restart backend

# 3. Test modifiche
curl http://localhost:8001/api/emails/

# 4. Commit
git add .
git commit -m "Add new feature"
git push
```

---

## 📊 Categorie Email

```python
# 8 categorie supportate
EmailCategory = Enum(
    'info_generiche',
    'richiesta_appuntamento',
    'richiesta_tesseramento',
    'convocazione_scuola',
    'comunicazione_ust_usr',
    'comunicazione_scuola',
    'comunicazione_snals_centrale',
    'varie'
)
```

---

## 🎯 Azioni Automatiche

```python
# Tipi azione supportati
TipoAzione = Enum(
    'BOZZA_RISPOSTA',          # Genera risposta LLM + salva in Drafts
    'CREA_EVENTO_CALENDARIO',  # Crea evento Google Calendar
    'CARICA_SU_DRIVE',         # Upload allegati Drive
    'INOLTRA_EMAIL',           # Inoltra a destinatario
)

# Stati azione
StatoAzione = Enum(
    'PENDING',        # In attesa
    'IN_ESECUZIONE',  # In corso
    'COMPLETATA',     # Completata
    'FALLITA'         # Fallita
)
```

---

## 🔍 Condizioni Rules Engine

```python
# Condizioni disponibili
conditions = [
    'uguale', 'diverso',
    'contiene', 'non_contiene',
    'inizia_con', 'finisce_con',
    'regex',
    'maggiore', 'minore',
    'in_lista',
    'vuoto', 'non_vuoto'
]

# Campi valutabili
fields = [
    'mittente', 'destinatario', 'oggetto', 'corpo',
    'categoria', 'account_type',
    'has_allegati', 'num_allegati',
    'interpretazione.*'
]
```

---

## 📈 Performance Tips

```python
# 1. Usa indici database per query frequenti
# 2. Limita polling interval se troppe email
EMAIL_POLL_INTERVAL=300  # 5 minuti invece di 2

# 3. Usa Ollama con GPU
docker-compose.yml:
  ollama:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              capabilities: [gpu]

# 4. Scale Celery workers
docker-compose up -d --scale celery-worker=3

# 5. Ottimizza query LLM
LLM_MAX_TOKENS=500  # Riduci token se risposte troppo lunghe
```

---

## ❓ Troubleshooting

### Problema: Backend non si avvia
```bash
# Check logs
docker-compose logs backend

# Common causes:
# - Database non pronto → attendi 30s
# - .env mancante → copia da .env.example
# - Port 8001 occupato → cambia API_PORT
```

### Problema: Celery non esegue tasks
```bash
# Check beat schedule
docker-compose logs celery-beat | grep "Scheduler"

# Check worker
docker exec -it snals-celery-worker celery -A app.tasks inspect active

# Restart celery
docker-compose restart celery-worker celery-beat
```

### Problema: Ollama lento/errore
```bash
# Check GPU
nvidia-smi

# Usa CPU se no GPU
OLLAMA_NUM_GPU=0

# Usa modelli più piccoli
LLM_MODEL_CATEGORIZATION=llama3.2:1b
```

### Problema: Google API non funziona
```bash
# 1. Verifica credentials.json
cat /path/to/credentials.json

# 2. Autenticazione OAuth manuale
python
>>> from app.integrations.google_drive_client import GoogleDriveClient
>>> client = GoogleDriveClient()
>>> client.authenticate()

# 3. Usa account test senza OAuth per sviluppo
```

---

## 📚 Risorse

- **Docs ufficiali:** `README.md`, `DOCKER_README.md`, `ARCHITECTURE.md`
- **FastAPI docs:** https://fastapi.tiangolo.com
- **SQLAlchemy:** https://docs.sqlalchemy.org/en/20/
- **Celery:** https://docs.celeryq.dev
- **Ollama:** https://ollama.ai/docs

---

**Ultimo aggiornamento:** 2025-11-13
**Versione:** 0.3.0
