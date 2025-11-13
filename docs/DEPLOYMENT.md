# SNALS Email Agent - Guida Deployment

Guida completa per il deployment del sistema in produzione.

## 📋 Indice

- [Deployment con Docker](#deployment-con-docker)
- [Deployment Manuale](#deployment-manuale)
- [Configurazione Nginx](#configurazione-nginx)
- [Systemd Services](#systemd-services)
- [Sicurezza](#sicurezza)
- [Backup](#backup)
- [Monitoring](#monitoring)

---

## 🐳 Deployment con Docker

### Metodo Raccomandato

Il modo più semplice per deployare il sistema è utilizzare Docker Compose.

#### 1. Prerequisiti

```bash
# Docker
docker --version  # >= 20.10
docker-compose --version  # >= 2.0

# Sistema
# - 4GB RAM minimo
# - 20GB spazio disco
# - (Opzionale) GPU NVIDIA per Ollama
```

#### 2. Setup

```bash
# Clone repository
git clone https://github.com/SnalsAI/Snals-Mail.git
cd Snals-Mail

# Configura ambiente
cd backend
cp .env.docker .env
nano .env  # Modifica con credenziali reali

cd ..
```

#### 3. Avvio

```bash
# Build e avvio
make setup

# Verifica
make test
make ps
```

#### 4. Servizi Avviati

- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379  
- **Ollama**: localhost:11434
- **Backend API**: localhost:8001
- **Celery Worker**: background
- **Celery Beat**: background

#### 5. Manutenzione

```bash
# Logs
make logs

# Restart
make restart

# Backup database
docker-compose exec postgres pg_dump -U snals_user snals_email_agent > backup.sql

# Aggiornamento
git pull
make restart
```

### Personalizzazione Docker

#### Cambio Porte

Modifica `docker-compose.yml`:

```yaml
services:
  backend:
    ports:
      - "8080:8001"  # Usa porta 8080
```

#### Volumi Persistenti

```yaml
volumes:
  postgres_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /opt/snals/postgres
```

#### Limiti Risorse

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
```

---

## 🔧 Deployment Manuale

Per deployment senza Docker.

### 1. Prerequisiti Sistema

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3.11 python3.11-venv postgresql redis-server nginx

# CentOS/RHEL
sudo dnf install -y python3.11 postgresql redis nginx
```

### 2. PostgreSQL Setup

```bash
# Crea database e utente
sudo -u postgres psql << EOF
CREATE DATABASE snals_email_agent;
CREATE USER snals_user WITH PASSWORD 'secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE snals_email_agent TO snals_user;
