# SNALS Email Agent - Architettura Sistema

**Versione:** 0.3.0
**Data:** 2025-11-13
**Status:** 🟢 Backend Production Ready

---

## 📊 Overview Sistema

SNALS Email Agent è un sistema completo di automazione gestione email per sindacati scolastici, con analisi LLM, azioni automatiche e integrazione Google Workspace.

### Statistiche
- **Fasi completate:** 7/8 (87.5%)
- **Linee di codice:** ~5000+
- **File Python:** 34
- **Endpoint API:** 30+
- **Servizi Docker:** 6
- **Database models:** 7
- **Celery tasks:** 6

---

## 🏗️ Architettura Generale

```
┌─────────────────────────────────────────────────────────────┐
│                     SNALS Email Agent                        │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Frontend   │───▶│   FastAPI    │───▶│  PostgreSQL  │  │
│  │   React UI   │    │   Backend    │    │   Database   │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│                             │                                │
│                             ▼                                │
│                      ┌──────────────┐                        │
│                      │    Redis     │                        │
│                      │ Message Bus  │                        │
│                      └──────────────┘                        │
│                             │                                │
│          ┌──────────────────┼──────────────────┐            │
│          ▼                  ▼                  ▼             │
│   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐      │
│   │   Celery    │   │   Celery    │   │   Ollama    │      │
│   │   Worker    │   │    Beat     │   │  LLM Local  │      │
│   └─────────────┘   └─────────────┘   └─────────────┘      │
│          │                  │                  │             │
│          └──────────────────┴──────────────────┘            │
│                             │                                │
│                    External Integrations                     │
│          ┌──────────────────┼──────────────────┐            │
│          ▼                  ▼                  ▼             │
│   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐      │
│   │    Email    │   │   Google    │   │   Google    │      │
│   │ POP3/IMAP   │   │   Drive     │   │  Calendar   │      │
│   └─────────────┘   └─────────────┘   └─────────────┘      │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 Stack Tecnologico

### Backend Core
- **FastAPI 0.104.1** - Web framework REST API
- **Python 3.11** - Linguaggio principale
- **SQLAlchemy 2.0.23** - ORM database
- **Alembic 1.12.1** - Database migrations
- **Pydantic 2.5.0** - Validazione dati

### Task Queue & Caching
- **Celery 5.3.4** - Task queue distribuito
- **Celery Beat** - Scheduler task periodici
- **Redis 7** - Message broker + cache

### Database
- **PostgreSQL 15** - Database principale
- **7 tabelle**: emails, interpretazioni, azioni, eventi_calendario, regole, utenti, log_sistema

### LLM & AI
- **Ollama** - LLM locale (GPU support)
  - `llama3.2:3b` - Categorizzazione veloce
  - `mistral:7b` - Interpretazione accurata
- **OpenAI API** - Alternativa cloud
- **Modelli custom** - Supporto modelli personalizzati

### Integrazioni Google
- **Google Drive API** - Upload allegati automatico
- **Google Calendar API** - Sincronizzazione eventi
- **OAuth2** - Autenticazione sicura

### Email
- **POP3/SMTP** - Fetch/send email standard
- **IMAP** - Gestione bozze e cartelle
- **PEC** - Supporto email certificate

### Deployment
- **Docker Compose** - Orchestrazione container
- **Docker** - Containerizzazione
- **Makefile** - Automazione comandi

---

## 📁 Struttura Progetto

```
Snals-Mail/
├── backend/                      # Backend FastAPI
│   ├── app/
│   │   ├── api/
│   │   │   └── routes/          # 4 routers API (30+ endpoints)
│   │   │       ├── emails.py    # Gestione email
│   │   │       ├── azioni.py    # Gestione azioni
│   │   │       ├── regole.py    # Gestione regole
│   │   │       └── calendario.py # Gestione calendario
│   │   ├── models/              # 7 SQLAlchemy models
│   │   │   ├── email.py
│   │   │   ├── interpretazione.py
│   │   │   ├── azione.py
│   │   │   ├── evento.py
│   │   │   ├── regola.py
│   │   │   ├── utente.py
│   │   │   └── log_sistema.py
│   │   ├── services/            # Business logic
│   │   │   ├── email_ingest.py  # Client POP3/SMTP
│   │   │   ├── categorizer.py   # Categorizzatore LLM
│   │   │   ├── interpreter.py   # Interprete LLM
│   │   │   ├── action_executor.py # Esecutore azioni
│   │   │   └── rules_engine.py  # Motore regole
│   │   ├── integrations/        # Integrazioni esterne
│   │   │   ├── llm_client.py    # Client LLM unificato
│   │   │   ├── google_drive_client.py
│   │   │   ├── google_calendar_client.py
│   │   │   └── webmail_client.py
│   │   ├── tasks/               # Celery tasks
│   │   │   ├── email_polling.py # Poll email periodico
│   │   │   └── action_tasks.py  # Esecuzione azioni
│   │   ├── schemas/             # Pydantic schemas
│   │   ├── core/                # Utilities
│   │   ├── config.py            # Configurazione centrale
│   │   └── database.py          # Setup database
│   ├── alembic/                 # Database migrations
│   ├── scripts/                 # Utility scripts
│   │   ├── test_system.py       # Test automatizzati
│   │   └── init_ollama.sh       # Init modelli LLM
│   ├── main.py                  # Entry point FastAPI
│   ├── requirements.txt         # Dipendenze Python
│   ├── Dockerfile               # Container backend
│   └── docker-entrypoint.sh     # Startup script
├── frontend/                    # Frontend React (TODO)
├── docs/                        # Documentazione
│   ├── DEVELOPMENT_LOG.md       # Changelog sviluppo
│   ├── DEPLOYMENT.md            # Guida deployment
│   └── RESUME_GUIDE.md          # Guida ripresa sviluppo
├── docker-compose.yml           # Orchestrazione container
├── Makefile                     # Automazione comandi
├── README.md                    # Documentazione principale
├── DOCKER_README.md             # Guida Docker completa
├── DEPLOYMENT_QUICKSTART.md     # Quick start 5 minuti
└── ARCHITECTURE.md              # Questo file
```

---

## 🔄 Flusso Dati

### 1. Ingest Email (Ogni 120s)
```
POP3 Server → Celery Beat → email_polling task
    ↓
Parse email (headers, body, attachments)
    ↓
Save to DB (Email model)
    ↓
Trigger categorization
```

### 2. Categorizzazione LLM
```
Email text → LLM Client (Ollama/OpenAI)
    ↓
Prompt categorization (8 categorie)
    ↓
Parse JSON response
    ↓
Update Email.categoria + confidence_score
    ↓
Trigger interpretation
```

### 3. Interpretazione
```
Email + Categoria → LLM Client
    ↓
Category-specific prompt
    ↓
Extract structured data (JSON)
    ↓
Save to DB (Interpretazione model)
    ↓
Trigger actions
```

### 4. Azioni Automatiche
```
Rules Engine → Evaluate rules
    ↓
Match conditions → Create actions
    ↓
Save to DB (Azione model)
    ↓
Celery Beat (ogni 60s) → execute_pending_actions
    ↓
Execute action (draft, calendar, drive)
    ↓
Update Azione.stato = COMPLETATA
```

### 5. API Frontend
```
React UI → FastAPI REST API
    ↓
Auth middleware (TODO)
    ↓
Route handler (emails/azioni/regole/calendario)
    ↓
Database query (SQLAlchemy)
    ↓
Pydantic validation
    ↓
JSON response
```

---

## 📮 Categorie Email

Il sistema categorizza automaticamente le email in 8 categorie:

1. **info_generiche** - Richieste informazioni generali
2. **richiesta_appuntamento** - Richieste appuntamento
3. **richiesta_tesseramento** - Richieste iscrizione sindacato
4. **convocazione_scuola** - Convocazioni RSU/riunioni scuola
5. **comunicazione_ust_usr** - Comunicazioni uffici scolastici
6. **comunicazione_scuola** - Comunicazioni da scuole
7. **comunicazione_snals_centrale** - Comunicazioni interne SNALS
8. **varie** - Altre email

---

## 🎯 Azioni Automatiche

Per ogni categoria, il sistema esegue azioni specifiche:

### richiesta_appuntamento
- ✅ Crea bozza risposta (LLM-generated)
- ✅ Crea evento calendario

### convocazione_scuola
- ✅ Crea evento calendario
- ✅ Upload allegati su Google Drive

### comunicazione_ust_usr / comunicazione_scuola
- ✅ Upload allegati su Google Drive (se presenti)

### richiesta_tesseramento
- ✅ Crea bozza risposta con istruzioni
- ✅ Upload allegati su Google Drive

---

## 🔧 Rules Engine

Sistema flessibile per regole personalizzate.

### Condizioni Supportate
- `uguale` / `diverso`
- `contiene` / `non_contiene`
- `inizia_con` / `finisce_con`
- `regex` - Regular expression match
- `maggiore` / `minore` - Confronti numerici
- `in_lista` - Valore in array
- `vuoto` / `non_vuoto`

### Campi Valutabili
- `mittente`, `destinatario`, `oggetto`, `corpo`
- `categoria`, `account_type`
- `has_allegati`, `num_allegati`
- `data_ricezione`
- `interpretazione.*` - Tutti i campi estratti

### Operatori Logici
- `AND` - Tutte le condizioni devono essere vere
- `OR` - Almeno una condizione vera

### Azioni Regole
- `crea_bozza_risposta` - Genera risposta con template
- `crea_evento_calendario` - Crea evento
- `carica_allegati_drive` - Upload su Drive
- `assegna_categoria` - Cambia categoria
- `aggiungi_tag` - Tagga email
- `inoltra_a` - Inoltra a indirizzo
- `marca_come_letto` - Segna letto
- `marca_priorita_alta` - Alta priorità

### Esempio Regola
```json
{
  "nome": "Urgenze al supervisore",
  "condizioni": {
    "operator": "AND",
    "rules": [
      {"field": "oggetto", "condition": "contiene", "value": "urgente"},
      {"field": "account_type", "condition": "uguale", "value": "pec"}
    ]
  },
  "azioni": {
    "actions": [
      {
        "type": "inoltra_a",
        "params": {"to": "supervisore@snals.it"}
      },
      {
        "type": "marca_priorita_alta"
      }
    ]
  },
  "priorita": 100,
  "attiva": true
}
```

---

## 🚀 API Endpoints

### Email (`/api/emails`)
- `GET /` - Lista email (filtri: categoria, stato, search)
- `GET /{id}` - Dettagli email singola
- `PUT /{id}` - Aggiorna email
- `DELETE /{id}` - Elimina email
- `GET /{id}/interpretazione` - Dati interpretati
- `GET /{id}/azioni` - Azioni associate
- `POST /{id}/reprocess` - Riprocessa con LLM

### Azioni (`/api/azioni`)
- `GET /` - Lista azioni (filtri: email_id, tipo, stato)
- `GET /{id}` - Dettagli azione
- `POST /{id}/execute` - Esegui manualmente
- `POST /{id}/retry` - Ritenta fallita
- `DELETE /{id}` - Elimina azione
- `GET /stats/summary` - Statistiche azioni

### Regole (`/api/regole`)
- `GET /` - Lista regole
- `GET /{id}` - Dettagli regola
- `POST /` - Crea nuova regola
- `PUT /{id}` - Aggiorna regola
- `DELETE /{id}` - Elimina regola
- `POST /{id}/toggle` - Attiva/disattiva
- `POST /{id}/test` - Testa su email
- `POST /test-conditions` - Testa condizioni

### Calendario (`/api/calendario`)
- `GET /` - Lista eventi
- `GET /{id}` - Dettagli evento
- `POST /` - Crea evento (+ sync Google)
- `PUT /{id}` - Aggiorna evento
- `DELETE /{id}` - Elimina evento
- `POST /sync-google` - Import da Google Calendar

---

## ⏱️ Celery Tasks

### Task Periodici (Celery Beat)
1. **poll_email_normal** - Ogni 120s
   - Fetch email da account normale
   - Categorizza + interpreta

2. **poll_email_pec** - Ogni 120s
   - Fetch email da PEC
   - Categorizza + interpreta

3. **execute_pending_actions** - Ogni 60s
   - Esegue azioni in stato PENDING
   - Max 10 azioni per run

4. **retry_failed_actions** - Ogni 600s (10 min)
   - Ritenta azioni FALLITE
   - Max 10 azioni per run

### Task On-Demand
5. **create_actions_for_email** - Triggered
   - Crea azioni per email specifica
   - Chiamato da Rules Engine

6. **reprocess_email** - Triggered
   - Ricategorizza + reinterpreta email

---

## 🔒 Sicurezza

### Implementato
- ✅ Pydantic validation su tutti gli input
- ✅ SQLAlchemy ORM (protezione SQL injection)
- ✅ CORS configurato con origini specifiche
- ✅ Environment variables per credenziali
- ✅ .env escluso da Git
- ✅ Docker network isolation

### Da Implementare (Fase 5)
- 🔲 JWT Authentication
- 🔲 Rate limiting API
- 🔲 HTTPS/TLS
- 🔲 Password hashing (bcrypt)
- 🔲 Role-based access control (RBAC)
- 🔲 Audit logging

---

## 📊 Database Schema

```sql
-- Email principale
emails (id, message_id, mittente, oggetto, corpo_testo, corpo_html,
        data_ricezione, account_type, categoria, stato, letto,
        confidence_score, allegati, note)

-- Interpretazione LLM
interpretazioni (id, email_id, dati_estratti, creata_at)

-- Azioni automatiche
azioni (id, email_id, tipo_azione, stato, parametri, risultato,
        errore, creata_at, eseguita_at)

-- Eventi calendario
eventi_calendario (id, email_id, titolo, data_inizio, data_fine,
                   luogo, descrizione, partecipanti, google_event_id,
                   sincronizzato_google)

-- Regole personalizzate
regole (id, nome, descrizione, condizioni, azioni, priorita, attiva)

-- Utenti sistema (TODO)
utenti (id, username, email, hashed_password, ruolo, attivo)

-- Log sistema
log_sistema (id, tipo, messaggio, dettagli, timestamp)
```

---

## 🧪 Testing

### Test Automatizzati
```bash
# Test sistema completo
python backend/scripts/test_system.py

# Test include:
# 1. Health check API
# 2. Database connection
# 3. LLM categorizer
# 4. LLM interpreter
# 5. Email save & retrieve
```

### Test Manuali
```bash
# Test API endpoints
curl http://localhost:8001/health
curl http://localhost:8001/api/emails/

# Test Celery tasks
celery -A app.tasks inspect active
celery -A app.tasks inspect scheduled

# Test database
psql -U snals_user -d snals_email_agent -c "SELECT COUNT(*) FROM emails;"
```

---

## 🚀 Deployment

### Development
```bash
make setup      # Build + start + init
make test       # Run tests
make logs       # View logs
make down       # Stop all
```

### Production
Vedi `docs/DEPLOYMENT.md` per:
- Setup server Linux
- Nginx reverse proxy
- Systemd services
- SSL/TLS (Let's Encrypt)
- Backup automatico
- Monitoring (Prometheus/Grafana)

---

## 📈 Performance

### Metriche Attese
- **Categorizzazione email:** ~2-3s (Ollama local)
- **Interpretazione email:** ~3-5s (Ollama local)
- **API response time:** <100ms (queries semplici)
- **Polling interval:** 120s (configurabile)
- **Action execution:** 60s (configurabile)

### Scalabilità
- **Celery workers:** Scalabile orizzontalmente
- **Database:** PostgreSQL può gestire milioni di email
- **Redis:** Cache in-memory per performance
- **Ollama:** GPU-accelerated per LLM veloci

---

## 🔮 Roadmap

### ✅ Completato (v0.3.0)
- FASE 1: Setup iniziale
- FASE 2: Ingest email
- FASE 3: LLM categorizzazione/interpretazione
- FASE 4: Azioni automatiche
- FASE 6: API complete
- FASE 7: Rules engine
- FASE 8: Docker & deployment

### 🔲 Da Fare (v0.4.0)
- FASE 5: Frontend React completo
  - Dashboard con statistiche
  - Gestione email UI
  - Calendario integrato
  - Builder regole visuale drag&drop
  - Configurazione sistema

### 🔮 Future (v0.5.0+)
- Autenticazione JWT multi-utente
- Mobile app (React Native)
- Plugin sistema per estensioni
- Machine learning per ottimizzazione regole
- Export/import configurazioni
- Multi-tenancy per più sedi SNALS
- Integrazione Telegram bot

---

## 📞 Supporto

- **Documentazione:** Vedi `README.md`, `DOCKER_README.md`
- **Issues:** GitHub Issues
- **Logs:** `logs/` directory
- **Development:** Vedi `docs/DEVELOPMENT_LOG.md`

---

**Creato da:** Claude (Anthropic)
**Licenza:** [Specificare]
**Ultimo aggiornamento:** 2025-11-13
