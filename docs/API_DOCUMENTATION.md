# API Documentation - SNALS Email Agent

Documentazione completa delle API REST del sistema.

**Base URL:** `http://localhost:8000/api`

---

## Autenticazione

Attualmente il sistema non richiede autenticazione per le API interne.

---

## Endpoints

### Email

#### Lista Email
```http
GET /api/emails/
```

**Query Parameters:**
| Parametro | Tipo | Default | Descrizione |
|-----------|------|---------|-------------|
| `page` | int | 1 | Pagina |
| `per_page` | int | 20 | Elementi per pagina |
| `categoria` | string | - | Filtra per categoria |
| `is_spam` | bool | - | Filtra spam |
| `is_read` | bool | - | Filtra lette/non lette |
| `date_from` | date | - | Data inizio |
| `date_to` | date | - | Data fine |

**Response:**
```json
{
  "items": [
    {
      "id": 1,
      "mittente": "scuola@istruzione.it",
      "oggetto": "Convocazione tavolo",
      "categoria": "comunicazione_scuola",
      "sottocategoria": "convocazione",
      "created_at": "2025-11-30T10:00:00Z"
    }
  ],
  "total": 150,
  "page": 1,
  "per_page": 20
}
```

#### Dettaglio Email
```http
GET /api/emails/{id}
```

**Response:**
```json
{
  "id": 1,
  "mittente": "scuola@istruzione.it",
  "destinatario": "info@snals.it",
  "oggetto": "Convocazione tavolo contrattazione",
  "corpo": "Testo completo...",
  "corpo_html": "<html>...</html>",
  "categoria": "comunicazione_scuola",
  "sottocategoria": "convocazione",
  "confidence": 0.95,
  "account_type": "normale",
  "is_spam": false,
  "is_read": true,
  "allegati_nomi": ["convocazione.pdf"],
  "created_at": "2025-11-30T10:00:00Z"
}
```

#### Elimina Email
```http
DELETE /api/emails/{id}
```

**Query Parameters:**
| Parametro | Tipo | Default | Descrizione |
|-----------|------|---------|-------------|
| `from_server` | bool | false | Elimina anche dal server IMAP |

**Response:**
```json
{
  "success": true,
  "message": "Email eliminata",
  "deleted_from_server": true
}
```

#### Riclassifica Email
```http
POST /api/emails/{id}/classify
```

**Response:**
```json
{
  "categoria": "comunicazione_scuola",
  "sottocategoria": "convocazione",
  "confidence": 0.92
}
```

#### Marca come Spam
```http
POST /api/emails/{id}/spam
```

**Body:**
```json
{
  "delete_from_server": true
}
```

---

### Calendario

#### Lista Eventi
```http
GET /api/calendario/
```

**Query Parameters:**
| Parametro | Tipo | Default | Descrizione |
|-----------|------|---------|-------------|
| `data_inizio` | date | - | Data minima evento |
| `data_fine` | date | - | Data massima evento |
| `stato` | string | - | confermato, rinviato, annullato, completato |
| `scuola` | string | - | Codice meccanografico |

**Response:**
```json
{
  "items": [
    {
      "id": 123,
      "titolo": "Tavolo contrattazione",
      "data_inizio": "2025-12-15T10:00:00Z",
      "data_fine": "2025-12-15T12:00:00Z",
      "luogo": "Via Roma 1, Taranto",
      "stato": "confermato",
      "scuola": "TAPC070005"
    }
  ]
}
```

#### Dettaglio Evento
```http
GET /api/calendario/{id}
```

**Response:**
```json
{
  "id": 123,
  "email_id": 456,
  "titolo": "[POST RINVIO] Tavolo contrattazione",
  "descrizione": "Descrizione completa...",
  "data_inizio": "2025-12-15T10:00:00Z",
  "data_fine": "2025-12-15T12:00:00Z",
  "data_inizio_originale": "2025-12-08T10:00:00Z",
  "luogo": "Via Roma 1, Taranto",
  "stato": "confermato",
  "scuola": "TAPC070005",
  "tipo_convocazione": "contrattazione",
  "email_modifica_id": 789,
  "note_modifica": "Modifica (rinvio) da email ID 789",
  "google_event_id": "abc123",
  "sincronizzato": true,
  "created_at": "2025-11-30T10:00:00Z",
  "updated_at": "2025-12-01T09:00:00Z"
}
```

#### Crea Evento
```http
POST /api/calendario/
```

**Body:**
```json
{
  "titolo": "Nuovo evento",
  "data_inizio": "2025-12-20T10:00:00Z",
  "data_fine": "2025-12-20T12:00:00Z",
  "luogo": "Via Roma 1",
  "descrizione": "Descrizione opzionale"
}
```

#### Aggiorna Evento
```http
PUT /api/calendario/{id}
```

**Body:**
```json
{
  "titolo": "Titolo aggiornato",
  "stato": "completato"
}
```

#### Elimina Evento
```http
DELETE /api/calendario/{id}
```

#### Report Anomalie
```http
GET /api/calendario/report/anomalie
```

**Query Parameters:**
| Parametro | Tipo | Default | Descrizione |
|-----------|------|---------|-------------|
| `data_da` | date | -7 giorni | Data minima per eventi da controllare |

**Response:**
```json
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

**Tipi di Anomalie:**
| Tipo | Descrizione |
|------|-------------|
| `stato_inconsistente` | Titolo contiene [RINVIATO]/[ANNULLATO] ma stato diverso |
| `evento_passato_confermato` | Evento passato (>1 giorno) ancora in stato "confermato" |
| `sottocategoria_errata` | Evento creato da email non-Convocazione |
| `dati_incompleti` | Manca data_inizio |

#### Risolvi Anomalie Automaticamente
```http
POST /api/calendario/report/anomalie/risolvi-auto
```

Risolve automaticamente:
- Eventi passati confermati → marcati come `completato`
- Stati inconsistenti → corregge in base al prefisso titolo
- Sincronizza modifiche su Google Calendar

**Response:**
```json
{
  "success": true,
  "risolte": {
    "eventi_completati": 8,
    "stati_corretti": 2,
    "google_aggiornati": 10
  },
  "totale": 10
}
```

#### Risolvi Singola Anomalia
```http
DELETE /api/calendario/report/anomalie/{evento_id}?azione=completato
```

**Query Parameters:**
| Parametro | Tipo | Default | Descrizione |
|-----------|------|---------|-------------|
| `azione` | string | completato | Nuovo stato: completato, annullato, rinviato, confermato |

**Response:**
```json
{
  "success": true,
  "evento_id": 123,
  "stato_precedente": "confermato",
  "nuovo_stato": "completato"
}
```

#### Elimina Tutti gli Eventi
```http
DELETE /api/calendario/cleanup-all
```

**⚠️ ATTENZIONE:** Operazione irreversibile!

Elimina tutti gli eventi dal database locale e da Google Calendar.

**Response:**
```json
{
  "message": "Cleanup completato",
  "eventi_eliminati_locale": 50,
  "eventi_eliminati_google": 48,
  "errori": null
}
```

#### Sync Google Calendar
```http
POST /api/calendario/sync-google
```

**Query Parameters:**
| Parametro | Tipo | Default | Descrizione |
|-----------|------|---------|-------------|
| `limit` | int | 10 | Numero massimo eventi da importare |

**Response:**
```json
{
  "message": "Sincronizzazione completata",
  "eventi_importati": 5,
  "eventi_totali_google": 10
}
```

---

### Interpelli

#### Lista Interpelli
```http
GET /api/interpelli/
```

**Query Parameters:**
| Parametro | Tipo | Default | Descrizione |
|-----------|------|---------|-------------|
| `classe_concorso` | string | - | Es. A042, AB24 |
| `provincia` | string | - | Es. Taranto |
| `scaduti` | bool | - | Includi scaduti |

**Response:**
```json
{
  "items": [
    {
      "id": 1,
      "classe_concorso": "A042",
      "numero_posti": 2,
      "ore_settimanali": 18,
      "istituto": "ITST Pacinotti",
      "provincia": "Taranto",
      "data_scadenza": "2025-12-10T12:00:00Z"
    }
  ]
}
```

#### Dettaglio Interpello
```http
GET /api/interpelli/{id}
```

#### Parse Manuale
```http
POST /api/interpelli/parse
```

**Body:**
```json
{
  "email_id": 123
}
```

---

### Azioni

#### Lista Azioni
```http
GET /api/azioni/
```

**Query Parameters:**
| Parametro | Tipo | Default | Descrizione |
|-----------|------|---------|-------------|
| `stato` | string | - | IN_CODA, IN_ESECUZIONE, COMPLETATA, FALLITA |
| `tipo` | string | - | EVENTO_CALENDARIO, PARSE_INTERPELLO, etc. |
| `email_id` | int | - | Filtra per email |

**Response:**
```json
{
  "items": [
    {
      "id": 462,
      "email_id": 200,
      "tipo_azione": "EVENTO_CALENDARIO",
      "stato": "COMPLETATA",
      "risultato": {"evento_id": 157},
      "created_at": "2025-11-30T10:00:00Z",
      "executed_at": "2025-11-30T10:01:00Z"
    }
  ]
}
```

#### Riprova Azione
```http
POST /api/azioni/{id}/retry
```

**Response:**
```json
{
  "success": true,
  "new_stato": "IN_CODA"
}
```

---

### RAG Chat

#### Query Chat
```http
POST /api/rag/chat
```

**Body:**
```json
{
  "query": "Quali sono le procedure per il tesseramento?",
  "history": [
    {"role": "user", "content": "Ciao"},
    {"role": "assistant", "content": "Ciao! Come posso aiutarti?"}
  ]
}
```

**Response:**
```json
{
  "response": "Le procedure per il tesseramento sono...",
  "sources": [
    {
      "document": "guida_tesseramento.pdf",
      "page": 3,
      "relevance": 0.92
    }
  ]
}
```

#### Indicizza Documento
```http
POST /api/rag/index
```

**Body (multipart/form-data):**
- `file`: File da indicizzare
- `metadata`: JSON con metadati opzionali

---

### Regole

#### Lista Regole
```http
GET /api/rules/
```

**Response:**
```json
{
  "items": [
    {
      "id": 1,
      "nome": "Convocazioni � Calendario",
      "descrizione": "Crea evento per ogni convocazione",
      "attiva": true,
      "condizioni": {
        "operator": "AND",
        "rules": [
          {"field": "categoria", "operator": "uguale", "value": "comunicazione_scuola"},
          {"field": "sottocategoria", "operator": "uguale", "value": "convocazione"}
        ]
      },
      "azioni": ["EVENTO_CALENDARIO"]
    }
  ]
}
```

#### Crea Regola
```http
POST /api/rules/
```

#### Aggiorna Regola
```http
PUT /api/rules/{id}
```

#### Elimina Regola
```http
DELETE /api/rules/{id}
```

---

### Sistema

#### Health Check
```http
GET /api/health
```

**Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "ollama": "available"
}
```

#### Statistiche
```http
GET /api/stats
```

**Response:**
```json
{
  "emails": {
    "total": 500,
    "today": 15,
    "unread": 23,
    "spam": 45
  },
  "eventi": {
    "total": 157,
    "upcoming": 12
  },
  "azioni": {
    "pending": 3,
    "failed": 1
  }
}
```

---

### Google Integration

#### Stato Autenticazione
```http
GET /api/google/status
```

**Response:**
```json
{
  "authenticated": true,
  "email": "snals@gmail.com",
  "scopes": ["calendar", "drive"]
}
```

#### Avvia OAuth
```http
GET /api/google/auth
```

Redirect al flusso OAuth di Google.

#### Callback OAuth
```http
GET /api/google/callback
```

Endpoint interno per ricevere il token da Google.

---

## Codici di Errore

| Codice | Descrizione |
|--------|-------------|
| 400 | Bad Request - parametri non validi |
| 404 | Not Found - risorsa non trovata |
| 422 | Validation Error - dati non validi |
| 500 | Internal Server Error |

**Formato Errore:**
```json
{
  "detail": "Descrizione errore",
  "error_code": "VALIDATION_ERROR"
}
```

---

## Rate Limiting

Le API non hanno rate limiting esterno, ma il sistema interno limita:
- Email sending: max 30/ora, 5/minuto
- LLM requests: processate in coda sequenziale

---

**Ultimo aggiornamento:** 2025-12-11
**Versione API:** 1.4.1
