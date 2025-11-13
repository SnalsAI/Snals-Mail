# SNALS Email Agent

Sistema automatico di gestione email per sindacato scuola SNALS con analisi LLM.

[![Status](https://img.shields.io/badge/status-production%20ready-green)]()
[![Docker](https://img.shields.io/badge/docker-supported-blue)]()
[![Python](https://img.shields.io/badge/python-3.11-blue)]()

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

### ✅ FASE 8: Testing & Deployment (Completata)
- [x] Docker Compose setup completo
- [x] Script testing automatizzati
- [x] Documentazione deployment
- [x] Makefile per gestione facile
- [x] Health checks

### ✅ FASE 4: Azioni Automatiche (Completata)
- [x] Google Drive Client per upload allegati
- [x] Webmail Client IMAP per bozze
- [x] Action Executor orchestratore
- [x] Celery tasks azioni automatiche

### ✅ FASE 6: API Complete (Completata)
- [x] Google Calendar Client
- [x] API REST complete (Email, Azioni, Regole, Calendario)
- [x] 30+ endpoints CRUD
- [x] Pydantic schemas validazione

### ✅ FASE 7: Rules Engine (Completata)
- [x] Motore valutazione regole
- [x] Condizioni complesse (AND/OR)
- [x] Test regole senza esecuzione
- [x] Sistema priorità e template

### 🔲 FASE 5: Frontend React (Da Implementare)
- [ ] Dashboard con statistiche
- [ ] Gestione email UI completa
- [ ] Calendario eventi integrato
- [ ] Builder regole visuale

## 🚀 Quick Start con Docker

### Setup in 5 Minuti

```bash
# 1. Clone repository
git clone https://github.com/SnalsAI/Snals-Mail.git
cd Snals-Mail

# 2. Configura credenziali email
cd backend
cp .env.docker .env
nano .env  # Modifica EMAIL_* con le tue credenziali reali

# 3. Avvia tutto
cd ..
make setup

# 4. Verifica
make test
```

### Servizi Disponibili

- **API REST**: http://localhost:8001
- **Swagger Docs**: http://localhost:8001/docs
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379
- **Ollama**: localhost:11434

### Comandi Utili

```bash
make help       # Mostra tutti i comandi
make up         # Avvia servizi
make down       # Ferma servizi
make logs       # Visualizza logs
make ps         # Status servizi
make test       # Test sistema
make clean      # Pulizia completa
```

## 🔧 Setup Manuale

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
createdb snals_email_agent
alembic upgrade head

# 4. Ollama models
ollama pull llama3.2:3b
ollama pull mistral:7b

# 5. Avvia servizi (3 terminali)
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

# Test completo
python backend/scripts/test_system.py
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
Snals-Mail/
├── docker-compose.yml          # Docker orchestration
├── Makefile                    # Comandi utili
├── DOCKER_README.md            # Guida Docker
├── DEPLOYMENT_QUICKSTART.md    # Quick start deployment
│
├── backend/
│   ├── Dockerfile              # Container backend
│   ├── docker-entrypoint.sh    # Startup script
│   ├── main.py                 # FastAPI entry point
│   ├── requirements.txt        # Dependencies
│   │
│   ├── app/
│   │   ├── config.py          # Settings
│   │   ├── database.py        # SQLAlchemy setup
│   │   ├── models/            # Database models (7)
│   │   ├── services/          # Business logic
│   │   │   ├── email_ingest.py
│   │   │   ├── categorizer.py
│   │   │   └── interpreter.py
│   │   ├── integrations/
│   │   │   └── llm_client.py
│   │   └── tasks/
│   │       └── email_polling.py
│   │
│   ├── alembic/               # Database migrations
│   └── scripts/
│       ├── test_system.py     # Test completo
│       └── init_ollama.sh     # Init modelli LLM
│
└── docs/
    ├── DEVELOPMENT_LOG.md     # Development log
    ├── ARCHITECTURE.md        # System architecture
    ├── DEPLOYMENT.md          # Guida deployment completa
    ├── RESUME_GUIDE.md        # Come riprendere sviluppo
    └── API_DOCUMENTATION.md   # API reference
```

## 📝 Categorie Email

Il sistema categorizza automaticamente le email in 8 categorie:

1. **info_generiche** - Richieste informazioni generiche
2. **richiesta_appuntamento** - Richieste appuntamenti
3. **richiesta_tesseramento** - Richieste iscrizione
4. **convocazione_scuola** - Convocazioni OO.SS.
5. **comunicazione_ust_usr** - Comunicazioni enti pubblici
6. **comunicazione_scuola** - Comunicazioni scuole
7. **comunicazione_snals_centrale** - Comunicazioni SNALS
8. **varie** - Altro

## 🔧 Stack Tecnologico

**Backend:**
- FastAPI 0.104 - Web framework
- SQLAlchemy 2.0 - ORM
- Alembic - Database migrations
- Celery 5.3 - Task queue
- Redis - Message broker
- Pydantic - Validation

**Database:**
- PostgreSQL - Primary database

**LLM:**
- Ollama - Local LLM inference
- OpenAI API - Alternative provider

**Deployment:**
- Docker & Docker Compose
- Nginx (reverse proxy)
- Systemd (services)

## 🧪 Testing

### Test Automatici

```bash
# Con Docker
make test

# Manuale
python backend/scripts/test_system.py
```

Output atteso:
```
🧪 SNALS Email Agent - Test Sistema Completo
============================================================
✅ API Health           PASS
✅ Database            PASS
✅ LLM Categorizer     PASS
✅ LLM Interpreter     PASS
✅ Save Email          PASS

Totale: 5/5 test passati
🎉 Tutti i test sono passati!
```

### Test Manuali

```bash
# Health check
curl http://localhost:8001/health

# Swagger UI interattiva
open http://localhost:8001/docs

# Logs
make logs          # Docker
tail -f logs/app.log  # Manuale
```

## 📚 Documentazione

- **[DOCKER_README.md](DOCKER_README.md)** - Guida completa Docker
- **[DEPLOYMENT_QUICKSTART.md](DEPLOYMENT_QUICKSTART.md)** - Quick start
- **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Deployment produzione
- **[docs/RESUME_GUIDE.md](docs/RESUME_GUIDE.md)** - Guida sviluppo
- **[docs/DEVELOPMENT_LOG.md](docs/DEVELOPMENT_LOG.md)** - Diario sviluppo
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Architettura sistema

## 🔒 Sicurezza

- Password database forti
- SECRET_KEY generata
- SSL/TLS per produzione
- Rate limiting Nginx
- Firewall configurato
- Credenziali email criptate (TODO)

## 💾 Backup

### Database

```bash
# Backup
docker-compose exec postgres pg_dump -U snals_user snals_email_agent > backup.sql

# Restore
docker-compose exec -T postgres psql -U snals_user snals_email_agent < backup.sql
```

### Storage

```bash
# Backup allegati e configurazioni
tar -czf backup-storage.tar.gz storage/ backend/.env
```

## 🔄 Aggiornamento

```bash
# Pull nuovo codice
git pull origin main

# Con Docker
make restart

# Manuale
cd backend
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
sudo systemctl restart snals-backend snals-celery snals-celery-beat
```

## 🐛 Troubleshooting

### Servizi non si avviano

```bash
# Docker
make logs
make ps

# Manuale
sudo systemctl status snals-backend
journalctl -u snals-backend -n 50
```

### Database errori

```bash
# Connessione
docker-compose exec postgres psql -U snals_user -d snals_email_agent

# Verifica migrations
alembic current
alembic history
```

### LLM non risponde

```bash
# Verifica Ollama
curl http://localhost:11434/api/tags

# Scarica modelli
./backend/scripts/init_ollama.sh
```

Vedi [DOCKER_README.md](DOCKER_README.md#troubleshooting) per troubleshooting dettagliato.

## 🤝 Contributing

1. Fork il repository
2. Crea feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit modifiche (`git commit -m 'Add AmazingFeature'`)
4. Push al branch (`git push origin feature/AmazingFeature`)
5. Apri Pull Request

## 📄 Licenza

[Specificare licenza]

## 🔗 Links Utili

- [Documentazione Ollama](https://ollama.ai/docs)
- [FastAPI Docs](https://fastapi.tiangolo.com)
- [Celery Docs](https://docs.celeryq.dev)
- [Docker Compose](https://docs.docker.com/compose/)

## 📞 Supporto

- **Issues**: https://github.com/SnalsAI/Snals-Mail/issues
- **Documentazione**: [docs/](docs/)
- **Email**: [specificare]

---

**Versione:** 0.3.0
**Ultimo aggiornamento:** 2025-11-13
**Status:** 🟢 Backend Production Ready - Frontend in sviluppo

**Fasi completate:** 1, 2, 3, 4, 6, 7, 8 (7/8)
**Endpoint API:** 30+
**Integrazioni:** Google Drive, Google Calendar, Ollama LLM, OpenAI

**Tempo setup:** ~5 minuti con Docker, ~15 minuti manuale
