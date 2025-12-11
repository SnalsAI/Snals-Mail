# Changelog

Tutti i cambiamenti importanti al progetto SNALS Email Agent saranno documentati in questo file.

Il formato è basato su [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
e questo progetto aderisce a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.4.1] - 2025-12-11

### Fix API Calendario

#### Bug Fix
- **Import `re` mancante** - Aggiunto import modulo `re` in `calendario.py` per funzione `risolvi_anomalie_auto`
- **Attributo `sincronizzato_google` errato** - Corretto in `sincronizzato` nella funzione `delete_evento`

#### Risoluzione Automatica Anomalie
- **Endpoint `/api/calendario/report/anomalie/risolvi-auto`** - Ora funzionante correttamente
- **Eventi passati confermati** - Marcati automaticamente come "completato"
- **Sincronizzazione Google Calendar** - Titoli aggiornati con prefisso [COMPLETATO]

#### Anomalie Risolte (10 Dicembre 2025)
- 8 eventi passati ancora in stato "confermato" → marcati come "completato"
- 2 eventi duplicati da email "Risposta personale" → eliminati (eventi 201, 202)

### File Modificati

- `backend/app/api/routes/calendario.py`
  - Riga 6: Aggiunto `import re`
  - Riga 388: Corretto `sincronizzato_google` → `sincronizzato`

---

## [1.4.0] - 2025-11-30

### Gestione Rinvii e Annullamenti Eventi Calendario

#### Aggiornamento Automatico Stato Eventi
- **Campo `stato` ora aggiornato automaticamente** - Quando arriva email di rinvio/annullamento
  - `rinvio` → stato = "rinviato"
  - `annullamento` → stato = "annullato"
  - Se c'è nuova data → stato torna "confermato"
- **Nuovo stato `completato`** - Per eventi passati che sono avvenuti regolarmente
- **Prefisso `[POST RINVIO]`** - Indica evento rinviato CON nuova data assegnata

#### Tracciabilità Modifiche Eventi
- **`email_modifica_id`** - Ora popolato con ID email che ha modificato l'evento
- **`note_modifica`** - Dettagli della modifica (tipo, email, oggetto)
- **`data_inizio_originale`** - Nuovo campo che preserva la data originale prima del rinvio
- **Audit trail in descrizione** - Storico completo delle modifiche

#### Estrazione Nuova Data
- **Nuova funzione `_extract_new_date_from_email()`** - Estrae automaticamente la nuova data
- **Pattern supportati**:
  - "nuova data 20/11/2025"
  - "rinviato al 22.11"
  - "spostato al giorno 15 dicembre"
  - "nuova convocazione per il 10/12/2025"
- **Aggiornamento automatico `data_inizio`** - Se trovata nuova data nell'email

#### Logica Prefissi Titolo
| Prefisso | Significato | Stato |
|----------|-------------|-------|
| `[RINVIATO]` | Evento rinviato senza nuova data | `rinviato` |
| `[POST RINVIO]` | Evento rinviato CON nuova data | `confermato` |
| `[ANNULLATO]` | Evento cancellato definitivamente | `annullato` |

### Sistema Eliminazione Email Spam

#### Fix Servizio Email Deletion
- **Derivazione automatica server IMAP** - Dal server POP3 configurato
- **Mappatura provider specifici**:
  - `mail.truemail.it` → `mail.truemail.it` (stesso server per POP3/IMAP)
  - `pop3s.pec.aruba.it` → `imaps.pec.aruba.it`
- **Credenziali corrette** - Usa stesse credenziali POP3 per IMAP
- **Logging migliorato** - Traccia connessione, login, eliminazione

#### Funzionamento Eliminazione Spam
1. Connessione IMAP SSL (porta 993)
2. Login con credenziali POP3
3. Ricerca email per Message-ID
4. Flag `\Deleted` + EXPUNGE
5. Soft-delete nel database locale (storico preservato)

### Rate Limiting Email

#### Nuovo Modulo `email_rate_limiter.py`
- **Singleton pattern** - Una sola istanza per tutto il sistema
- **Limiti configurabili**:
  - Max 30 email/ora
  - Max 5 email/minuto
  - Delay minimo 10 secondi tra invii
  - Delay burst 60 secondi se 3+ errori consecutivi
- **Prevenzione blocco IP** - Rallenta automaticamente se troppe email

### UI Anomalie Calendario (spostata in Reports)

#### Nuova Sezione in `/reports`
- **Tab "Calendario"** - Dedicato alle anomalie eventi
- **Spiegazioni dettagliate** - Perché c'è l'anomalia, impatto, come risolvere
- **Pulsanti azione rapida**:
  - Elimina evento
  - Segna come completato
  - Segna come annullato

### File Backend Modificati

- `backend/app/models/evento.py`
  - Aggiunto stato `COMPLETATO` all'enum
  - Aggiunto campo `data_inizio_originale`

- `backend/app/services/action_executor.py`
  - Nuova funzione `_extract_new_date_from_email()`
  - `_update_existing_event()` ora aggiorna stato, email_modifica_id, data originale
  - Estrazione e applicazione nuova data automatica

- `backend/app/services/email_deletion.py`
  - Nuova funzione `_derive_imap_from_pop3()`
  - Usa `get_settings()` per configurazione
  - Mappatura provider specifici (TrueMail, Aruba PEC)

- `backend/app/services/email_rate_limiter.py` (NUOVO)
  - Classe `EmailRateLimiter` con singleton pattern
  - Metodi `wait_if_needed()`, `record_send()`

- `backend/app/api/routes/calendario.py`
  - Aggiornata logica anomalie per escludere `[POST RINVIO]`
  - Commenti esplicativi sulla logica

### File Frontend Modificati

- `frontend/src/pages/Reports.tsx`
  - Nuova tab "Calendario" per anomalie
  - Costante `ANOMALY_EXPLANATIONS` con spiegazioni dettagliate
  - Mutations per delete/update eventi
  - Pulsanti azione rapida

- `frontend/src/pages/Calendar.tsx`
  - Rimossa tab anomalie (spostata in Reports)

### Migration Database

```sql
-- Aggiunta colonna data_inizio_originale
ALTER TABLE eventi_calendario
ADD COLUMN IF NOT EXISTS data_inizio_originale TIMESTAMP;
```

---

## [1.3.0] - 2025-11-30

### Miglioramenti Sistema Calendario

#### Sanity Check Estrazione Dati
- **Validazione Date** - Blocca date nel passato (>30 giorni fa) o troppo future (>2 anni)
- **Validazione Ore** - Blocca orari irrealistici (es. 25:00, 99:00)
- **Validazione Luogo** - Rimuove indirizzi evidentemente non validi
- **Flag `_sanity_passed`** - Tracciabilità validazione nei dati estratti

#### Soglia Minima Creazione Eventi
- **Completezza < 40%** - Non crea evento, richiede intervento manuale
- **Sanity Check Fallito** - Non crea evento, segnala problemi specifici
- **Data Mancante** - Non crea evento, richiede inserimento manuale
- **Messaggio Dettagliato** - Indicazione chiara su cosa correggere

#### Endpoint Anomalie Calendario
- **`GET /api/calendario/report/anomalie`** - Rileva anomalie negli eventi
- **Tipi Anomalie Rilevate**:
  - `stato_inconsistente`: Titolo contiene [RINVIATO]/[ANNULLATO] ma stato diverso
  - `evento_passato_confermato`: Evento passato ancora in stato "confermato"
  - `sottocategoria_errata`: Evento creato da email non-convocazione
  - `dati_incompleti`: Mancano luogo o data

### Miglioramento Classificatore Sottocategorie

#### Distinzione Comunicazione vs Convocazione
- **Pattern Migliorati** - Distingue convocazioni esplicite da comunicazioni generiche
- **"Prosecuzione trattative"** → Comunicazione (non crea eventi)
- **Convocazioni con data/ora** → Convocazione (crea eventi)

---

## [1.2.0] - 2025-11-28

### NLP Training con ChatGPT

#### Sistema di Training Supervisionato
- **Modulo NLP Training** - Nuova pagina `/nlp-training` per addestrare modelli NLP
- **Analisi ChatGPT** - Usa GPT-4o-mini come "teacher" per generare training data annotati
- **Workflow di Approvazione** - I risultati ChatGPT devono essere approvati manualmente
- **EntityRuler Training** - I pattern approvati vengono aggiunti all'EntityRuler di spaCy

#### Sistema di Benchmark
- **Benchmark Pre/Post Training** - Misura le performance NLP prima e dopo il training
- **Metriche Complete** - Precision, Recall, F1-score per ogni campo estratto
- **Confronto Performance** - Visualizzazione delta con indicazione miglioramento/peggioramento

#### Pattern NLP Custom
- **853 Pattern EntityRuler** - Pattern per classi concorso, meccanografici, istituti, province
- **Classi di Concorso** - 349 pattern per tutti i codici classi
- **Codici Meccanografici** - 122 pattern per scuole provincia Taranto

---

## [1.1.0] - 2025-11-20

### Chat RAG con Knowledge Base
- **Endpoint `/api/rag/chat`** - Query conversazionale con LLM basata su documenti
- **Interfaccia Chat React** - Pagina `/chat-rag` con UI moderna
- **Citazione Fonti** - Ogni risposta include riferimenti ai documenti utilizzati

### Sistema Azioni Completamente Automatico
- **Creazione Automatica Azioni** - Dopo ogni email processata
- **Supporto PARSE_INTERPELLO** - Estrazione automatica interpelli
- **Esecuzione Background** - Azioni processate ogni minuto

### Eventi Calendario Automatici
- **Creazione Automatica** - Da email con categoria `CONVOCAZIONE_SCUOLA`
- **SmartExtractor** - Estrazione intelligente data/ora/luogo
- **Google Calendar Sync** - Sincronizzazione automatica

### Ottimizzazioni Performance
- **EMAIL_FETCH_LIMIT**: 50 → 3 email per batch
- **Error Handling Migliorato** - Try/except isolati per email

---

## [1.0.0] - 2025-11-17

### Rilascio Iniziale

#### Funzionalità Complete
- Email Processing (POP3/SMTP normale + PEC)
- Categorizzazione LLM (8 categorie)
- Rules Engine
- Google Drive/Calendar integration
- Frontend React completo
- API REST (30+ endpoints)
- Docker Compose setup

---

## Formato Versioni

- **MAJOR version** (X.0.0) - Cambiamenti incompatibili nell'API
- **MINOR version** (1.X.0) - Nuove funzionalità retrocompatibili
- **PATCH version** (1.0.X) - Bug fix retrocompatibili
