# SNALS Email Agent - Docker Setup

Guida completa per eseguire il sistema con Docker Compose.

## 🚀 Quick Start

### Prerequisiti

- Docker 20.10+
- Docker Compose 2.0+
- 4GB RAM minimo
- (Opzionale) NVIDIA GPU per Ollama

### Setup Rapido

```bash
# 1. Clone repository
git clone https://github.com/SnalsAI/Snals-Mail.git
cd Snals-Mail

# 2. Configura variabili ambiente
cd backend
cp .env.example .env
# Modifica .env con le tue credenziali email

# 3. Avvia tutto
cd ..
make setup

# 4. Verifica funzionamento
make test
```

## 📋 Comandi Disponibili

```bash
make help          # Mostra tutti i comandi disponibili
make build         # Build container
make up            # Avvia servizi
make down          # Ferma servizi
make restart       # Riavvia servizi
make logs          # Mostra logs
make test          # Test sistema
make clean         # Pulizia completa
```

## 🏗️ Architettura Docker

```
┌─────────────────────────────────────────────────────────┐
│                     Docker Network                       │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │PostgreSQL│  │  Redis   │  │  Ollama  │             │
│  │  :5432   │  │  :6379   │  │  :11434  │             │
│  └─────┬────┘  └─────┬────┘  └─────┬────┘             │
│        │             │              │                   │
│        └─────────────┴──────────────┘                   │
│                      │                                   │
│        ┌─────────────┴─────────────┐                   │
│        │                           │                    │
│  ┌─────▼──────┐  ┌────────────┐  ┌─────────────┐     │
│  │  Backend   │  │   Celery   │  │ Celery Beat │     │
│  │   FastAPI  │  │   Worker   │  │  Scheduler  │     │
│  │   :8001    │  └────────────┘  └─────────────┘     │
│  └────────────┘                                        │
│                                                         │
└─────────────────────────────────────────────────────────┘
           │
           ▼
    http://localhost:8001
```

## 📦 Servizi

### PostgreSQL
- **Porta**: 5432
- **Database**: snals_email_agent
- **User**: snals_user
- **Password**: snals_password (configurabile)
- **Volume**: `postgres_data`

### Redis
- **Porta**: 6379
- **Volume**: `redis_data`
- **Uso**: Message broker per Celery

### Ollama
- **Porta**: 11434
- **Volume**: `ollama_data`
- **Modelli**: llama3.2:3b, mistral:7b
- **GPU**: Opzionale (NVIDIA)

### Backend (FastAPI)
- **Porta**: 8001
- **Endpoints**:
  - `GET /` - Info API
  - `GET /health` - Health check
  - `GET /docs` - Swagger UI

### Celery Worker
- **Task**: Elaborazione asincrona
- **Queue**: Redis

### Celery Beat
- **Task**: Scheduling periodico
- **Polling email**: Ogni 120s

## ⚙️ Configurazione

### Variabili Ambiente

Modifica `backend/.env`:

```bash
# Database (auto-configurato in Docker)
DATABASE_URL=postgresql://snals_user:snals_password@postgres:5432/snals_email_agent

# Email Account Normale
EMAIL_NORMAL_POP3_HOST=pop.yourdomain.com
EMAIL_NORMAL_POP3_USER=snals@yourdomain.com
EMAIL_NORMAL_POP3_PASSWORD=your_password

# Email Account PEC
EMAIL_PEC_POP3_HOST=pop.pec.yourdomain.com
EMAIL_PEC_POP3_USER=snals@pec.it
EMAIL_PEC_POP3_PASSWORD=your_password

# LLM (auto-configurato in Docker)
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://ollama:11434

# Redis (auto-configurato in Docker)
REDIS_URL=redis://redis:6379/0
```

### Personalizzazione docker-compose.yml

**Cambiare porte esposte:**

```yaml
services:
  backend:
    ports:
      - "8080:8001"  # Usa porta 8080 invece di 8001
```

**Disabilitare GPU per Ollama:**

```yaml
services:
  ollama:
    # Rimuovi sezione deploy.resources
    image: ollama/ollama:latest
    # ... resto configurazione
```

## 🧪 Testing

### Test Completo Sistema

```bash
make test
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

### Test Manuale API

```bash
# Health check
curl http://localhost:8001/health

# Documentazione interattiva
open http://localhost:8001/docs
```

### Verifica Logs

```bash
# Tutti i servizi
make logs

# Solo backend
make logs-backend

# Solo Celery
make logs-celery
```

## 🔍 Troubleshooting

### Container non si avvia

```bash
# Verifica status
make ps

# Controlla logs
make logs

# Ricostruisci
make clean
make build
make up
```

### Database non raggiungibile

```bash
# Verifica PostgreSQL
docker-compose exec postgres pg_isready -U snals_user

# Connessione manuale
make shell-db
```

### Ollama non risponde

```bash
# Verifica servizio
curl http://localhost:11434/api/tags

# Scarica modelli
make init-ollama

# Logs Ollama
docker-compose logs ollama
```

### Problemi Celery

```bash
# Verifica worker
docker-compose exec celery-worker celery -A app.tasks inspect active

# Restart worker
docker-compose restart celery-worker celery-beat
```

## 📊 Monitoraggio

### Status Servizi

```bash
make ps
```

Output:
```
NAME                  STATUS    PORTS
snals-postgres        Up        0.0.0.0:5432->5432/tcp
snals-redis           Up        0.0.0.0:6379->6379/tcp
snals-ollama          Up        0.0.0.0:11434->11434/tcp
snals-backend         Up        0.0.0.0:8001->8001/tcp
snals-celery-worker   Up
snals-celery-beat     Up
```

### Uso Risorse

```bash
docker stats
```

### Volumi

```bash
docker volume ls | grep snals
```

## 🛠️ Manutenzione

### Backup Database

```bash
# Export
docker-compose exec postgres pg_dump -U snals_user snals_email_agent > backup.sql

# Import
docker-compose exec -T postgres psql -U snals_user snals_email_agent < backup.sql
```

### Aggiornamento Codice

```bash
git pull origin main
docker-compose restart backend celery-worker celery-beat
```

### Pulizia Volumi

```bash
# Attenzione: cancella tutti i dati!
make clean
```

## 🚀 Deployment Produzione

### Modifiche Necessarie

1. **Variabili Ambiente**:
   ```bash
   DEBUG=false
   SECRET_KEY=<generate-secure-key>
   ```

2. **Password Database**:
   - Cambia password in docker-compose.yml
   - Aggiorna DATABASE_URL in .env

3. **Reverse Proxy**:
   - Aggiungi Nginx davanti al backend
   - Configura SSL/TLS

4. **Volumi Persistenti**:
   - Usa volumi named o bind mounts
   - Backup regolari

5. **Logging**:
   - Centralizza logs (es. ELK stack)
   - Configura log rotation

### Nginx Setup (Opzionale)

Vedi `deployment/nginx/snals-email.conf` per configurazione.

## 📚 Risorse

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose](https://docs.docker.com/compose/)
- [FastAPI Docker](https://fastapi.tiangolo.com/deployment/docker/)
- [PostgreSQL Docker](https://hub.docker.com/_/postgres)

## 🆘 Supporto

Per problemi o domande:
1. Controlla troubleshooting sopra
2. Verifica logs: `make logs`
3. Apri issue su GitHub

---

**Versione**: 1.0  
**Ultimo aggiornamento**: 2025-11-13
