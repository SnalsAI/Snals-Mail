# SNALS Email Agent - Sistema Completo

Sistema automatizzato di gestione email per sindacato scuola SNALS.

## ✅ Stato Progetto: PRODUCTION READY

Tutte le fasi implementate e testate:
- ✓ Setup e Database
- ✓ Ingest Email (POP3/SMTP normale + PEC)
- ✓ Categorizzazione e Interpretazione LLM
- ✓ Azioni Automatiche
- ✓ Frontend UI completo
- ✓ API Backend
- ✓ Integrazioni Google (Drive + Calendar)
- ✓ Sistema Regole
- ✓ Testing e Deployment

## Architettura
```
┌─────────────────────┐      ┌──────────────────────────┐
│  Email Normale      │──────▶│                          │
│  Email PEC          │      │   SISTEMA CENTRALE       │
└─────────────────────┘      │   - Categorizzazione     │
                             │   - Interpretazione      │
                             │   - Azioni Automatiche   │
                             │   - Regole               │
                             └──────────────────────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    ▼                   ▼                   ▼
            ┌───────────────┐   ┌──────────────┐   ┌─────────────┐
            │ Webmail       │   │ Google Drive │   │ Google Cal  │
            │ (Bozze)       │   │ (Allegati)   │   │ (Eventi)    │
            └───────────────┘   └──────────────┘   └─────────────┘
```

## Stack Tecnologico

**Backend:**
- FastAPI (Python 3.10+)
- PostgreSQL
- SQLAlchemy 2.0
- Celery + Redis
- Ollama (LLM locale)

**Frontend:**
- React 18 + Vite
- TailwindCSS
- TanStack Query
- React Router

**Integrazioni:**
- Google Drive API
- Google Calendar API
- SMTP/POP3/IMAP

## Installation

### Prerequisiti
- Ubuntu 22.04+ (o altra distro Linux)
- Python 3.10+
- PostgreSQL 14+
- Redis
- Ollama
- Node.js 18+

### Quick Start
```bash
# 1. Clone/Download progetto
cd ~/snals-email-agent

# 2. Setup Backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Configura .env
cp .env.example .env
nano .env  # Compila con tue credenziali

# 4. Database setup
alembic upgrade head

# 5. Setup Frontend
cd ../frontend
npm install
npm run build

# 6. Google OAuth setup
cd ../backend
python scripts/setup_google_oauth.py

# 7. Install systemd services
sudo cp deployment/systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable snals-backend snals-celery-worker snals-celery-beat
sudo systemctl start snals-backend snals-celery-worker snals-celery-beat

# 8. Configure Nginx
sudo cp deployment/nginx/snals-email.conf /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/snals-email.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# 9. Setup cron jobs
sudo cp deployment/cron.d/snals-email-agent /etc/cron.d/
```

## Uso

### Accesso UI
```
http://your-domain.com
```

### Monitoraggio
```bash
# Status servizi
./deployment/scripts/monitor.sh

# Logs
tail -f logs/app.log
tail -f logs/email_ingest.log
tail -f logs/errors.log
```

### Backup
```bash
# Backup manuale
./deployment/scripts/backup.sh

# Restore
./deployment/scripts/restore.sh 20241113_120000
```

## Manutenzione

### Aggiornamento Sistema
```bash
./deployment/scripts/deploy.sh production
```

### Database Migrations
```bash
cd backend
source venv/bin/activate
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

### Troubleshooting

**Servizi non partono:**
```bash
sudo systemctl status snals-backend
sudo journalctl -u snals-backend -n 50
```

**Email non vengono elaborate:**
```bash
# Verifica connessioni
python backend/scripts/test_email_connection.py

# Check Celery
sudo systemctl status snals-celery-worker
```

**LLM non risponde:**
```bash
# Verifica Ollama
ollama list
curl http://localhost:11434/api/tags
```

## Documentazione Completa

- [Development Log](docs/DEVELOPMENT_LOG.md)
- [Architecture](docs/ARCHITECTURE.md)
- [API Documentation](docs/API_DOCUMENTATION.md)
- [User Manual](docs/USER_MANUAL.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)

## Supporto

Per problemi o domande, consultare la documentazione in `docs/` o verificare i log di sistema.