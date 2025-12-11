# Snals Mail Agent - Implementation Plan

## Stato Attuale

### ✅ Completato
- Sistema di categorizzazione email (ibrido rule-based + LLM)
- Gestione PEC con estrazione buste
- Calendario eventi automatico (Google Calendar)
- Upload automatico allegati su Google Drive
- Sistema regole con condizioni e azioni
- RAG per indicizzazione email e allegati
- Sezione Interpelli con parsing AI in background (Celery)
- Background processing con Celery e timeout lunghi per Ollama

### 🔄 In Corso
- Task interpello in esecuzione (background processing funzionante)

---

## Nuove Funzionalità Richieste

### 1. Draft Risposte Intelligenti con RAG Integration

#### Obiettivo
Migliorare la qualità delle bozze di risposta utilizzando il RAG per recuperare:
- Risposte precedenti simili
- Normativa rilevante
- Documenti di riferimento
- Prassi consolidate

#### Implementazione

##### Backend
**File: `/backend/app/services/draft_generator.py`** (nuovo)
- Classe `SmartDraftGenerator`
- Metodi:
  - `generate_draft_with_context(email, categoria, llm_client, rag_service)`
  - `_retrieve_relevant_context(email_text, categoria, limit=5)`
  - `_build_enriched_prompt(email, relevant_docs)`

```python
class SmartDraftGenerator:
    def generate_draft_with_context(self, email, categoria):
        # 1. Query RAG per documenti rilevanti
        query = f"{email.oggetto} {email.corpo[:500]}"
        relevant_docs = rag_service.search(
            query=query,
            filter_categoria=categoria,
            limit=5
        )

        # 2. Costruisci prompt arricchito
        context = self._format_context(relevant_docs)
        prompt = f"""
Sei un assistente SNALS. Genera una risposta professionale.

EMAIL RICEVUTA:
{email.corpo}

DOCUMENTI DI RIFERIMENTO:
{context}

Genera una risposta che:
- Faccia riferimento alla normativa/documentazione pertinente
- Sia coerente con risposte precedenti su casi simili
- Includa riferimenti specifici quando necessario
"""

        # 3. Genera con timeout lungo in background
        return llm_client.generate(prompt, timeout=180.0)
```

**Modifiche necessarie:**
- `action_executor.py:_execute_draft_response()` → usa `SmartDraftGenerator`
- Nuovo task Celery `draft_tasks.py` per elaborazione in background
- Aggiunta metadati alle bozze: `referenced_documents: [rag_doc_ids]`

##### Frontend
**Miglioramenti `EmailDetail.tsx`:**
- Mostra documenti di riferimento usati per la bozza
- Link ai documenti RAG citati
- Indicatore "Draft arricchito con knowledge base"

**Stima:** 6-8 ore
**Priorità:** Alta
**Dipendenze:** RAG funzionante, Background tasks

---

### 2. Knowledge Base Manager (RAG Enhancement)

#### Obiettivo
Permettere upload e gestione manuale di documenti nel RAG:
- Normativa
- Circolari ministeriali
- Documenti interni SNALS
- FAQ consolidate
- Modelli di risposta

#### Implementazione

##### Modello Database
**File: `/backend/app/models/knowledge_document.py`** (nuovo)

```python
class KnowledgeDocument(Base):
    """Documento knowledge base caricato manualmente"""
    __tablename__ = "knowledge_documents"

    id = Column(Integer, primary_key=True)
    titolo = Column(String(500), nullable=False)
    descrizione = Column(Text)
    file_path = Column(String(1000))

    # Categorizzazione
    tipo_documento = Column(Enum(TipoDocumento))  # normativa, circolare, faq, modello
    categoria_email = Column(Enum(EmailCategory))  # a quale categoria si riferisce

    # Metadati ricercabili
    tags = Column(JSON)  # ["GPS", "graduatorie", "2024/2025"]
    ente_emittente = Column(String(200))  # "Ministero Istruzione", "SNALS Nazionale"
    data_emissione = Column(Date)
    numero_protocollo = Column(String(100))

    # RAG
    indexed_in_rag = Column(Boolean, default=False)
    rag_document_ids = Column(JSON)  # IDs documenti ChromaDB

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    caricato_da = Column(String(100))  # username
```

**Enum `TipoDocumento`:**
```python
class TipoDocumento(enum.Enum):
    NORMATIVA = "normativa"  # Leggi, decreti
    CIRCOLARE = "circolare"  # Circolari ministeriali
    FAQ = "faq"  # Domande frequenti
    MODELLO = "modello"  # Template risposte
    CONTRATTO = "contratto"  # CCNL, contratti
    PRASSI = "prassi"  # Procedure interne
    ALTRO = "altro"
```

##### Backend API
**File: `/backend/app/api/routes/knowledge.py`** (nuovo)

```python
@router.post("/upload")
async def upload_knowledge_document(
    file: UploadFile,
    titolo: str,
    tipo_documento: str,
    categoria_email: Optional[str],
    tags: Optional[str],  # JSON string
    ...
):
    # 1. Salva file su disco
    # 2. Estrai testo (PDF, DOCX, ecc.)
    # 3. Crea record DB
    # 4. Schedula indicizzazione RAG in background
    return {"success": True, "document_id": doc.id}

@router.get("/")
def list_knowledge_documents(
    tipo: Optional[str],
    categoria: Optional[str],
    tags: Optional[List[str]],
    search: Optional[str],
    ...
):
    # Query con filtri avanzati
    # Ricerca full-text su titolo/descrizione
    # Filtro per tags, tipo, categoria
    pass

@router.delete("/{doc_id}")
def delete_knowledge_document(doc_id: int):
    # 1. Rimuovi da RAG (ChromaDB)
    # 2. Elimina file
    # 3. Elimina record DB
    pass

@router.post("/{doc_id}/reindex")
def reindex_knowledge_document(doc_id: int):
    # Re-indicizza in RAG con metadati aggiornati
    pass
```

**Task Celery:** `knowledge_tasks.py`
```python
@celery_app.task
def index_knowledge_document(doc_id: int):
    """
    Indicizza documento knowledge in RAG con metadati arricchiti.
    Timeout: 10 minuti
    """
    doc = db.query(KnowledgeDocument).get(doc_id)

    metadata = {
        "source": "knowledge_base",
        "document_id": doc.id,
        "tipo": doc.tipo_documento,
        "categoria": doc.categoria_email,
        "tags": doc.tags,
        "ente": doc.ente_emittente,
        "data": doc.data_emissione.isoformat(),
        "protocollo": doc.numero_protocollo,
    }

    rag_service.index_document(
        file_path=doc.file_path,
        metadata=metadata
    )
```

##### Frontend
**Nuova pagina: `/frontend/src/pages/KnowledgeBase.tsx`**

Features:
- **Upload area** (drag & drop) con form metadati
- **Filtri avanzati:**
  - Tipo documento (dropdown)
  - Categoria email (dropdown)
  - Tags (multi-select)
  - Ricerca full-text
  - Range date emissione
- **Tabella documenti** con:
  - Titolo, tipo, categoria, tags
  - Azioni: view, edit, reindex, delete
  - Badge "Indicizzato in RAG" (verde)
- **Dettaglio documento:**
  - Visualizzazione PDF inline
  - Modifica metadati
  - Gestione tags
  - Cronologia modifiche

**Componente `TagsInput.tsx`:**
- Input con autocomplete per tags esistenti
- Creazione nuovi tags al volo
- Visualizzazione tags come chips

**Stima:** 12-16 ore
**Priorità:** Alta
**Dipendenze:** RAG service, File upload handler

---

### 3. RAG Search Enhancement

#### Obiettivo
Migliorare ricerca RAG con:
- Filtri per metadati (tags, tipo documento, ente, data)
- Hybrid search (semantic + keyword)
- Ranking personalizzato

#### Implementazione

**File: `/backend/app/services/rag_service.py`**

Modifiche metodo `search()`:
```python
def search(
    self,
    query: str,
    filter_categoria: Optional[str] = None,
    filter_tags: Optional[List[str]] = None,
    filter_tipo_documento: Optional[str] = None,
    filter_source: Optional[str] = None,  # "email" o "knowledge_base"
    filter_date_range: Optional[tuple] = None,
    limit: int = 10,
    min_relevance_score: float = 0.5
):
    """
    Ricerca ibrida semantica + filtri metadati
    """
    # Costruisci where clause per ChromaDB
    where_conditions = {}

    if filter_categoria:
        where_conditions["categoria"] = filter_categoria

    if filter_tags:
        where_conditions["tags"] = {"$in": filter_tags}

    if filter_tipo_documento:
        where_conditions["tipo"] = filter_tipo_documento

    if filter_source:
        where_conditions["source"] = filter_source

    # Query ChromaDB con filtri
    results = self.collection.query(
        query_texts=[query],
        n_results=limit,
        where=where_conditions if where_conditions else None
    )

    # Filtra per relevance score
    filtered = [
        doc for doc in results
        if doc['distance'] >= min_relevance_score
    ]

    return filtered
```

**Frontend - Advanced Search Component:**
```tsx
<RAGSearchPanel>
  <input placeholder="Cerca documenti..." />

  <Filters>
    <select name="source">
      <option value="">Tutte le fonti</option>
      <option value="email">Solo email</option>
      <option value="knowledge_base">Solo knowledge base</option>
    </select>

    <TagsFilter multiple>
      {/* Auto-complete tags */}
    </TagsFilter>

    <DateRangePicker />
  </Filters>

  <Results>
    {/* Lista documenti con score di rilevanza */}
  </Results>
</RAGSearchPanel>
```

**Stima:** 6-8 ore
**Priorità:** Media
**Dipendenze:** Knowledge Base

---

## Plan di Testing Completo

### 1. Test Interpelli Background Processing

**Test Case 1: Parsing Interpello Base**
```
✅ Email #79 viene schedulata per parsing
✅ Task Celery viene eseguito
✅ Timeout lungo (5 min) permette completamento
✅ Interpello viene creato con dati estratti
✅ Azione viene marcata COMPLETATA
```

**Test Case 2: Parsing Fallito con Retry**
```
- Simula errore temporaneo Ollama
- Verifica retry automatico (max 3 tentativi)
- Verifica delay tra retry (5 minuti)
- Verifica azione marcata FALLITA dopo 3 retry
```

**Test Case 3: Interpelli Scaduti**
```
- Crea interpello con data_scadenza passata
- Task giornaliero check_expired_interpelli
- Verifica cambio stato da "aperto" a "scaduto"
```

---

### 2. Test Draft con RAG

**Test Case 1: Draft Base (senza RAG)**
```
- Email richiesta informazioni GPS
- Genera bozza senza documenti rilevanti
- Verifica risposta generica ma corretta
```

**Test Case 2: Draft Arricchito (con RAG)**
```
- Carica normativa GPS nel knowledge base
- Email richiesta informazioni GPS
- Genera bozza con RAG
- Verifica:
  ✅ Risposta cita normativa specifica
  ✅ Metadati bozza includono referenced_documents
  ✅ Frontend mostra link a documenti citati
```

**Test Case 3: Draft Background Processing**
```
- Email complessa richiede timeout lungo
- Bozza generata in background (Celery)
- Verifica stato azione: IN_CODA → COMPLETATA
- Verifica bozza salvata correttamente
```

---

### 3. Test Knowledge Base

**Test Case 1: Upload Documento**
```
Input:
- File: "Circolare_GPS_2024.pdf"
- Tipo: CIRCOLARE
- Categoria: comunicazione_ust_usr
- Tags: ["GPS", "2024/2025", "graduatorie"]
- Ente: "Ministero Istruzione"

Verifica:
✅ File salvato su disco
✅ Record DB creato
✅ Task indicizzazione schedulato
✅ Dopo task: indexed_in_rag = True
✅ rag_document_ids popolato
```

**Test Case 2: Ricerca Knowledge Base**
```
- Upload 5 documenti vari tipi
- Ricerca "graduatorie"
  ✅ Trova documenti pertinenti
- Filtro tipo=CIRCOLARE
  ✅ Mostra solo circolari
- Filtro tags=["GPS"]
  ✅ Mostra solo doc con tag GPS
- Filtro data_emissione > 2024-01-01
  ✅ Mostra solo doc recenti
```

**Test Case 3: Delete Documento**
```
- Upload documento e indicizza
- Delete documento
- Verifica:
  ✅ Rimosso da ChromaDB
  ✅ File eliminato da disco
  ✅ Record DB eliminato
  ✅ Ricerca RAG non lo trova più
```

---

### 4. Test RAG Enhanced Search

**Test Case 1: Hybrid Search**
```
- Query: "supplenze graduatorie esaurite"
- Verifica:
  ✅ Trova interpelli (semantic match)
  ✅ Trova normativa GPS (keyword match)
  ✅ Trova email precedenti simili
  ✅ Ordina per relevance score
```

**Test Case 2: Filtri Metadati**
```
Scenario: 10 documenti nel RAG
- 3 email interpelli
- 4 circolari ministeriali
- 3 FAQ interne

Query con filtri:
- source="email" → 3 risultati
- source="knowledge_base" + tipo="CIRCOLARE" → 4 risultati
- tags=["GPS"] → N risultati con tag
```

---

### 5. Test Integrazione End-to-End

**Test Case: Flusso Completo Interpello**
```
1. Email interpello arriva (POP3 polling)
2. Categorizzazione: comunicazione_ust_usr, sottocategoria: Interpello
3. Regola trigger: azione PARSE_INTERPELLO
4. Task Celery schedulato (background)
5. Ollama processa con timeout lungo (5 min)
6. Interpello creato con dati estratti
7. Frontend mostra interpello in pagina /interpelli
8. Utente può candidarsi tramite link

✅ Tutto automatico
✅ Nessun timeout
✅ Elaborazione accurata
```

**Test Case: Risposta Intelligente**
```
1. Upload normativa GPS nel knowledge base
2. Email richiesta info supplenze GPS
3. Sistema genera bozza con RAG
4. Bozza cita normativa caricata
5. Utente revisiona e invia

✅ Risposta accurata
✅ Riferimenti corretti
✅ Tempo ridotto per operatore
```

---

## Priorità e Timeline

### Sprint 1 (Alta Priorità) - 2-3 giorni
1. ✅ Sistema background processing interpelli (COMPLETATO)
2. Draft risposte con RAG integration (6-8h)
3. Knowledge Base - Model & API base (8h)

### Sprint 2 (Media Priorità) - 2-3 giorni
4. Knowledge Base - Frontend completo (8h)
5. RAG Enhanced Search con filtri (6-8h)
6. Testing completo funzionalità base (6h)

### Sprint 3 (Ottimizzazioni) - 1-2 giorni
7. Performance tuning RAG queries
8. UI/UX improvements
9. Documentazione utente

**Tempo totale stimato:** 5-8 giorni lavorativi

---

## Note Tecniche

### Ollama Configuration
- Timeout interpelli: 300s (5 min)
- Timeout draft risposte: 180s (3 min)
- Timeout categorizzazione: 60s (1 min)
- Retry automatici: 3 tentativi con delay 5 min

### Celery Workers
- Worker principale: 4 processi concorrenti
- Pool type: prefork (per compatibilità librerie)
- Task time limit: 600s (10 min hard limit)
- Soft time limit: 540s (9 min warning)

### RAG ChromaDB
- Embedding model: sentence-transformers (locale)
- Collection: "snals_documents"
- Persistence: `storage/chroma_db`
- Backup schedule: giornaliero

### Storage
- Email attachments: `storage/attachments/{email_id}/`
- Knowledge docs: `storage/knowledge_base/{year}/{month}/`
- Backup: Google Drive (automatico)

---

## Checklist Finale

Prima del deploy in produzione:

- [ ] Tutti i test passano (unit + integration)
- [ ] Documentazione API aggiornata (Swagger)
- [ ] Logs configurati correttamente
- [ ] Monitoring Celery tasks attivo
- [ ] Backup automatici configurati
- [ ] Guida utente knowledge base creata
- [ ] Training operatori su nuove funzionalità
- [ ] Rollback plan documentato
