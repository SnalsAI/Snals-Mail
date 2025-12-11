# Sistema Calendario - Documentazione Tecnica

Questo documento descrive in dettaglio il funzionamento del sistema di gestione eventi calendario, inclusa la gestione di rinvii e annullamenti.

## Indice

1. [Flusso Creazione Eventi](#flusso-creazione-eventi)
2. [Gestione Rinvii e Annullamenti](#gestione-rinvii-e-annullamenti)
3. [Stati degli Eventi](#stati-degli-eventi)
4. [Anomalie e Loro Risoluzione](#anomalie-e-loro-risoluzione)
5. [Database Schema](#database-schema)
6. [API Endpoints](#api-endpoints)
7. [Troubleshooting](#troubleshooting)

---

## Flusso Creazione Eventi

### Pipeline Completa

```
┌─────────────────────────────────────────────────────────────────────┐
│ 1. EMAIL RICEVUTA (email_polling.py)                                │
│    - POP3 polling ogni 2 minuti                                     │
│    - Salvataggio in database                                        │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 2. CLASSIFICAZIONE (rule_based_classifier.py)                       │
│    - Categoria: "comunicazione_scuola"                              │
│    - Sottocategoria: "Convocazione" | "Rinvio" | "Comunicazione"    │
│    - Confidence score                                               │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 3. ESTRAZIONE DATI (unified_extractor.py)                           │
│    Pipeline multi-step:                                             │
│    ① REGEX → Pattern data/ora/luogo                                 │
│    ② NLP → spaCy + BERT per entità                                  │
│    ③ OLLAMA → LLM locale per semantica                              │
│    ④ ChatGPT → Fallback se completezza < soglia                     │
│    ⑤ Sanity Check → Validazione dati estratti                       │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 4. RILEVAZIONE MODIFICA (action_executor.py)                        │
│    _detect_event_modification() analizza:                           │
│    - È una NUOVA convocazione? → Crea evento                        │
│    - È un RINVIO di evento esistente? → Cerca e aggiorna            │
│    - È un ANNULLAMENTO? → Cerca e marca annullato                   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
              ┌────────────────┴────────────────┐
              │                                 │
     NUOVA CONVOCAZIONE                   MODIFICA ESISTENTE
              │                                 │
              ▼                                 ▼
┌─────────────────────────┐     ┌─────────────────────────────────────┐
│ Crea nuovo evento       │     │ _find_existing_event()              │
│ con stato "confermato"  │     │ - Cerca per codice meccanografico   │
└─────────────────────────┘     │ - Cerca per data ±7 giorni          │
                                │ - Cerca per titolo simile           │
                                └──────────────────┬──────────────────┘
                                                   │
                                    ┌──────────────┴──────────────┐
                                    │                             │
                               TROVATO                        NON TROVATO
                                    │                             │
                                    ▼                             ▼
                    ┌───────────────────────────┐   ┌─────────────────────────┐
                    │ _update_existing_event()  │   │ Crea nuovo evento       │
                    │ - Aggiorna stato          │   │ con prefisso            │
                    │ - Aggiorna titolo         │   │ [RINVIATO]/[ANNULLATO]  │
                    │ - Salva data originale    │   └─────────────────────────┘
                    │ - Applica nuova data      │
                    │ - Collega email_modifica  │
                    └───────────────────────────┘
```

### Pattern Rilevamento Rinvio

File: `backend/app/services/action_executor.py`

```python
CANCELLATION_PATTERNS = [
    r'\brinvio\b[\w\s]*del\s+(\d{1,2}[\.\/]\d{1,2})',
    r'(?:tavolo|incontro|riunione)\s+del\s+(\d{1,2}[\.\/]\d{1,2})\s+[\w\s]*rinviat[oa]',
    r'rinviat[oa]\s+[\w\s]*del\s+(\d{1,2}[\.\/]\d{1,2})',
    r'(?:è\s+)?rinviat[oa]\s+a\s+data\s+da\s+destinarsi',
    r'(?:è\s+)?posticipal[oa]\s+(?:la\s+)?(?:riunione|convocazione)',
    r'(?:è\s+)?sospeso\s+(?:il\s+)?(?:tavolo|incontro)',
]

ANNULLAMENTO_PATTERNS = [
    r'(?:è\s+)?annullat[oa]\s+(?:la\s+)?(?:riunione|convocazione|tavolo)',
    r'(?:è\s+)?cancel+at[oa]\s+(?:la\s+)?(?:riunione|convocazione)',
    r'non\s+(?:si\s+)?terrà\s+(?:più\s+)?(?:la\s+)?(?:riunione|convocazione)',
    r'non\s+avrà\s+(?:più\s+)?luogo',
]
```

### Pattern Estrazione Nuova Data

```python
NEW_DATE_PATTERNS = [
    r'nuov[ao]\s+dat[ao]\s+(?:del\s+)?(\d{1,2})[\.\/](\d{1,2})[\.\/](\d{2,4})',
    r'(?:rinviat[oa]|spostat[oa]|posticipal[oa])\s+al\s+(?:giorno\s+)?(\d{1,2})[\.\/](\d{1,2})',
    r'nuov[ao]\s+convocazione\s+per\s+(?:il\s+)?(?:giorno\s+)?(\d{1,2})[\.\/](\d{1,2})[\.\/](\d{2,4})',
    r'(?:rinviat[oa]|spostat[oa])\s+al\s+(\d{1,2})\s+(gennaio|febbraio|...)',
]
```

---

## Gestione Rinvii e Annullamenti

### Logica Aggiornamento

Quando viene rilevata una modifica, la funzione `_update_existing_event()` esegue:

1. **Aggiorna Titolo** - Aggiunge prefisso `[RINVIATO]` o `[ANNULLATO]`
2. **Aggiorna Stato** - Basato sul tipo di modifica:
   - `rinvio` senza nuova data → `stato = "rinviato"`
   - `rinvio` con nuova data → `stato = "confermato"`, prefisso `[POST RINVIO]`
   - `annullamento` → `stato = "annullato"`
3. **Preserva Data Originale** - Salva in `data_inizio_originale`
4. **Applica Nuova Data** - Se presente nell'email
5. **Collega Email Modifica** - `email_modifica_id` e `note_modifica`
6. **Audit Trail** - Aggiunge dettagli nella descrizione

### Esempio Pratico

**Email ricevuta:**
```
Oggetto: Rinvio tavolo contrattazione del 15.11 - nuova data 22.11.2025 ore 10:00
```

**Evento PRIMA:**
```
id: 123
titolo: "Tavolo contrattazione"
stato: "confermato"
data_inizio: 2025-11-15 09:30:00
data_inizio_originale: NULL
email_modifica_id: NULL
```

**Evento DOPO:**
```
id: 123
titolo: "[POST RINVIO] Tavolo contrattazione"
stato: "confermato"  # Torna confermato perché ha nuova data
data_inizio: 2025-11-22 10:00:00
data_inizio_originale: 2025-11-15 09:30:00
email_modifica_id: 456  # ID dell'email di rinvio
note_modifica: "Modifica (rinvio) da email ID 456: Rinvio tavolo..."
```

---

## Stati degli Eventi

### Enum StatoEvento

```python
class StatoEvento(str, enum.Enum):
    CONFERMATO = "confermato"   # Evento attivo, confermato
    ANNULLATO = "annullato"     # Evento cancellato definitivamente
    RINVIATO = "rinviato"       # Evento rinviato senza nuova data
    COMPLETATO = "completato"   # Evento passato, avvenuto regolarmente
```

### Matrice Prefissi e Stati

| Prefisso Titolo | Stato Corretto | Descrizione |
|-----------------|----------------|-------------|
| (nessuno) | `confermato` | Evento normale |
| `[RINVIATO]` | `rinviato` | Rinviato, data da destinarsi |
| `[POST RINVIO]` | `confermato` | Rinviato ma ha nuova data |
| `[ANNULLATO]` | `annullato` | Cancellato definitivamente |
| (passato) | `completato` | Evento avvenuto |

---

## Anomalie e Loro Risoluzione

### Tipi di Anomalie

File: `backend/app/api/routes/calendario.py`

| Tipo | Descrizione | Come Risolvere |
|------|-------------|----------------|
| `stato_inconsistente` | Titolo dice [RINVIATO] ma stato ≠ "rinviato" | Aggiornare stato |
| `evento_passato_confermato` | Evento passato ancora "confermato" | Segnare come completato |
| `sottocategoria_errata` | Email non era Convocazione | Verificare se evento è corretto |
| `dati_incompleti` | Manca luogo o data | Completare dati |

### API Anomalie

```bash
GET /api/calendario/report/anomalie

Response:
{
  "totale_anomalie": 3,
  "per_tipo": {
    "stato_inconsistente": 1,
    "evento_passato_confermato": 2
  },
  "anomalie": [
    {
      "tipo": "stato_inconsistente",
      "evento_id": 140,
      "titolo": "[RINVIATO] Convocazione...",
      "dettaglio": "Titolo indica rinvio ma stato='confermato'",
      "azione_suggerita": "Aggiornare stato a 'rinviato'"
    }
  ]
}
```

### Risoluzione Automatica Anomalie

#### Endpoint API per Risoluzione Automatica

```bash
POST /api/calendario/report/anomalie/risolvi-auto

Response:
{
  "success": true,
  "risolte": {
    "eventi_completati": 8,   # Eventi passati marcati come completato
    "stati_corretti": 2,       # Stati corretti in base al titolo
    "google_aggiornati": 10    # Eventi aggiornati su Google Calendar
  },
  "totale": 10
}
```

Questa API risolve automaticamente:
- **Eventi passati confermati** → marcati come `completato`
- **Stati inconsistenti** → corregge lo stato in base al prefisso nel titolo
- **Sincronizzazione Google** → aggiorna i titoli su Google Calendar con prefisso [COMPLETATO]

#### Risoluzione Singola Anomalia

```bash
DELETE /api/calendario/report/anomalie/{evento_id}?azione=completato

Response:
{
  "success": true,
  "evento_id": 123,
  "stato_precedente": "confermato",
  "nuovo_stato": "completato"
}
```

Azioni disponibili: `completato`, `annullato`, `rinviato`, `confermato`

#### Query SQL Manuali (se necessario)

L'implementazione corretta in `_update_existing_event()` previene la maggior parte delle anomalie. Se si verificano, usare:

```sql
-- Correggi stato inconsistente
UPDATE eventi_calendario
SET stato = 'rinviato'
WHERE titolo LIKE '%[RINVIATO]%'
  AND titolo NOT LIKE '%[POST RINVIO]%'
  AND stato != 'rinviato';

-- Segna eventi passati come completati
UPDATE eventi_calendario
SET stato = 'completato'
WHERE data_inizio < NOW() - INTERVAL '1 day'
  AND stato = 'confermato';
```

---

## Database Schema

### Tabella eventi_calendario

```sql
CREATE TABLE eventi_calendario (
    id SERIAL PRIMARY KEY,
    email_id INTEGER REFERENCES emails(id),

    -- Stato evento
    stato VARCHAR(50) DEFAULT 'confermato',  -- confermato|annullato|rinviato|completato
    email_modifica_id INTEGER REFERENCES emails(id),  -- Email che ha modificato
    note_modifica TEXT,  -- Dettagli modifica

    -- Dettagli evento
    titolo VARCHAR(500) NOT NULL,
    descrizione TEXT,

    -- Timing
    data_inizio TIMESTAMP NOT NULL,
    data_fine TIMESTAMP,
    data_inizio_originale TIMESTAMP,  -- Preserva data pre-rinvio
    all_day BOOLEAN DEFAULT FALSE,

    -- Luogo
    luogo VARCHAR(500),
    link_videocall VARCHAR(500),

    -- Contesto
    scuola VARCHAR(255),
    tipo_convocazione VARCHAR(100),
    sintesi_motivo TEXT,

    -- Google Sync
    google_calendar_id VARCHAR(255),
    google_event_id VARCHAR(255),
    sincronizzato BOOLEAN DEFAULT FALSE,

    -- Metadati
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indici
CREATE INDEX idx_eventi_data ON eventi_calendario(data_inizio);
CREATE INDEX idx_eventi_stato ON eventi_calendario(stato);
CREATE INDEX idx_eventi_scuola ON eventi_calendario(scuola);
```

---

## API Endpoints

### Calendario

| Metodo | Endpoint | Descrizione |
|--------|----------|-------------|
| GET | `/api/calendario/` | Lista eventi |
| GET | `/api/calendario/{id}` | Dettaglio evento |
| POST | `/api/calendario/` | Crea evento |
| PUT | `/api/calendario/{id}` | Aggiorna evento |
| DELETE | `/api/calendario/{id}` | Elimina evento |
| GET | `/api/calendario/report/anomalie` | Lista anomalie |
| POST | `/api/calendario/report/anomalie/risolvi-auto` | Risolve anomalie automaticamente |
| DELETE | `/api/calendario/report/anomalie/{id}` | Risolve singola anomalia |
| DELETE | `/api/calendario/cleanup-all` | Elimina tutti gli eventi |
| POST | `/api/calendario/sync-google` | Sincronizza con Google Calendar |

---

## Troubleshooting

### Problema: Evento creato con stato sbagliato

**Causa:** Email di rinvio non rilevata correttamente

**Soluzione:**
1. Verificare pattern in `_detect_event_modification()`
2. Controllare log per keyword trovate
3. Correggere manualmente:
   ```sql
   UPDATE eventi_calendario SET stato = 'rinviato' WHERE id = X;
   ```

### Problema: Nuova data non estratta

**Causa:** Pattern non riconosciuto

**Soluzione:**
1. Verificare testo email
2. Aggiungere pattern a `_extract_new_date_from_email()`
3. Aggiornare manualmente:
   ```sql
   UPDATE eventi_calendario
   SET data_inizio = '2025-12-15 10:00:00',
       data_inizio_originale = data_inizio
   WHERE id = X;
   ```

### Problema: Evento duplicato dopo rinvio

**Causa:** `_find_existing_event()` non ha trovato l'originale

**Soluzione:**
1. Verificare codice meccanografico mittente
2. Verificare range date (±7 giorni)
3. Unificare manualmente:
   ```sql
   -- Elimina duplicato
   DELETE FROM eventi_calendario WHERE id = X_duplicato;

   -- Aggiorna originale
   UPDATE eventi_calendario SET ... WHERE id = X_originale;
   ```

---

## File di Riferimento

| File | Descrizione |
|------|-------------|
| `backend/app/models/evento.py` | Model database |
| `backend/app/services/action_executor.py` | Logica creazione/modifica |
| `backend/app/services/unified_extractor.py` | Estrazione dati |
| `backend/app/api/routes/calendario.py` | API endpoints |
| `frontend/src/pages/Calendar.tsx` | UI calendario |
| `frontend/src/pages/Reports.tsx` | UI anomalie |

---

**Ultimo aggiornamento:** 2025-12-11
**Versione:** 1.4.1
