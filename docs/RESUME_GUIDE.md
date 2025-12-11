# Guida Ripresa Sviluppo - SNALS Email Agent

## Stato Attuale: v1.4.0 (Dicembre 2025)

Sistema **COMPLETO e IN PRODUZIONE** con tutte le funzionalità core implementate.

---

## Panoramica Rapida

### Cosa Fa il Sistema

1. **Email Processing** - Riceve email via POP3 (normale + PEC) ogni 2 minuti
2. **Classificazione** - Categorizza con ML/LLM (8 categorie + sottocategorie)
3. **Automazione** - Crea eventi calendario, estrae interpelli, genera bozze
4. **Integrazioni** - Google Calendar, Google Drive, RAG chat

### Funzionalità Recenti (v1.4.0)

- Gestione rinvii/annullamenti eventi calendario
- Eliminazione email spam dal server
- Rate limiting per prevenire blocchi IP
- Sistema anomalie calendario

---

## Quick Start

### 1. Avvia Servizi

```bash
cd /home/ubuntu/Snals-Mail

# Avvia tutto con Docker Compose
docker-compose up -d

# Verifica stato
docker-compose ps

# Logs in tempo reale
docker-compose logs -f backend
```

### 2. Verifica Funzionamento

```bash
# Health check
curl http://localhost:8000/api/health

# Lista email recenti
curl http://localhost:8000/api/emails/?limit=5

# Lista eventi calendario
curl http://localhost:8000/api/calendario/

# Anomalie calendario
curl http://localhost:8000/api/calendario/report/anomalie
```

### 3. Accedi al Frontend

- **URL**: http://snals-mail.local (o IP del server)
- **Pagine principali**:
  - `/` - Dashboard inbox
  - `/calendar` - Calendario eventi
  - `/reports` - Report + anomalie
  - `/interpelli` - Lista interpelli
  - `/chat-rag` - Chat con knowledge base

---

## Architettura File

```
/home/ubuntu/Snals-Mail/
├── backend/
│   ├── app/
│   │   ├── models/
│   │   │   ├── email.py              # Model email
│   │   │   ├── evento.py             # Model evento calendario
│   │   │   └── interpello.py         # Model interpello
│   │   ├── services/
│   │   │   ├── action_executor.py    # Esecuzione azioni (CORE)
│   │   │   ├── categorizer.py        # Classificazione email
│   │   │   ├── email_deletion.py     # Eliminazione da server
│   │   │   ├── email_polling.py      # Polling POP3
│   │   │   ├── email_rate_limiter.py # Rate limiting
│   │   │   ├── unified_extractor.py  # Pipeline estrazione
│   │   │   └── llm_queue_service.py  # Coda LLM singleton
│   │   └── api/routes/
│   │       ├── emails.py             # API email
│   │       ├── calendario.py         # API calendario
│   │       └── rag.py                # API RAG chat
│   └── requirements.txt
├── frontend/
│   └── src/pages/
│       ├── Inbox.tsx                 # Lista email
│       ├── Calendar.tsx              # Calendario
│       └── Reports.tsx               # Report + anomalie
├── docs/
│   ├── ARCHITECTURE.md               # Architettura completa
│   ├── SISTEMA_CALENDARIO.md         # Sistema calendario
│   ├── SISTEMA_EMAIL.md              # Sistema email
│   ├── FLUSSI_ESTRAZIONE_DATI.md     # Pipeline estrazione
│   └── RESUME_GUIDE.md               # Questa guida
├── CHANGELOG.md                      # Log modifiche
└── docker-compose.yml                # Orchestrazione
```

---

## Concetti Chiave

### Stati Evento Calendario

| Stato | Prefisso Titolo | Descrizione |
|-------|-----------------|-------------|
| `confermato` | (nessuno) | Evento attivo |
| `rinviato` | `[RINVIATO]` | Rinviato senza nuova data |
| `confermato` | `[POST RINVIO]` | Rinviato CON nuova data |
| `annullato` | `[ANNULLATO]` | Cancellato |
| `completato` | (nessuno) | Passato/avvenuto |

### Pipeline Estrazione Dati

```
1. REGEX (pattern matching veloce)
   ↓
2. NLP (spaCy entity extraction)
   ↓
3. Ollama (LLM locale)
   ↓
4. ChatGPT (fallback se completezza < 75%)
   ↓
5. Sanity Check (validazione date/ore/luoghi)
```

### Eliminazione Email dal Server

```
Database (soft delete) + Server IMAP (hard delete)
                              ↓
              _derive_imap_from_pop3()
                              ↓
              mail.truemail.it → mail.truemail.it (stesso!)
              pop3s.pec.aruba.it → imaps.pec.aruba.it
```

---

## Troubleshooting Comune

### Email non processate

```bash
# Verifica polling
docker-compose logs backend | grep "poll"

# Verifica azioni in coda
curl http://localhost:8000/api/azioni/?stato=IN_CODA

# Forza reprocessing
curl -X POST http://localhost:8000/api/emails/{id}/reprocess
```

### Eventi non creati

```bash
# Verifica azione specifica
curl http://localhost:8000/api/azioni/{id}

# Verifica log estrazione
docker-compose logs backend | grep "SmartConvocazione"

# Verifica anomalie
curl http://localhost:8000/api/calendario/report/anomalie
```

### LLM non risponde

```bash
# Verifica Ollama
curl http://localhost:11434/api/tags

# Verifica coda LLM
curl http://localhost:8000/api/llm-queue/status

# Riavvia Ollama
docker-compose restart ollama
```

### Email non eliminate dal server

```bash
# Verifica log
docker-compose logs backend | grep "IMAP"

# Il problema comune è mapping server errato
# TrueMail: mail.truemail.it (stesso per POP3 e IMAP!)
```

---

## Modifiche Frequenti

### Aggiungere nuova categoria email

File: `backend/app/services/categorizer.py`

```python
# Aggiungi alla lista CATEGORIE
CATEGORIE = [
    "COMUNICAZIONE_SCUOLA",
    "NUOVA_CATEGORIA",  # Aggiungi qui
    ...
]

# Aggiungi pattern in rule_based_classifier.py
```

### Aggiungere nuovo tipo azione

File: `backend/app/services/action_executor.py`

```python
# Aggiungi handler
def _execute_nuova_azione(self, azione, email):
    # Implementazione
    pass

# Registra in execute()
if tipo == "NUOVA_AZIONE":
    return self._execute_nuova_azione(azione, email)
```

### Modificare pattern estrazione

File: `backend/app/services/action_executor.py`

```python
# Pattern per rilevare rinvii/annullamenti
CANCELLATION_PATTERNS = [
    r'\brinvio\b[\w\s]*del\s+(\d{1,2}[\./]\d{1,2})',
    # Aggiungi nuovo pattern
]
```

---

## Documentazione Dettagliata

| Documento | Quando Leggerlo |
|-----------|-----------------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Overview completo sistema |
| [SISTEMA_CALENDARIO.md](SISTEMA_CALENDARIO.md) | Problemi con eventi |
| [SISTEMA_EMAIL.md](SISTEMA_EMAIL.md) | Problemi con email/spam |
| [FLUSSI_ESTRAZIONE_DATI.md](FLUSSI_ESTRAZIONE_DATI.md) | Dati non estratti correttamente |
| [CHANGELOG.md](../CHANGELOG.md) | Vedere cosa è cambiato |

---

## Contatti e Risorse

- **Repository**: /home/ubuntu/Snals-Mail
- **Database**: PostgreSQL su localhost
- **LLM**: Ollama locale + OpenAI fallback
- **Google APIs**: Configurate in .env

---

**Ultimo aggiornamento:** 2025-12-01
**Versione sistema:** 1.4.0
