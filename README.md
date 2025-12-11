# SNALS Email Agent

Sistema automatico di gestione email per sindacato scuola SNALS con analisi LLM e intelligenza artificiale.

[![Status](https://img.shields.io/badge/status-production%20ready-green)]()
[![Docker](https://img.shields.io/badge/docker-supported-blue)]()
[![Python](https://img.shields.io/badge/python-3.11-blue)]()
[![React](https://img.shields.io/badge/react-18-blue)]()

## 🎯 Funzionalità Principali

- ✅ **Email Processing Automatico** - Polling ogni 2 minuti con elaborazione intelligente
- ✅ **Categorizzazione LLM** - 8 categorie con confidence scoring e fallback Ollama
- ✅ **Interpretazione Strutturata** - Estrazione dati da email con LLM (llama3.2:3b)
- ✅ **Azioni Automatiche** - Sistema regole con esecuzione automatica (eventi, interpelli, upload)
- ✅ **Calendario Eventi** - Creazione automatica eventi da convocazioni + Google Calendar sync
- ✅ **Parsing Interpelli** - Estrazione automatica interpelli con strategia smart (regex + LLM)
- ✅ **RAG Knowledge Base** - Sistema di indicizzazione documenti con ChromaDB
- ✅ **Chat RAG con LLM** - Interfaccia conversazionale per interrogare la knowledge base
- ✅ **Upload Google Drive** - Sincronizzazione automatica allegati
- ✅ **Frontend React** - Dashboard moderna con statistiche, grafici e gestione completa
- ✅ **API REST Complete** - 30+ endpoints con documentazione Swagger

## 📋 Stato Progetto

### ✅ FASE 1-8: Sistema Completo (100%)
- [x] Setup iniziale (Docker, database, migrations)
- [x] Ingest email (POP3/SMTP normale + PEC)
- [x] Categorizzazione & Interpretazione LLM
- [x] Azioni automatiche con regole
- [x] Frontend React completo
- [x] API REST complete
- [x] Rules Engine avanzato
- [x] Testing & Deployment

### 🆕 NUOVE FUNZIONALITÀ (Sessione Corrente)
- [x] **Sistema azioni completamente automatico**
  - Creazione azioni dopo ogni email processata
  - Esecuzione asincrona in background
  - Supporto PARSE_INTERPELLO per estrazione interpelli

- [x] **Eventi Calendario Automatici**
  - Creazione eventi da convocazioni
  - Estrazione data/ora/luogo con SmartExtractor
  - Sync con Google Calendar
  - 1+ eventi creati e testati

- [x] **Parsing Interpelli Avanzato**
  - Estrazione automatica classe concorso, scuola, data scadenza
  - Strategia smart: regex + LLM validation
  - 1+ interpelli estratti e salvati

- [x] **Ottimizzazione Performance**
  - Batch size ridotto: 50 → 3 email per evitare timeout Ollama
  - Error handling migliorato con try/except isolati
  - Nessun rollback totale su errori singoli

- [x] **Chat RAG con Knowledge Base**
  - Endpoint `/api/rag/chat` per query conversazionali
  - Interfaccia chat moderna nel frontend
  - Risposta LLM basata su documenti rilevanti
  - Citazione fonti con metadati completi
  - 8 documenti attualmente indicizzati

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

- **Frontend Web UI**: http://localhost:3001
- **API REST**: http://localhost:8001
- **Swagger Docs**: http://localhost:8001/docs
- **PostgreSQL**: localhost:5433
- **Redis**: localhost:6380
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

## 📊 Architettura Sistema

```
┌─────────────────────────────────────────────────────────┐
│              Email Server (POP3/SMTP)                    │
└───────────────────┬─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│          Celery Worker (Email Polling)                   │
│  • Polling ogni 2 minuti                                 │
│  • Batch: 3 email per volta (ottimizzato Ollama)        │
└───────────────────┬─────────────────────────────────────┘
                    │
    ┌───────────────┼───────────────┐
    │               │               │
    ▼               ▼               ▼
┌─────────┐  ┌─────────────┐  ┌─────────────┐
│ Catego- │  │ Interpreta- │  │  Estrazione │
│ rizza   │  │   zione     │  │  PDF Text   │
│ (Rules+ │  │  (LLM 3b)   │  │  (pdfplumber│
│  LLM)   │  │             │  │  + PyPDF2)  │
└────┬────┘  └──────┬──────┘  └──────┬──────┘
     │              │                │
     └──────────────┼────────────────┘
                    │
                    ▼
           ┌────────────────┐
           │   PostgreSQL   │
           │   • emails     │
           │   • interpreta │
           │   • azioni ✨   │
           │   • eventi 📅  │
           │   • interpelli │
           └────────┬───────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│            Action Executor (Celery Tasks)                │
│  • EVENTO_CALENDARIO → Crea evento + Google sync        │
│  • PARSE_INTERPELLO → Estrai dati interpello            │
│  • UPLOAD_DRIVE → Upload allegati su Drive              │
│  • SINTESI → Genera sintesi con LLM                     │
│  • INDICIZZA_RAG → Indicizza in ChromaDB ✨             │
└─────────────────────────────────────────────────────────┘
                    │
    ┌───────────────┼───────────────┐
    │               │               │
    ▼               ▼               ▼
┌─────────┐  ┌─────────────┐  ┌─────────────┐
│ Google  │  │   Google    │  │  ChromaDB   │
│Calendar │  │    Drive    │  │  Vector DB  │
│         │  │             │  │   (RAG) ✨   │
└─────────┘  └─────────────┘  └──────┬──────┘
                                      │
                    ┌─────────────────┘
                    │
                    ▼
           ┌────────────────┐
           │  Chat RAG API  │
           │  • Query docs  │
           │  • LLM answer  │
           │  • Sources ✨  │
           └────────┬───────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│          FastAPI REST API (8001)                         │
│  30+ endpoints: emails, actions, rules, calendar, RAG ✨ │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│          React Frontend (3001)                           │
│  • Dashboard con stats                                   │
│  • Email management                                      │
│  • Calendario eventi                                     │
│  • Chat RAG ✨ (Nuova!)                                  │
│  • Interpelli + Classi Concorso                         │
│  • Rules & Actions                                       │
└─────────────────────────────────────────────────────────┘
```

✨ = Funzionalità nuove/aggiornate

## 🗂️ Struttura Progetto

```
Snals-Mail/
├── docker-compose.yml          # Docker orchestration
├── Makefile                    # Comandi utili
│
├── backend/
│   ├── Dockerfile              # Container backend
│   ├── main.py                 # FastAPI entry point
│   ├── requirements.txt        # Dependencies
│   │
│   ├── app/
│   │   ├── config.py          # Settings (EMAIL_FETCH_LIMIT=3 ✨)
│   │   ├── database.py        # SQLAlchemy setup
│   │   │
│   │   ├── models/            # Database models
│   │   │   ├── email.py       # Email model
│   │   │   ├── azione.py      # Action model (con PARSE_INTERPELLO ✨)
│   │   │   ├── interpello.py  # Interpello model
│   │   │   └── evento_calendario.py  # Calendar event
│   │   │
│   │   ├── services/          # Business logic
│   │   │   ├── categorizer.py         # Email categorization
│   │   │   ├── interpreter.py         # Data extraction
│   │   │   ├── action_executor.py     # Action orchestrator ✨
│   │   │   ├── rules_engine.py        # Rules evaluation ✨
│   │   │   ├── rag_service.py         # RAG + Chat ✨
│   │   │   └── smart_convocazione_extractor.py  # Event data
│   │   │
│   │   ├── api/routes/        # API endpoints
│   │   │   ├── emails.py
│   │   │   ├── azioni.py
│   │   │   ├── calendar.py
│   │   │   ├── interpelli.py
│   │   │   └── rag.py         # RAG + Chat endpoints ✨
│   │   │
│   │   ├── tasks/             # Celery tasks
│   │   │   ├── email_polling.py      # Email polling ✨
│   │   │   ├── action_tasks.py       # Action execution ✨
│   │   │   └── interpello_tasks.py   # Interpello parsing
│   │   │
│   │   └── integrations/      # External integrations
│   │       ├── llm_client.py         # Ollama + OpenAI
│   │       ├── google_drive.py
│   │       └── google_calendar.py
│   │
│   └── storage/               # File storage
│       ├── attachments/       # Email attachments
│       ├── chroma_db/         # ChromaDB vector store ✨
│       └── repository/        # Knowledge base docs
│
└── frontend/
    ├── src/
    │   ├── pages/
    │   │   ├── Dashboard.tsx        # Main dashboard
    │   │   ├── Emails.tsx           # Email list
    │   │   ├── Calendar.tsx         # Calendar view
    │   │   ├── Interpelli.tsx       # Interpelli management
    │   │   ├── ChatRAG.tsx          # Chat interface ✨ NUOVO!
    │   │   └── ...
    │   │
    │   └── components/
    │       └── Layout.tsx           # Navigation (+ Chat RAG link ✨)
    │
    └── package.json
```

## 🤖 Sistema di Azioni Automatiche

### Flusso Automatico

```
Email Ricevuta
    │
    ├─▶ Categorizzata (rules + LLM fallback)
    │
    ├─▶ Interpretata (LLM estrae dati strutturati)
    │
    ├─▶ Salvata in database
    │
    └─▶ create_actions_for_email() schedulato ✨
            │
            ├─▶ RulesEngine valuta regole attive
            │
            ├─▶ Crea azioni basate su categoria/sottocategoria
            │   │
            │   ├─▶ EVENTO_CALENDARIO (per convocazioni)
            │   ├─▶ PARSE_INTERPELLO (per interpelli)
            │   ├─▶ UPLOAD_DRIVE (per UST/USR)
            │   ├─▶ SINTESI (per comunicazioni)
            │   └─▶ INDICIZZA_RAG (per knowledge base)
            │
            └─▶ execute_pending_actions() (ogni minuto)
                    │
                    ├─▶ Esegue azioni IN_CODA
                    ├─▶ Aggiorna stato (COMPLETATA/FALLITA)
                    └─▶ Salva risultati
```

### Tipi di Azioni Supportate

| Tipo Azione | Descrizione | Trigger Automatico |
|-------------|-------------|-------------------|
| `EVENTO_CALENDARIO` | Crea evento calendario | Convocazioni scuole |
| `PARSE_INTERPELLO` | Estrae dati interpello | Email interpelli UST/USR |
| `UPLOAD_DRIVE` | Carica allegati su Drive | UST/USR, SNALS centrale |
| `SINTESI` | Genera sintesi con LLM | Comunicazioni scuole |
| `INDICIZZA_RAG` | Indicizza nel vector DB | Tutti i documenti |
| `BOZZA_RISPOSTA` | Genera risposta automatica | Info generiche |
| `INOLTRA_DELEGATI_ZONA` | Inoltra a delegati zona | Convocazioni RSU |

### Configurazione Batch Size

```python
# backend/app/config.py
EMAIL_FETCH_LIMIT = 3  # ✨ Ridotto per evitare timeout Ollama

# backend/.env
EMAIL_FETCH_LIMIT=3
```

**Perché 3?** Ollama processa una richiesta LLM alla volta. Con 3 email per batch:
- Nessun timeout (ogni email ~30-40 sec)
- Processing completo in ~2 minuti
- Sistema stabile e resiliente

## 💬 Chat RAG - Nuova Funzionalità

### Accesso
Frontend: **http://localhost:3001/chat-rag**

### Funzionalità

1. **Interfaccia Conversazionale**
   - Chat moderna con messaggi utente/assistente
   - Typing indicator durante elaborazione
   - Timestamp per ogni messaggio

2. **Query Intelligente**
   - Similarity search su ChromaDB (embedding multilingua)
   - Recupero top 5 documenti rilevanti
   - Costruzione contesto per LLM

3. **Risposta LLM**
   - Generazione con llama3.2:3b
   - Risposta basata SOLO sui documenti trovati
   - Citazione delle fonti

4. **Visualizzazione Fonti**
   - Espandibile per ogni risposta
   - Metadati completi (filename, mittente, data, categoria)
   - Snippet di testo rilevante
   - Score di rilevanza

### API Endpoint

```bash
# Query conversazionale
POST /api/rag/chat
{
  "query": "Quali sono le scadenze per gli interpelli?",
  "n_results": 5,
  "filter_categoria": "comunicazione_ust_usr"  # opzionale
}

# Risposta
{
  "query": "...",
  "answer": "Risposta generata dal LLM basata sui documenti...",
  "sources": [
    {
      "document": "testo del documento...",
      "metadata": {
        "filename": "interpello.pdf",
        "mittente": "UST...",
        "data": "2025-11-20",
        "categoria": "comunicazione_ust_usr"
      },
      "distance": 0.3
    }
  ],
  "sources_count": 3
}
```

### Documenti Indicizzati

Vengono automaticamente indicizzati:
- ✅ Email da `info@snals.it` (comunicazioni SNALS)
- ✅ Email categoria `comunicazione_ust_usr` (UST/USR)
- ✅ Allegati PDF estratti
- ✅ Documenti Knowledge Base

**Statistiche attuali:** 8 documenti indicizzati

## 📝 Categorie Email

Il sistema categorizza automaticamente in 8 categorie con sottocategorie:

| Categoria | Sottocategorie | Azioni Automatiche |
|-----------|----------------|-------------------|
| `CONVOCAZIONE_SCUOLA` | Convocazione, Convocazione RSU | EVENTO_CALENDARIO, SEGNA_IMPORTANTE |
| `COMUNICAZIONE_UST_USR` | Interpello, Comunicazione | PARSE_INTERPELLO, UPLOAD_DRIVE, INDICIZZA_RAG |
| `COMUNICAZIONE_SCUOLA` | Comunicazione | SINTESI, ARCHIVIA |
| `INFO_GENERICHE` | - | BOZZA_RISPOSTA (manuale) |
| `RICHIESTA_APPUNTAMENTO` | - | BOZZA_APPUNTAMENTO (manuale) |
| `RICHIESTA_TESSERAMENTO` | - | BOZZA_TESSERAMENTO (manuale) |
| `COMUNICAZIONE_SNALS_CENTRALE` | - | UPLOAD_DRIVE, INDICIZZA_RAG |
| `VARIE` | - | Nessuna azione automatica |

## 🔧 Stack Tecnologico

**Backend:**
- FastAPI 0.104 - Web framework
- SQLAlchemy 2.0 - ORM
- Alembic - Database migrations
- Celery 5.3 - Task queue
- Redis - Message broker
- ChromaDB - Vector database ✨
- Sentence Transformers - Embeddings multilingua ✨

**Frontend:**
- React 18 - UI framework
- TypeScript - Type safety
- TailwindCSS - Styling
- React Router - Routing
- Axios - HTTP client
- Lucide React - Icons

**Database:**
- PostgreSQL 15 - Primary database

**LLM:**
- Ollama - Local LLM inference
  - llama3.2:1b (categorization)
  - llama3.2:3b (interpretation + chat ✨)
- OpenAI API - Alternative provider (gpt-4o-mini)

**Integrazioni:**
- Google Calendar API
- Google Drive API
- POP3/SMTP (email server)

## 🧪 Testing

### Test Automatici

```bash
# Con Docker
make test

# Test completo sistema
docker exec snals-backend python /app/test_create_actions.py

# Test chat RAG
curl -X POST http://localhost:8001/api/rag/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "Cosa dicono i documenti sugli interpelli?", "n_results": 5}'
```

### Verifica Stato Sistema

```bash
# Health check
curl http://localhost:8001/health

# Statistiche RAG
curl http://localhost:8001/api/rag/statistics

# Database stats
docker exec snals-postgres psql -U snals_user -d snals_email_agent -c "
  SELECT
    (SELECT COUNT(*) FROM emails) as emails,
    (SELECT COUNT(*) FROM azioni) as azioni,
    (SELECT COUNT(*) FROM eventi_calendario) as eventi,
    (SELECT COUNT(*) FROM interpelli) as interpelli;
"
```

Output atteso:
```
 emails | azioni | eventi | interpelli
--------+--------+--------+------------
      9 |     14 |      1 |          1
```

## 📚 Documentazione Completa

- **[DOCKER_README.md](DOCKER_README.md)** - Guida completa Docker
- **[DEPLOYMENT_QUICKSTART.md](DEPLOYMENT_QUICKSTART.md)** - Quick start deployment
- **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Deployment produzione
- **[docs/RESUME_GUIDE.md](docs/RESUME_GUIDE.md)** - Guida sviluppo
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Architettura dettagliata
- **[docs/API_DOCUMENTATION.md](docs/API_DOCUMENTATION.md)** - API reference

## 🔒 Sicurezza

- Password database forti
- SECRET_KEY generata casualmente
- SSL/TLS per produzione
- Rate limiting Nginx
- Firewall configurato
- Environment variables per credenziali
- Google Service Account per API

## 💾 Backup

### Database

```bash
# Backup completo
docker exec snals-postgres pg_dump -U snals_user snals_email_agent > backup_$(date +%Y%m%d).sql

# Backup con compressione
docker exec snals-postgres pg_dump -U snals_user snals_email_agent | gzip > backup_$(date +%Y%m%d).sql.gz

# Restore
docker exec -i snals-postgres psql -U snals_user snals_email_agent < backup.sql
```

### Storage & ChromaDB

```bash
# Backup completo storage
tar -czf backup-storage-$(date +%Y%m%d).tar.gz \
  backend/storage/ \
  backend/.env

# Restore
tar -xzf backup-storage-YYYYMMDD.tar.gz
```

## 🔄 Aggiornamento

```bash
# Pull nuovo codice
git pull origin main

# Con Docker
docker-compose down
docker-compose build
docker-compose up -d

# Verifica migrations
docker exec snals-backend alembic current
docker exec snals-backend alembic upgrade head

# Restart servizi
docker restart snals-backend snals-celery-worker
```

## 🐛 Troubleshooting

### Email non vengono processate

```bash
# Verifica Celery worker
docker logs snals-celery-worker --tail 50

# Verifica polling
docker logs snals-celery-worker | grep "Polling completato"

# Output atteso: "Polling completato: X nuove email su Y processate"
```

### Ollama timeout

```bash
# Verifica batch size
docker exec snals-backend cat /app/.env | grep EMAIL_FETCH_LIMIT
# Deve essere: EMAIL_FETCH_LIMIT=3

# Verifica Ollama
curl http://localhost:11434/api/tags

# Logs Ollama
docker logs snals-ollama --tail 100
```

### Azioni non vengono create

```bash
# Verifica task schedulati
docker logs snals-celery-worker | grep "Task creazione azioni"

# Verifica azioni nel database
docker exec snals-postgres psql -U snals_user -d snals_email_agent -c \
  "SELECT tipo, stato, COUNT(*) FROM azioni GROUP BY tipo, stato;"
```

### Chat RAG non risponde

```bash
# Verifica documenti indicizzati
curl http://localhost:8001/api/rag/statistics

# Test query diretta
curl -X POST http://localhost:8001/api/rag/query \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "n_results": 3}'

# Verifica ChromaDB
docker exec snals-backend ls -la /app/storage/chroma_db/
```

### Frontend non carica

```bash
# Verifica frontend container
docker ps | grep snals-frontend

# Logs frontend
docker logs snals-frontend --tail 50

# Rebuild se necessario
docker-compose build snals-frontend
docker-compose up -d snals-frontend
```

## 📊 Performance & Monitoring

### Metriche Chiave

- **Email Processing**: ~30-40 sec/email (con LLM)
- **Batch Size**: 3 email ogni 2 minuti
- **Throughput**: ~90 email/ora max
- **LLM Timeout**: 60 sec (Ollama)
- **Action Execution**: 1/minuto in background

### Monitoring

```bash
# Container stats
docker stats snals-backend snals-celery-worker snals-ollama

# Database connections
docker exec snals-postgres psql -U snals_user -d snals_email_agent -c \
  "SELECT count(*) FROM pg_stat_activity WHERE datname='snals_email_agent';"

# Disk usage
docker exec snals-backend du -sh /app/storage/*
```

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
- [ChromaDB Docs](https://docs.trychroma.com)
- [React Docs](https://react.dev)

## 📞 Supporto

- **Issues**: https://github.com/SnalsAI/Snals-Mail/issues
- **Documentazione**: [docs/](docs/)

---

**Versione:** 1.1.0
**Ultimo aggiornamento:** 2025-11-20
**Status:** 🟢 Production Ready - Full Stack Complete + RAG Chat

### 🎉 Nuove Features v1.1.0

- ✨ **Chat RAG** con interfaccia conversazionale e LLM
- ✨ **Sistema azioni automatico** completamente funzionante
- ✨ **Eventi calendario** creati automaticamente da convocazioni
- ✨ **Interpelli** estratti e salvati automaticamente
- ✨ **Performance ottimizzate** con batch size 3 per Ollama
- ✨ **Error handling robusto** senza rollback totali

**Statistiche:**
- **Endpoint API:** 35+ (5 nuovi per RAG)
- **Frontend Pages:** 12 (1 nuova: Chat RAG)
- **Database Tables:** 10+
- **Celery Tasks:** 15+
- **Vector Store:** ChromaDB con 8 documenti
- **Email Processing:** 9 email processate correttamente
- **Azioni Eseguite:** 13/14 completate con successo
- **Eventi Creati:** 1 evento calendario
- **Interpelli Estratti:** 1 interpello

**Tempo setup:** ~5 minuti con Docker
**Tempo processing email:** ~30-40 sec/email
**Uptime:** Stabile 24/7 ✅
