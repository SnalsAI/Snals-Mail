# Chat RAG - Guida Completa

Guida all'utilizzo del sistema Chat RAG (Retrieval-Augmented Generation) per interrogare la knowledge base SNALS con intelligenza artificiale.

## 📚 Indice

1. [Introduzione](#introduzione)
2. [Accesso](#accesso)
3. [Come Funziona](#come-funziona)
4. [Utilizzo Frontend](#utilizzo-frontend)
5. [Utilizzo API](#utilizzo-api)
6. [Documenti Indicizzati](#documenti-indicizzati)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)
9. [Architettura Tecnica](#architettura-tecnica)

## Introduzione

Il sistema Chat RAG permette di interrogare la knowledge base documentale SNALS usando domande in linguaggio naturale. Il sistema:

1. Cerca documenti rilevanti nella knowledge base
2. Utilizza un LLM (llama3.2:3b) per generare risposte basate sui documenti trovati
3. Cita sempre le fonti utilizzate

### Vantaggi

✅ **Risponde solo con informazioni verificate** - Usa solo i documenti indicizzati
✅ **Cita le fonti** - Ogni risposta include riferimenti ai documenti
✅ **Multilingua** - Supporta italiano e altre lingue
✅ **Veloce** - Risposta tipica in 10-30 secondi
✅ **Contestuale** - Comprende il contesto della domanda

## Accesso

### Frontend Web UI

**URL**: http://localhost:3001/chat-rag

**Accesso tramite menu**:
1. Apri l'applicazione web
2. Click su "Chat RAG" 💬 nel menu laterale
3. Inizia a fare domande!

### API REST

**Endpoint**: `POST /api/rag/chat`

**URL Completo**: http://localhost:8001/api/rag/chat

## Come Funziona

### Flusso di Elaborazione

```
1. Utente fa una domanda
   ↓
2. Sistema cerca documenti rilevanti
   • Vector similarity search in ChromaDB
   • Embedding multilingua (paraphrase-multilingual-mpnet-base-v2)
   • Recupera top 5 documenti più rilevanti
   ↓
3. Costruisce contesto
   • Combina testi documenti trovati
   • Aggiunge metadati (mittente, data, filename)
   ↓
4. Genera risposta con LLM
   • Prompt con regole chiare
   • LLM: llama3.2:3b (Ollama)
   • Temperature: 0.3 (risposta accurata)
   • Max tokens: 1000
   ↓
5. Ritorna risposta + fonti
   • Risposta testuale
   • Lista documenti utilizzati
   • Score di rilevanza per ogni fonte
```

### Esempio Concreto

**Domanda**: "Quali sono le scadenze per gli interpelli di novembre?"

**Processo**:
1. ✅ Cerca "scadenze", "interpelli", "novembre" nei documenti
2. ✅ Trova 3 PDF di interpelli UST con date novembre 2025
3. ✅ LLM legge i documenti e estrae le date
4. ✅ Risponde: "Secondo il Documento 1 (interpello A040), la scadenza è il 18 novembre 2025 ore 10:00..."

## Utilizzo Frontend

### Interfaccia Chat

#### Header
- **Titolo**: "Chat con Knowledge Base SNALS"
- **Sottotitolo**: Descrizione funzionalità

#### Area Messaggi
- **Messaggi Utente**: Allineati a destra, background blu/viola
- **Messaggi Assistente**: Allineati a sinistra, background grigio chiaro
- **Timestamp**: Ora invio messaggio
- **Typing Indicator**: Animazione durante elaborazione

#### Fonti Espandibili
Ogni risposta include un pulsante "📚 X fonti":

**Click per espandere e vedere**:
- **Filename**: Nome file PDF/documento
- **Mittente**: Chi ha inviato l'email
- **Data**: Data ricezione/emissione
- **Categoria**: Classificazione email
- **Testo Rilevante**: Snippet del documento (300 caratteri)
- **Score Rilevanza**: Percentuale match con query

#### Input Form
- **Campo testo**: Scrivi domanda
- **Pulsante invio**: "📤 Invia"
- **Stato disabled**: Durante elaborazione

### Esempi di Domande

#### Domande Generali
```
"Cosa dicono i documenti sugli interpelli?"
"Quali comunicazioni UST sono disponibili?"
"Riassumi i documenti di novembre 2025"
```

#### Domande Specifiche
```
"Qual è la scadenza per l'interpello A040?"
"Chi ha inviato l'interpello per scienze tessili?"
"Quali sono i requisiti per la classe di concorso A044?"
```

#### Domande con Filtri
```
"Mostrami solo interpelli UST Taranto"
"Cosa dice l'email del 20 novembre?"
"Quali documenti parlano di supplenze?"
```

## Utilizzo API

### Endpoint Chat

#### Request

```bash
POST http://localhost:8001/api/rag/chat
Content-Type: application/json

{
  "query": "Quali sono le classi di concorso disponibili?",
  "n_results": 5,
  "filter_categoria": "comunicazione_ust_usr"  // opzionale
}
```

#### Parametri

| Parametro | Tipo | Required | Default | Descrizione |
|-----------|------|----------|---------|-------------|
| `query` | string | ✅ Sì | - | Domanda dell'utente |
| `n_results` | integer | ❌ No | 5 | Numero documenti da recuperare (1-20) |
| `filter_categoria` | string | ❌ No | null | Filtra per categoria email |
| `filter_sottocategoria` | string | ❌ No | null | Filtra per sottocategoria |
| `filter_mittente` | string | ❌ No | null | Filtra per mittente email |

#### Response

```json
{
  "query": "Quali sono le classi di concorso disponibili?",
  "answer": "Secondo i documenti disponibili, le classi di concorso menzionate sono:\n\n1. **A040** - Scienze e Tecnologie Elettriche ed Elettroniche (Documento 1)\n2. **A044** - Scienze e tecnologie tessili, dell'abbigliamento e della moda (Documento 2)\n\nEntrambe le classi hanno interpelli attivi per supplenze fino al 30/06/2026.",
  "sources": [
    {
      "document": "OGGETTO: INTERPELLO PER SUPPLENZA FINO AL 30.06.2026- 2 ore\nCDC - A040 (SCIENZE E TECNOLOGIE ELETTRICHE ED ELETTRONICHE)\na.s.2025/2026...",
      "metadata": {
        "filename": "Interpello nazionale a040.pdf",
        "mittente": "USP di Taranto <usp.ta@istruzione.it>",
        "data": "2025-11-14T11:53:56",
        "categoria": "comunicazione_ust_usr",
        "sottocategoria": "Interpello"
      },
      "distance": 0.35
    },
    {
      "document": "Oggetto: Secondo Interpello nazionale per supplenza su classe di concorso A044– Scienze e tecnologie tessili...",
      "metadata": {
        "filename": "SECONDO -INTERPELLO NAZIONALE _CDC_A044.pdf",
        "mittente": "USP di Taranto <usp.ta@istruzione.it>",
        "data": "2025-11-14T07:59:50",
        "categoria": "comunicazione_ust_usr",
        "sottocategoria": "Interpello"
      },
      "distance": 0.42
    }
  ],
  "sources_count": 2
}
```

### Altri Endpoint RAG

#### Query Documenti (senza LLM)

```bash
POST /api/rag/query
{
  "query": "interpelli",
  "n_results": 5
}

# Response: documenti rilevanti senza risposta generata
```

#### Statistiche

```bash
GET /api/rag/statistics

# Response
{
  "total_documents": 8,
  "collection_name": "snals_documents",
  "persist_directory": "storage/chroma_db"
}
```

#### Lista Documenti

```bash
GET /api/rag/documents?limit=10&offset=0

# Response: lista documenti indicizzati con metadati
```

## Documenti Indicizzati

### Criteri di Indicizzazione

Vengono **automaticamente** indicizzati:

1. ✅ Email da `info@snals.it` (comunicazioni SNALS centrale)
2. ✅ Email categoria `COMUNICAZIONE_UST_USR` (UST/USR/ATP)
3. ✅ Allegati PDF estratti (pdfplumber + PyPDF2)
4. ✅ Documenti Knowledge Base caricati manualmente

### Metadati Disponibili

Ogni documento include:

```json
{
  "filename": "nome_file.pdf",
  "mittente": "email@mittente.it",
  "data": "2025-11-20T10:30:00",
  "categoria": "comunicazione_ust_usr",
  "sottocategoria": "Interpello",
  "email_id": "123",
  "text_length": 4500
}
```

### Verifica Indicizzazione

```bash
# Statistiche
curl http://localhost:8001/api/rag/statistics

# Lista documenti
curl "http://localhost:8001/api/rag/documents?limit=50"
```

### Indicizzazione Manuale

Se un documento non è stato indicizzato automaticamente:

```bash
POST /api/rag/index-email
{
  "email_id": 123
}
```

## Best Practices

### Domande Efficaci

#### ✅ FARE

**Domande specifiche**:
- "Qual è la scadenza dell'interpello A040?"
- "Chi ha inviato l'email del 18 novembre?"
- "Quali sono i requisiti per la supplenza A044?"

**Domande aperte**:
- "Cosa dicono i documenti sugli interpelli di novembre?"
- "Riassumi le comunicazioni UST dell'ultima settimana"

**Domande comparative**:
- "Quali sono le differenze tra l'interpello A040 e A044?"
- "Confronta le scadenze degli interpelli"

#### ❌ EVITARE

**Domande troppo generiche**:
- "Dimmi tutto" → Meglio: "Riassumi i documenti disponibili"

**Informazioni non nei documenti**:
- "Qual è la capitale dell'Italia?" → Non è nella knowledge base

**Domande multiple insieme**:
- "Quali sono gli interpelli e le convocazioni e le comunicazioni?" → Dividi in 3 domande

### Interpretare i Risultati

#### Score di Rilevanza

- **90-100%**: Match perfetto, informazione molto probabilmente corretta
- **70-90%**: Match buono, informazione attendibile
- **50-70%**: Match moderato, verifica le fonti
- **< 50%**: Match basso, LLM potrebbe non avere info sufficienti

#### Citazioni Fonti

Il LLM cita sempre le fonti:
- "Secondo il Documento 1..."
- "Come indicato nel file interpello.pdf..."
- "L'email del 18 novembre riporta che..."

**Verifica sempre le fonti espandibili** per confermare l'informazione!

### Performance

#### Tempi di Risposta

- **Query veloce** (< 5 sec): Solo ricerca documenti
- **Chat con LLM** (~10-30 sec): Ricerca + generazione risposta
- **Dipende da**:
  - Numero documenti richiesti (n_results)
  - Lunghezza documenti
  - Complessità domanda

#### Limiti

- **Max documenti**: 20 per query (consigliato: 5)
- **Max tokens risposta**: 1000 (~750 parole)
- **Timeout LLM**: 60 secondi

## Troubleshooting

### Nessuna Risposta / Timeout

**Problema**: La chat non risponde o va in timeout.

**Soluzioni**:
```bash
# 1. Verifica Ollama
curl http://localhost:11434/api/tags
# Deve mostrare llama3.2:3b

# 2. Verifica backend logs
docker logs snals-backend --tail 100 | grep "Chat RAG"

# 3. Restart Ollama
docker restart snals-ollama

# 4. Riduce n_results
# Invece di n_results: 10, prova n_results: 3
```

### Risposta "Non ho trovato documenti rilevanti"

**Problema**: Sistema non trova documenti per la query.

**Soluzioni**:

1. **Verifica documenti indicizzati**:
```bash
curl http://localhost:8001/api/rag/statistics
# Se total_documents = 0, nessun documento indicizzato
```

2. **Riformula la domanda**:
   - Troppo specifica → Prova più generica
   - Usa termini presenti nei documenti
   - Evita abbreviazioni non standard

3. **Controlla filtri**:
   - Rimuovi filtri `filter_categoria`, `filter_mittente`
   - Prova query senza filtri

### Risposta Imprecisa

**Problema**: La risposta non è corretta o è vaga.

**Soluzioni**:

1. **Aumenta n_results**:
```json
{
  "query": "...",
  "n_results": 10  // invece di 5
}
```

2. **Espandi le fonti** e verifica:
   - Leggi i documenti originali
   - Controlla se il LLM ha interpretato correttamente

3. **Riformula più specificamente**:
   - Aggiungi dettagli: date, nomi, codici
   - Esempio: "interpello" → "interpello A040 novembre 2025"

### ChromaDB Errori

**Problema**: Errori vector database.

**Soluzione**:
```bash
# Reset ChromaDB (ATTENZIONE: elimina tutti i documenti!)
curl -X POST "http://localhost:8001/api/rag/reset?confirm=CONFIRM"

# Poi ri-indicizza le email
for id in {1..50}; do
  curl -X POST http://localhost:8001/api/rag/index-email \
    -H "Content-Type: application/json" \
    -d "{\"email_id\": $id}"
done
```

## Architettura Tecnica

### Stack Tecnologico

**Vector Database**:
- ChromaDB 0.4+ (persistent)
- Directory: `backend/storage/chroma_db/`

**Embedding Model**:
- `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`
- Dimensioni: 768
- Supporto: 50+ lingue (incluso italiano)

**LLM**:
- Modello: llama3.2:3b
- Provider: Ollama
- Temperature: 0.3
- Max tokens: 1000

**Frontend**:
- React 18 + TypeScript
- Axios per HTTP requests
- Custom CSS con animazioni

### Configurazione

#### Backend Settings

```python
# backend/app/services/rag_service.py

EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
COLLECTION_NAME = "snals_documents"
PERSIST_DIRECTORY = "storage/chroma_db"

# Chat settings
DEFAULT_N_RESULTS = 5
LLM_TEMPERATURE = 0.3
MAX_TOKENS = 1000
```

#### Prompt Template

Il sistema usa questo prompt template:

```
Sei un assistente esperto del sindacato SNALS.

La tua funzione è rispondere alle domande dell'utente
basandoti ESCLUSIVAMENTE sui documenti forniti nel contesto.

REGOLE:
- Rispondi SOLO usando le informazioni presenti nei documenti
- Se la risposta non è nei documenti, dillo chiaramente
- Cita sempre da quale documento provengono le informazioni
- Sii preciso e professionale
- Riporta esattamente date, numeri, riferimenti normativi
- Rispondi in italiano

DOCUMENTI DISPONIBILI:
[documenti recuperati...]

DOMANDA DELL'UTENTE:
[query utente...]

RISPOSTA:
```

### Chunking Strategy

Documenti lunghi vengono divisi in chunks:

```python
CHUNK_SIZE = 1000        # caratteri
CHUNK_OVERLAP = 200      # caratteri overlap
```

**Perché?**
- Migliora precisione search
- Riduce dimensione context LLM
- Permette citazioni più precise

### Esempio Flow Completo

```python
# 1. User query
user_query = "Qual è la scadenza interpello A040?"

# 2. Embedding query
query_embedding = embedding_model.encode(user_query)

# 3. Vector search
results = chroma_collection.query(
    query_embeddings=[query_embedding],
    n_results=5
)

# 4. Build context
context = "\n---\n".join([
    f"[Documento {i+1} - {doc['filename']}]\n{doc['text']}"
    for i, doc in enumerate(results['documents'])
])

# 5. LLM generation
prompt = f"{system_prompt}\n\nCONTESTO:\n{context}\n\nDOMANDA:\n{user_query}\n\nRISPOSTA:"
answer = llm.generate(prompt, temperature=0.3, max_tokens=1000)

# 6. Return with sources
return {
    "answer": answer,
    "sources": results['documents'],
    "sources_count": len(results['documents'])
}
```

---

## Conclusione

Il sistema Chat RAG fornisce un modo potente e affidabile per interrogare la knowledge base SNALS.

**Ricorda**:
- ✅ Domande specifiche = Risposte migliori
- ✅ Verifica sempre le fonti
- ✅ Il sistema risponde SOLO con info nei documenti
- ✅ Segnala eventuali problemi per migliorare il sistema

Per supporto: https://github.com/SnalsAI/Snals-Mail/issues
