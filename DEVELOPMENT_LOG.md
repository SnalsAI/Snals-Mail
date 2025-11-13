# SNALS Mail Agent - Development Log

## [2024-11-13] - Implementazione Fasi 4, 5, 6

### Panoramica
Implementazione completa delle Fasi 4 (Azioni Automatiche), 5 (Frontend UI), e 6 (API Backend + Google Calendar Integration) del progetto SNALS Mail Agent.

---

## FASE 4: AZIONI AUTOMATICHE

### Obiettivi
- Motore esecuzione azioni automatiche
- Generazione bozze email (info generiche, appuntamento, tesseramento)
- Creazione eventi calendario
- Upload Google Drive
- Integrazione IMAP per salvare bozze
- Task async per azioni

### File Creati

#### 1. `backend/app/services/action_executor.py`
**Motore principale esecuzione azioni (400+ righe)**

- Classe `ActionExecutor` che coordina tutte le azioni automatiche
- Metodo `execute_actions_for_email(email_id)` - dispatcher principale
- Azioni per categoria:
  - `_azione_info_generiche()` - Genera bozza risposta con LLM
  - `_azione_appuntamento()` - Bozza con link prenotazione
  - `_azione_tesseramento()` - Bozza + allegati repository
  - `_azione_convocazione()` - Crea evento calendario
  - `_azione_ust_usr()` - Upload allegati su Google Drive
  - `_azione_snals_centrale()` - Upload allegati SNALS centrale
  - `_azione_scuola()` - Log interpretazione per sintesi

**Caratteristiche:**
- Integrazione con LLM per generazione risposte intelligenti
- Gestione template email personalizzati
- Parsing date per eventi calendario
- Upload organizzato su Google Drive (cartelle per anno/mese)
- Registrazione azioni nel database

#### 2. `backend/app/integrations/webmail_imap.py`
**Client IMAP per salvataggio bozze**

- Classe `WebmailIMAPClient`
- Metodo `save_draft()` - salva bozza in cartella Drafts
- Supporto allegati multipli
- Threading email (In-Reply-To, References)
- Gestione nomi cartella Drafts variabili (Drafts, Bozze, [Gmail]/Drafts, etc.)

**Caratteristiche:**
- Connessione SSL sicura
- Encoding UTF-8 per testo italiano
- Encoding base64 per allegati
- Error handling robusto

#### 3. `backend/app/integrations/google_drive.py`
**Client Google Drive per upload allegati**

- Classe `GoogleDriveClient`
- Autenticazione OAuth2 con refresh automatico
- Metodo `upload_file()` - upload con metadati custom
- Metodo `get_or_create_folder()` - creazione cartelle gerarchiche
- Metodo `share_file()` - condivisione file

**Caratteristiche:**
- Token salvato in pickle per persistenza
- Creazione cartelle automatica (es: UST_USR/2024/11)
- Metadati custom come properties
- Upload resumable per file grandi

#### 4. `backend/app/tasks/action_tasks.py`
**Task Celery per esecuzione asincrona**

- Task `execute_email_actions(email_id)` - esegue azioni per email
- Integrazione con ActionExecutor
- Logging completo
- Error handling con retry

#### 5. `backend/scripts/setup_google_oauth.py`
**Script interattivo setup OAuth**

- Setup OAuth2 per Google Drive e Calendar
- Flow interattivo con browser
- Salvataggio token
- Istruzioni per ottenere credenziali da Google Console

**Usage:**
```bash
cd backend
python scripts/setup_google_oauth.py
```

### Funzionalità Implementate
- ✓ Generazione bozze con LLM (info generiche)
- ✓ Bozze template (appuntamento, tesseramento)
- ✓ Salvataggio bozze via IMAP in webmail
- ✓ Creazione eventi calendario interno
- ✓ Upload allegati su Google Drive (cartelle organizzate)
- ✓ Task async per esecuzione azioni
- ✓ OAuth2 Google (Drive + Calendar)

### Azioni per Categoria

| Categoria | Azione |
|-----------|--------|
| info_generiche | Bozza risposta generata con LLM → webmail |
| richiesta_appuntamento | Bozza template con link prenotazione → webmail |
| richiesta_tesseramento | Bozza + allegati repository → webmail |
| convocazione_scuola | Creazione evento calendario |
| comunicazione_ust_usr | Upload allegati su Google Drive |
| comunicazione_snals_centrale | Upload allegati su Google Drive |
| comunicazione_scuola | Log interpretazione per sintesi |

---

## FASE 5: FRONTEND UI

### Obiettivi
- Setup React + Vite
- Struttura componenti
- Dashboard con KPI
- Pagina Email (lista + dettaglio)
- Integrazione API backend

### Setup Tecnologico
- **Build Tool:** Vite 5.x
- **Framework:** React 18
- **Styling:** TailwindCSS 3.x
- **Routing:** React Router DOM v6
- **State Management:** TanStack Query (React Query)
- **HTTP Client:** Axios
- **Icons:** Lucide React
- **Date Formatting:** date-fns

### File Creati

#### Configurazione
1. `frontend/package.json` - Dipendenze e scripts
2. `frontend/vite.config.js` - Config Vite + proxy API
3. `frontend/tailwind.config.js` - Config Tailwind
4. `frontend/postcss.config.js` - Config PostCSS
5. `frontend/index.html` - HTML entry point

#### Servizi API
6. `frontend/src/services/api.js` - Client Axios base
7. `frontend/src/services/emailService.js` - Servizio email API

**API Methods:**
- `getEmails(filters)` - Lista email con filtri
- `getEmail(id)` - Dettaglio email
- `getStats()` - Statistiche dashboard
- `recategorize(id)` - Ri-categorizza email

#### Componenti e Pagine
8. `frontend/src/components/Layout/Layout.jsx` - Layout principale con sidebar
9. `frontend/src/pages/Dashboard.jsx` - Dashboard con KPI
10. `frontend/src/pages/EmailsPage.jsx` - Lista + dettaglio email
11. `frontend/src/App.jsx` - Router principale
12. `frontend/src/main.jsx` - Entry point React

### Funzionalità UI

#### Dashboard
- **KPI Cards:**
  - Email Oggi
  - In Elaborazione
  - Completate
  - Questa Settimana
- **Chart:** Distribuzione categorie con progress bar
- **Stream:** Attività recenti
- **Auto-refresh:** Ogni 30 secondi

#### Pagina Email
- **Lista Email:**
  - Filtro per categoria
  - Ricerca full-text
  - Paginazione
  - Badge categoria colorati
- **Dettaglio Email:**
  - Visualizzazione completa
  - Interpretazione JSON formattata
  - Azioni eseguite con status
  - Info metadata (confidence, data, etc.)

#### Layout
- **Sidebar Navigation:**
  - Dashboard
  - Email
  - Calendario (placeholder)
  - Regole (placeholder)
  - Repository (placeholder)
  - Configurazione (placeholder)

### Styling
- Design moderno con Tailwind
- Palette colori consistente
- Responsive design (mobile-ready)
- Hover states e transizioni
- Shadow e rounded corners

---

## FASE 6: API BACKEND + GOOGLE CALENDAR

### Obiettivi
- API REST per frontend
- Pydantic schemas
- Google Calendar integration
- Task sincronizzazione calendario

### File Creati

#### API Backend
1. `backend/app/schemas/email.py` - Pydantic schemas
   - `EmailListResponse` - Schema lista email
   - `EmailDetailResponse` - Schema dettaglio completo
   - `EmailStatsResponse` - Schema statistiche
   - `InterpretazioneResponse` - Schema interpretazione
   - `AzioneResponse` - Schema azione

2. `backend/app/api/emails.py` - Router API email
   - `GET /api/emails` - Lista con filtri e ricerca
   - `GET /api/emails/stats` - Statistiche dashboard
   - `GET /api/emails/{id}` - Dettaglio email
   - `POST /api/emails/{id}/recategorize` - Ri-categorizza

**Features API:**
- Filtri categoria e ricerca full-text
- Paginazione con limit/offset
- Conteggi per KPI (oggi, settimana, processing, completed)
- Distribuzione categorie aggregata
- Caricamento relazioni (interpretazione, azioni)

#### Google Calendar Integration
3. `backend/app/integrations/google_calendar.py` - Client Calendar
   - Classe `GoogleCalendarClient`
   - Autenticazione OAuth2 condivisa con Drive
   - Metodi:
     - `create_event()` - Crea evento
     - `update_event()` - Aggiorna evento
     - `delete_event()` - Elimina evento

**Caratteristiche:**
- Timezone Europe/Rome
- Supporto location e attendees
- Event ID restituito per tracking
- Error handling

4. `backend/app/tasks/calendar_sync.py` - Task sincronizzazione
   - Task `sync_events_to_google()` - sync periodico
   - Processa max 50 eventi per run
   - Marca eventi come sincronizzati
   - Batch processing per performance

**Schedule:** Ogni 5 minuti (configurabile in Celery beat)

### Integrazione Frontend-Backend
- Proxy Vite configurato (/api → localhost:8001)
- TanStack Query per caching e auto-refresh
- Error handling centralizzato
- Loading states

---

## Struttura Progetto Completa

```
snals-mail/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── emails.py
│   │   ├── integrations/
│   │   │   ├── webmail_imap.py
│   │   │   ├── google_drive.py
│   │   │   └── google_calendar.py
│   │   ├── services/
│   │   │   └── action_executor.py
│   │   ├── tasks/
│   │   │   ├── action_tasks.py
│   │   │   └── calendar_sync.py
│   │   ├── schemas/
│   │   │   └── email.py
│   │   └── models/
│   │       └── (da fasi precedenti)
│   ├── config/
│   │   └── (google_credentials.json, google_token.json)
│   └── scripts/
│       └── setup_google_oauth.py
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   └── Layout/
│   │   │       └── Layout.jsx
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx
│   │   │   └── EmailsPage.jsx
│   │   ├── services/
│   │   │   ├── api.js
│   │   │   └── emailService.js
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── postcss.config.js
└── DEVELOPMENT_LOG.md
```

---

## Setup e Avvio

### Backend

#### Prerequisiti
- Python 3.9+
- PostgreSQL
- Redis (per Celery)
- Google Cloud Project con Drive & Calendar API abilitate

#### Setup Google OAuth
```bash
cd backend
python scripts/setup_google_oauth.py
# Segui le istruzioni per autorizzare l'app
```

#### Avvio Servizi
```bash
# Backend API
uvicorn app.main:app --reload --port 8001

# Celery Worker
celery -A app.tasks worker --loglevel=info

# Celery Beat (scheduler)
celery -A app.tasks beat --loglevel=info
```

### Frontend

#### Setup
```bash
cd frontend
npm install
```

#### Avvio Dev Server
```bash
npm run dev
# Apri http://localhost:3001
```

#### Build Production
```bash
npm run build
npm run preview
```

---

## Configurazione Necessaria

### Environment Variables (Backend)
```env
# Database
DATABASE_URL=postgresql://user:pass@localhost/snals_mail

# Redis
REDIS_URL=redis://localhost:6379

# IMAP Webmail
WEBMAIL_IMAP_HOST=mail.snals.it
WEBMAIL_IMAP_PORT=993
WEBMAIL_IMAP_USER=segreteria@snals.it
WEBMAIL_IMAP_PASSWORD=...

# Google
GOOGLE_CREDENTIALS_FILE=config/google_credentials.json
GOOGLE_TOKEN_FILE=config/google_token.json
GOOGLE_CALENDAR_ID=primary

# Repository
REPOSITORY_PATH=/var/snals/repository
```

### Environment Variables (Frontend)
```env
VITE_API_URL=http://localhost:8001
```

---

## Testing

### Test Backend
```bash
# Test manuale azione
python -c "
from app.services.action_executor import ActionExecutor
executor = ActionExecutor()
executor.execute_actions_for_email(1)  # ID email di test
"

# Verifica bozze in webmail
# Verifica file su Google Drive
# Verifica eventi su Google Calendar
```

### Test Frontend
```bash
cd frontend
npm run dev
# Apri http://localhost:3001
# Naviga tra Dashboard e Email
# Verifica filtri e ricerca
# Verifica dettaglio email
```

### Test API
```bash
# Stats
curl http://localhost:8001/api/emails/stats

# Lista email
curl http://localhost:8001/api/emails?limit=10

# Dettaglio
curl http://localhost:8001/api/emails/1

# Ricategorizza
curl -X POST http://localhost:8001/api/emails/1/recategorize
```

---

## Problemi Noti & Soluzioni

### Problema: Nome cartella Drafts varia per provider
**Soluzione:** Implementato tentativo multiplo con varianti comuni (Drafts, Bozze, [Gmail]/Drafts, INBOX.Drafts)

### Problema: Token Google scade
**Soluzione:** Refresh automatico con refresh_token

### Problema: Upload file grandi su Drive
**Soluzione:** MediaFileUpload con resumable=True

---

## Prossimi Step (FASE 7)

### Sistema Regole
- [ ] Motore regole personalizzabile
- [ ] UI builder regole
- [ ] Condizioni e azioni
- [ ] Test regole

### Pagine Frontend Mancanti
- [ ] Pagina Calendario con visualizzazione eventi
- [ ] Pagina Regole con CRUD
- [ ] Pagina Repository con browser file
- [ ] Pagina Configurazione

### Ottimizzazioni
- [ ] WebSocket per real-time updates
- [ ] Background tasks monitoring
- [ ] Metrics e analytics
- [ ] Test automatici

---

## Note Tecniche

### Performance
- TanStack Query usa cache aggressiva
- Auto-refresh dashboard ogni 30s
- Batch processing per sync calendario (max 50 eventi)
- Lazy loading componenti (possibile improvement)

### Security
- OAuth2 per Google APIs
- Token storage sicuro
- CORS configurato
- Input validation con Pydantic

### Scalability
- Task async con Celery
- Database connection pooling
- API pagination
- Stateless backend (scalabile orizzontalmente)

---

## Metriche Implementazione

### Backend
- **File Creati:** 10
- **Linee di Codice:** ~2000
- **Integrazioni:** 3 (IMAP, Google Drive, Google Calendar)
- **API Endpoints:** 4
- **Task Celery:** 2

### Frontend
- **File Creati:** 12
- **Componenti:** 3 (Layout, Dashboard, EmailsPage)
- **Servizi API:** 4 metodi
- **Pagine:** 2 complete + 4 placeholder

### Totale
- **File Totali:** 22
- **Linee Codice Totali:** ~3500
- **Tempo Implementazione:** ~2-3 giorni stimati

---

## Stato Progetto

✅ **FASE 4 COMPLETATA** - Azioni Automatiche
✅ **FASE 5 COMPLETATA** - Frontend UI Base
✅ **FASE 6 COMPLETATA** - API Backend + Google Calendar

🔄 **FASE 7 IN ATTESA** - Sistema Regole

---

## Contributi e Manutenzione

### Code Style
- Backend: PEP 8
- Frontend: ESLint + Prettier (da configurare)
- Docstrings per tutte le funzioni

### Git Workflow
- Branch: `claude/phase-4-automatic-actions-engine-*`
- Commit messages descrittivi
- Push dopo completamento fasi

### Documentazione
- Inline comments per logica complessa
- README per setup
- DEVELOPMENT_LOG per changelog

---

## Riferimenti

### Documentazione Esterna
- [Google Drive API](https://developers.google.com/drive/api/v3/about-sdk)
- [Google Calendar API](https://developers.google.com/calendar/api/v3/reference)
- [IMAP RFC 3501](https://tools.ietf.org/html/rfc3501)
- [React Router v6](https://reactrouter.com/)
- [TanStack Query](https://tanstack.com/query/latest)

### Librerie Utilizzate
- FastAPI
- SQLAlchemy
- Celery
- google-api-python-client
- google-auth-oauthlib
- React
- TailwindCSS
- Axios
- date-fns

---

**Last Updated:** 2024-11-13
**Version:** 1.0
**Author:** Claude (Anthropic)
