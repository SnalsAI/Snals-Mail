# 🚀 Quick Start - Deployment

Guida rapida per avviare il sistema SNALS Email Agent.

## ⚡ Opzione 1: Docker (Raccomandato)

### Setup in 5 minuti

```bash
# 1. Clone
git clone https://github.com/SnalsAI/Snals-Mail.git
cd Snals-Mail

# 2. Configura credenziali email
cd backend
cp .env.docker .env
nano .env  # Modifica EMAIL_* con le tue credenziali

# 3. Avvia tutto
cd ..
make setup

# 4. Test
make test
```

### Servizi Disponibili

- **API**: http://localhost:8001
- **Docs**: http://localhost:8001/docs
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379
- **Ollama**: localhost:11434

### Comandi Utili

```bash
make help      # Mostra tutti i comandi
make logs      # Visualizza logs
make ps        # Status servizi
make restart   # Riavvia
make clean     # Pulizia completa
```

## 🔧 Opzione 2: Manuale

### Prerequisiti

- Python 3.11+
- PostgreSQL
- Redis
- Ollama

### Setup

```bash
# Backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Database
createdb snals_email_agent
alembic upgrade head

# Ollama models
ollama pull llama3.2:3b
ollama pull mistral:7b

# Config
cp .env.example .env
nano .env

# Avvia (3 terminali)
python main.py  # Terminal 1
celery -A app.tasks worker --loglevel=info  # Terminal 2
celery -A app.tasks beat --loglevel=info  # Terminal 3
```

## 📚 Documentazione Completa

- **Docker**: [DOCKER_README.md](DOCKER_README.md)
- **Deployment**: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- **Sviluppo**: [docs/RESUME_GUIDE.md](docs/RESUME_GUIDE.md)
- **API**: http://localhost:8001/docs (dopo avvio)

## ✅ Verifica Funzionamento

```bash
# API Health
curl http://localhost:8001/health

# Test completo
make test  # Con Docker
# oppure
python backend/scripts/test_system.py  # Manuale
```

Output atteso:
```
✅ API Health           PASS
✅ Database            PASS  
✅ LLM Categorizer     PASS
✅ LLM Interpreter     PASS
✅ Save Email          PASS

🎉 Tutti i test sono passati!
```

## 🐛 Problemi?

```bash
# Verifica logs
make logs  # Docker
# oppure
tail -f logs/app.log  # Manuale

# Troubleshooting
cat DOCKER_README.md | grep "Troubleshooting" -A 50
```

## 📞 Supporto

- GitHub Issues: https://github.com/SnalsAI/Snals-Mail/issues
- Documentazione: [docs/](docs/)

---

**Tempo setup**: ~5 minuti con Docker, ~15 minuti manuale  
**Stato**: 🟢 Pronto per produzione (configurare credenziali reali)
