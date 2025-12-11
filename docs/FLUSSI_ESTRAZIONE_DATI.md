# Flussi di Estrazione Dati - SNALS Email Agent

## Panoramica

Il sistema SNALS Email Agent utilizza diversi flussi di estrazione dati per processare le email e estrarre informazioni strutturate. Questo documento descrive in dettaglio ogni flusso.

---

## 1. Pipeline Principale Email

### 1.1 Ingestion Email (`email_ingest.py`)

**Descrizione**: Scarica email dai server POP3 (normale e PEC) ed estrae dati grezzi.

**Flusso**:
```
Server POP3 → connect_pop3() → fetch_emails()
                                    │
                                    ├── _decode_header() → Mittente, Oggetto
                                    ├── _extract_body() → Corpo text + HTML
                                    └── _extract_attachments() → Allegati + PDF text
```

**Dati estratti**:
- `message_id`: ID univoco messaggio
- `mittente`: Email mittente (decodificata)
- `destinatario`: Email destinatario
- `oggetto`: Oggetto (decodificato)
- `corpo`: Corpo testo (con fallback HTML→text)
- `corpo_html`: Corpo HTML originale
- `allegati_nomi`: Lista nomi allegati
- `allegati_path`: Path file salvati
- `allegati_testo`: Testo estratto dai PDF (Dict {filename: testo})

**Gestione PEC** (`EmailPECClient`):
- Rileva buste PEC (postacert.eml)
- Estrae messaggio reale dall'allegato .eml interno
- Sostituisce mittente/oggetto/corpo con quelli reali

### 1.2 Estrazione Testo PDF (`_extract_attachments`)

**Librerie utilizzate**:
1. **pdfplumber** (primario): Migliore per layout complessi e tabelle
2. **PyPDF2** (fallback): Se pdfplumber non è disponibile

**Limiti**:
- Max 5 MB per file
- Max 10 pagine per PDF
- Max 10.000 caratteri per file

---

## 2. Categorizzazione Email

### 2.1 Categorizer Ibrido (`categorizer.py`)

**Strategia a cascata**:
```
Email → Rilevazione Ricevute PEC → Parsing Buste PEC → Rule-Based → Validazione LLM → LLM Fallback
```

**Step 1: Rilevazione rapida**
- Ricevute PEC: `CONSEGNA:`, `ACCETTAZIONE:` → `RICEVUTA_PEC`
- Spam: Pattern commerciali, truffe, phishing → `SPAM`

**Step 2: Rule-Based Classification** (`rule_based_classifier.py`)
- Identifica tipo mittente: `SCUOLA`, `USP_UST`, `SNALS_CENTRALE`, `ALTRO`
- Pattern regex per codici meccanografici: `[4 LETTERE][6 ALFANUM]@istruzione.it`
- Analizza contenuto per sottocategorie

**Step 3: Validazione Semantica LLM**
- Verifica coerenza categoria/contenuto
- Confidence threshold: 0.75
- Mittenti istituzionali verificati hanno priorità

**Step 4: LLM Categorization**
- Prompt specifici per tipo mittente
- Temperature: 0.2 (bassa per determinismo)
- Formato risposta: JSON

**Categorie supportate**:
- `COMUNICAZIONE_SCUOLA` (Convocazione, Contrattazione, Comunicazione)
- `COMUNICAZIONE_UST_USR`
- `COMUNICAZIONE_SNALS_CENTRALE`
- `RICHIESTA_TESSERAMENTO`
- `RICHIESTA_APPUNTAMENTO`
- `INFO_GENERICHE`
- `SPAM`
- `VARIE`
- `RICEVUTA_PEC`

---

## 3. Interpretazione Email

### 3.1 Email Interpreter (`interpreter.py`)

**Input**: Email categorizzata
**Output**: JSON con dati strutturati

**Flusso**:
```
Email → Parse Buste PEC → Estrai Allegati → Combina Testo → LLM Interpretation → JSON
```

**Estrazione specifica per categoria**:
- **Convocazioni**: data, ora, luogo, scuola, argomento
- **Appuntamenti**: disponibilità, argomento, modalità
- **Tesseramento**: dati richiedente, tipo richiesta

**Limiti**: Max 5.000 caratteri per LLM

---

## 4. Estrazione Dati Convocazioni

### 4.1 Smart Convocazione Extractor (`smart_convocazione_extractor.py`)

**Strategia multi-layer**:
```
1. REGEX (veloce, deterministico)
        ↓
2. VALIDAZIONE LLM LOCALE (verifica accuratezza)
        ↓
3. LLM LOCALE (estrazione completa)
        ↓
4. OPENAI FALLBACK (se necessario)
```

**Campi estratti**:
| Campo | Descrizione | Formato |
|-------|-------------|---------|
| `data_convocazione` | Data evento | `YYYY-MM-DD` |
| `ora_convocazione` | Ora evento | `HH:MM` |
| `luogo` | Indirizzo | Stringa |
| `sede` | Nome sede/sala | Stringa |
| `convocante` | Chi convoca | Stringa |
| `oggetto_riunione` | Scopo riunione | Stringa |

**Pattern Regex date**:
- Testuale: `28 novembre 2025`, `il 15 dicembre`
- Numerico: `28/11/2025`, `28.11.25`

**Pattern Regex ora**:
- Con contesto: `ore 09:00`, `alle 14:30`, `h. 15:00`
- Standalone: `09:00` (filtrato per escludere timestamp)

**Esclusioni automatiche**:
- Timestamp di protocolli: `del 20/11/2025 10:26`
- Date intestazione (non convocazione)

**Soglie completezza**:
- 100%: Usa solo regex
- ≥75%: Valida con LLM e usa regex
- <75%: Estrazione completa con LLM

### 4.2 Sanity Check Calendario (`unified_extractor.py`)

**Descrizione**: Validazione post-estrazione per bloccare dati incoerenti.

**Validazioni eseguite**:
| Campo | Validazione | Azione se fallisce |
|-------|-------------|-------------------|
| `data_inizio` | Non nel passato (>30gg) né futuro (>2 anni) | `data_inizio = None` |
| `ora_inizio` | Formato valido HH:MM, ore 0-23, minuti 0-59 | `ora_inizio = None` |
| `luogo` | Esclude pattern non validi ("Ai Rappresentanti", etc.) | `luogo = None` |

**Flag risultato**:
```python
result['_sanity_passed'] = True/False
result['_sanity_issues'] = ['data_vecchia', 'ora_invalida', ...]
```

**Pipeline completa**:
```
1. REGEX → 2. NLP → 3. LLM → 4. ChatGPT → 5. VALIDAZIONE → 6. SANITY CHECK
                                                               │
                                                   ┌───────────┴───────────┐
                                                   │                       │
                                              [PASSED]                [FAILED]
                                                   │                       │
                                            Dati validati        Dati azzerati +
                                                                 Issue tracciato
```

### 4.3 Soglia Minima Creazione Eventi (`action_executor.py`)

**Descrizione**: Blocca creazione eventi con dati insufficienti.

**Condizioni di blocco**:
| Condizione | Soglia | Risultato |
|------------|--------|-----------|
| Completezza | < 40% | `manual_intervention_required` |
| Sanity check | Fallito | `manual_intervention_required` |
| Data inizio | Mancante | `manual_intervention_required` |

**Risposta errore**:
```json
{
  "status": "manual_intervention_required",
  "error": "Completezza dati insufficiente: 33%",
  "extracted_data": {"ora_inizio": "15:00"},
  "message": "⚠️ INTERVENTO UMANO RICHIESTO: Dati incompleti..."
}
```

---

## 5. Estrazione Dati Interpelli

### 5.1 Interpello Parser (`interpello_parser.py`)

**Strategie disponibili**:
1. `regex`: Solo pattern matching
2. `ollama`: LLM locale
3. `openai`: OpenAI API
4. `smart`: Ibrido (default)

### 5.2 Smart Interpello Extractor (`smart_extractor.py`)

**Campi estratti**:
| Campo | Descrizione |
|-------|-------------|
| `classe_concorso` | Codice (A042, AB24, etc.) |
| `numero_posti` | Intero |
| `ore_settimanali` | Intero |
| `data_scadenza` | `YYYY-MM-DDTHH:MM:SS` |
| `data_inizio_servizio` | `YYYY-MM-DD` |
| `data_fine_contratto` | `YYYY-MM-DD` |
| `provincia` | Es: "Taranto" |
| `citta` | Nome città |
| `istituto` | Nome scuola completo |
| `indirizzo` | Indirizzo completo |
| `tipo_contratto` | supplenza, spezzone, etc. |
| `link_candidatura` | URL |

**Validazione classe di concorso**:
- Normalizzazione: `A-42` → `A042`
- Verifica contro database ufficiale
- Metadata validazione inclusi nel risultato

---

## 6. Estrazione Allegati

### 6.1 Attachment Text Extractor (`attachment_extractor.py`)

**Tipi supportati**:
| Estensione | Libreria | Note |
|------------|----------|------|
| `.txt` | built-in | Lettura diretta |
| `.pdf` | pdfplumber/PyPDF2 | Con estrazione tabelle |
| `.docx` | python-docx | Include tabelle |
| `.doc` | textract | Formato legacy |
| `.eml` | email (stdlib) | Parse completo |
| `.msg` | extract-msg | Outlook |

**Parsing EML completo** (`parse_eml_complete`):
- Estrae: `from`, `subject`, `body`
- Preferisce text/plain, fallback a text/html
- Usato per buste PEC

**File tecnici ignorati**:
- `.p7s` (firma digitale)
- `.xml` (daticert PEC)

---

## 7. Creazione Eventi Calendario

### 7.1 Action Executor - Calendar Event (`action_executor.py`)

**Flusso completo**:
```
Email con Convocazione
        ↓
SmartConvocazioneExtractor.extract()
        ↓
Inferenza sede (se mancante, da SchoolIdentifier)
        ↓
Rilevamento modifiche (rinvio/annullamento)
        ↓
    ┌───────────────────┐
    │ Evento esistente? │
    └─────────┬─────────┘
              │
    ┌─────────┴─────────┐
    │                   │
  [SÌ]               [NO]
    │                   │
Aggiorna evento   Crea nuovo evento
(titolo, stato)   (locale + Google Calendar)
```

### 7.2 Coda LLM (`llm_queue_service.py`)

**Problema risolto**: Chiamate LLM concorrenti causavano timeout/500 su Ollama.

**Soluzione**: Coda database con worker singleton.

**Flusso**:
```
Richiesta LLM → enqueue() → RichiestaLLM in DB → Worker Thread
                                                       │
                                              _process_next_request()
                                                       │
                                              LLMClient.generate()
                                                       │
                                              Salva risposta in DB
                                                       │
                                              wait_for_result() ritorna
```

**Stati richiesta**:
- `IN_CODA`: In attesa
- `IN_ELABORAZIONE`: Worker sta processando
- `COMPLETATA`: Risposta salvata
- `FALLITA`: Errore

**Parametri**:
- Priorità: 1 (alta) → 10 (bassa)
- Timeout wait: 120s default
- Pausa tra richieste: 2s

---

## 8. Identificazione Scuole

### 8.1 School Identifier (`school_identifier.py`)

**Database**: CSV con tutte le scuole italiane

**Dati per scuola**:
- Codice meccanografico
- Denominazione
- Comune
- Indirizzo
- Provincia

**Uso principale**:
- Inferenza sede per convocazioni
- Identificazione zona per inoltro delegati
- Validazione mittenti scuole

---

## 9. Regole e Azioni

### 9.1 Rules Engine (`rules_engine.py`)

**Valutazione condizioni**:
- Formato semplice: `{"categoria": "valore"}`
- Formato avanzato: `{"operator": "AND", "rules": [...]}`

**Condizioni supportate**:
- `uguale`, `diverso`
- `contiene`, `non_contiene`
- `inizia_con`, `finisce_con`
- `regex`
- `maggiore`, `minore`
- `in_lista`
- `vuoto`, `non_vuoto`
- `scuola_in_zona` (speciale)

**Azioni create**:
| Tipo | Descrizione |
|------|-------------|
| `BOZZA_RISPOSTA` | Genera bozza con LLM |
| `EVENTO_CALENDARIO` | Crea evento |
| `PARSE_INTERPELLO` | Estrai dati interpello |
| `INOLTRA_EMAIL` | Inoltra a destinatari |
| `INOLTRA_DELEGATI_ZONA` | Inoltra a delegati zona |
| `SINTESI` | Genera sintesi |
| `INDICIZZA_RAG` | Indicizza in RAG |
| `SPAM` | Marca come spam |

---

## 10. Normalizzazione Dati

### 10.1 Date

**Input supportati**:
- ISO: `2025-11-28T11:00:00Z`
- Italiano: `28/11/2025`
- Testuale: `28 novembre 2025`

**Normalizzazione**:
```python
# ISO → data semplice
if 'T' in data_str:
    data_str = data_str.split('T')[0]

# Italiano → ISO
if '/' in data_str:
    parts = data_str.split('/')
    data_str = f"{parts[2]}-{parts[1]}-{parts[0]}"
```

### 10.2 Orari

**Input supportati**:
- `09:00`, `9:00`
- `ore 9:00`, `alle 9.00`
- `h. 15:00`, `h 15:00`

**Normalizzazione**:
```python
ora_str = re.sub(r'^(ore|alle|h\.?|at)\s*', '', ora_str)
ora_str = ora_str.replace('.', ':')
```

### 10.3 Luoghi

**Problema**: Campo luogo può essere stringa o dict.

**Normalizzazione** (`_normalize_luogo`):
```python
if isinstance(luogo, dict):
    for key in ['sede/indirizzo', 'indirizzo', 'sede', 'address', 'luogo']:
        if key in luogo:
            return str(luogo[key])
    return ', '.join(v for v in luogo.values() if v)
return str(luogo)
```

---

## 11. Diagramma Flusso Completo

```
┌─────────────────────────────────────────────────────────────────┐
│                         EMAIL INBOX                              │
│                    (POP3 Normale + PEC)                         │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                     EMAIL INGEST SERVICE                         │
│   ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐   │
│   │ Decode Header │  │ Extract Body │  │ Extract Attachments│   │
│   └──────────────┘  └──────────────┘  └────────────────────┘   │
│                                              │                   │
│                                     ┌────────┴────────┐         │
│                                     │  PDF → pdfplumber │        │
│                                     │  EML → email lib  │        │
│                                     │  DOCX → python-docx│       │
│                                     └─────────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                     CATEGORIZER (Ibrido)                         │
│   ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐   │
│   │ Rule-Based   │→│ LLM Validate  │→│  LLM Categorize    │    │
│   │ (regex, dom) │  │ (semantic)    │  │  (fallback)        │   │
│   └──────────────┘  └──────────────┘  └────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      RULES ENGINE                                │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │ Evaluate Conditions → Create Actions → Execute Actions    │  │
│   └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                               │
           ┌───────────────────┼───────────────────┐
           │                   │                   │
           ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────┐
│ Interpello      │ │ Calendar Event  │ │ Draft Response      │
│ Parser          │ │ Creator         │ │ Generator           │
│ ┌─────────────┐ │ │ ┌─────────────┐ │ │ ┌─────────────────┐ │
│ │Smart Extract│ │ │ │Smart Conv.  │ │ │ │ RAG + LLM       │ │
│ │+ Validation │ │ │ │Extractor    │ │ │ │ (Celery task)   │ │
│ └─────────────┘ │ │ └─────────────┘ │ │ └─────────────────┘ │
└─────────────────┘ └─────────────────┘ └─────────────────────┘
           │                   │                   │
           ▼                   ▼                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                         DATABASE                                 │
│   ┌────────┐ ┌────────────┐ ┌──────────┐ ┌─────────────────┐   │
│   │ Email  │ │Interpello  │ │ Evento   │ │ Bozze Risposta  │   │
│   │        │ │            │ │Calendario│ │                 │    │
│   └────────┘ └────────────┘ └──────────┘ └─────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 12. Configurazione

### Variabili Ambiente Rilevanti

```env
# LLM
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL_INTERPRETATION=llama3.2:3b
OLLAMA_MODEL_GENERATION=llama3.2:1b
OLLAMA_MODEL_CATEGORIZATION=llama3.2:3b

# OpenAI (fallback)
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
OPENAI_DAILY_LIMIT_EUR=1.0

# Interpello Parser
INTERPELLO_PARSER_STRATEGY=smart

# Attachments
ATTACHMENTS_PATH=/backend/attachments
```

---

## 13. Troubleshooting

### Errori Comuni

| Errore | Causa | Soluzione |
|--------|-------|-----------|
| Timeout LLM | Chiamate concorrenti | Usa `llm_queue_service` |
| Data non estratta | Formato non riconosciuto | Aggiungi pattern regex |
| PDF vuoto | Scansione immagine | OCR non supportato |
| PEC non parsata | Busta malformata | Check allegati .eml |

### Log da Monitorare

```bash
# Estrazione convocazioni
grep "Smart" /logs/backend.log | grep -i "convocazione"

# Coda LLM
grep "LLM Queue" /logs/backend.log

# Errori categorizzazione
grep "Categoria" /logs/backend.log | grep -i "error\|warning"
```

---

## 14. Monitoraggio Anomalie Calendario

### 14.1 Endpoint Anomalie (`/api/calendario/report/anomalie`)

**Descrizione**: Rileva incoerenze negli eventi calendario esistenti.

**Tipi di anomalie**:

| Tipo | Descrizione | Severità |
|------|-------------|----------|
| `stato_inconsistente` | Titolo contiene [RINVIATO]/[ANNULLATO] ma stato ≠ rinviato/annullato | Alta |
| `evento_passato_confermato` | Evento passato ancora in stato "confermato" | Media |
| `sottocategoria_errata` | Evento creato da email non-convocazione | Alta |
| `dati_incompleti` | Manca data o luogo | Media |

**Response**:
```json
{
  "totale_anomalie": 8,
  "per_tipo": {
    "evento_passato_confermato": 7,
    "sottocategoria_errata": 1
  },
  "anomalie": [
    {
      "tipo": "evento_passato_confermato",
      "evento_id": 157,
      "titolo": "Convocazione tavolo...",
      "dettaglio": "Evento del 27/11/2025 ancora confermato",
      "azione_suggerita": "Verificare se è avvenuto o va eliminato"
    }
  ]
}
```

**Sottocategorie valide per eventi**:
- `convocazione`
- `rinvio`
- `contrattazione integrativa`
- `assemblea`
- `rsu`

---

*Documentazione aggiornata il 2025-11-30*
