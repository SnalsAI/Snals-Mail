# Snals Mail Agent - Stato Avanzamento Progetto

**Ultima modifica:** 19 Novembre 2025, 14:05
**Sessione:** Background Processing & Smart Features Implementation

---

## ✅ COMPLETATO (100%)

### 1. Sistema Background Processing Interpelli
**Stato:** ✅ PRODUZIONE

**Files creati/modificati:**
- `/backend/app/models/interpello.py` - Modello completo con tutti i campi
- `/backend/app/services/interpello_parser.py` - Parser AI con timeout 300s
- `/backend/app/tasks/interpello_tasks.py` - Task Celery con retry
- `/backend/app/api/routes/interpelli.py` - API endpoints completi
- `/backend/app/services/action_executor.py` - Azione PARSE_INTERPELLO integrata
- `/backend/app/integrations/llm_client.py` - Timeout configurabile
- `/frontend/src/pages/Interpelli.tsx` - UI completa con filtri e stats
- `/frontend/src/components/Layout.tsx` - Menu sidebar aggiornato
- `/frontend/src/App.tsx` - Routing aggiunto

**Caratteristiche:**
- ✅ Timeout Ollama: 5 minuti (300s)
- ✅ Retry automatici: 3 tentativi con 5 min delay
- ✅ Background processing via Celery
- ✅ Task giornaliero check scadenze (2:00 AM)
- ✅ API REST complete
- ✅ Frontend con filtri, stats, paginazione
- ✅ Gestione interpelli parziali (classe_concorso nullable)

**Test:**
- Email #79 processata con successo in background
- Task Celery funzionante e registrato
- Frontend accessibile su /interpelli

---

### 2. Draft Risposte Intelligenti con RAG
**Stato:** ✅ CODICE COMPLETO - DA TESTARE

**Files creati/modificati:**
- `/backend/app/services/draft_generator.py` - **NUOVO** SmartDraftGenerator
- `/backend/app/tasks/draft_tasks.py` - **NUOVO** Task Celery generate_smart_draft
- `/backend/app/services/action_executor.py` - Modificato per usare task background
- `/backend/app/tasks/__init__.py` - draft_tasks aggiunto

**Caratteristiche:**
- ✅ Recupero automatico documenti rilevanti da RAG (limit=5)
- ✅ Prompt arricchito con contesto normativa/FAQ
- ✅ Tracking documenti referenziati
- ✅ Fallback draft semplice se RAG fails
- ✅ Timeout: 3 minuti (180s)
- ✅ Retry automatici: 2 tentativi con 3 min delay
- ✅ Metadata completi in risultato azione

**Come funziona:**
1. Email richiede bozza risposta
2. Sistema query RAG per documenti rilevanti
3. LLM genera draft citando normativa trovata
4. Risultato include `referenced_documents` IDs
5. Frontend può mostrare link a documenti citati

**TODO Testing:**
- [ ] Testare con email reale
- [ ] Verificare quality draft con RAG vs senza
- [ ] Testare fallback mechanism

---

### 3. Knowledge Base - Backend
**Stato:** ✅ DATABASE & MODELLO COMPLETO

**Files creati:**
- `/backend/app/models/knowledge_document.py` - **NUOVO** Modello completo
- `/backend/alembic/versions/8e94fac1a209_*.py` - Migrazione applicata ✅

**Schema Database `knowledge_documents`:**
```sql
- id, titolo, descrizione
- file_path, file_name, file_size, file_type
- tipo_documento (ENUM: normativa, circolare, faq, modello, contratto, prassi, guida, altro)
- categoria_email (STRING: collegamento a EmailCategory)
- tags (JSON array): ["GPS", "2024/2025"]
- ente_emittente, data_emissione, numero_protocollo, anno_riferimento
- testo_estratto, testo_length
- indexed_in_rag (BOOL), rag_document_ids (JSON), rag_indexed_at
- created_at, updated_at, caricato_da, note_interne
- attivo (BOOL), verificato (BOOL)
```

**9 Indici creati per performance:**
- titolo, tipo_documento, categoria_email
- ente_emittente, data_emissione
- created_at, indexed_in_rag, attivo
- id (primary key)

---

## 🔧 IN SVILUPPO (50% completato)

### 4. Knowledge Base - API & Tasks

**Files da creare:**
- `/backend/app/api/routes/knowledge.py` - API CRUD completo
- `/backend/app/tasks/knowledge_tasks.py` - Task indicizzazione RAG

**API Endpoints richiesti:**
```python
POST /api/knowledge/upload
  - Upload file (PDF, DOCX)
  - Estrai testo
  - Salva metadati
  - Schedule indicizzazione RAG

GET /api/knowledge
  - List con filtri: tipo, categoria, tags, search, date_range
  - Paginazione

GET /api/knowledge/{id}
  - Dettaglio singolo documento

PUT /api/knowledge/{id}
  - Update metadati, tags

DELETE /api/knowledge/{id}
  - Rimuovi da RAG + filesystem + DB

POST /api/knowledge/{id}/reindex
  - Re-indicizza in RAG
```

**Task Celery richiesto:**
```python
@celery_app.task
def index_knowledge_document(doc_id: int):
    """
    1. Carica documento dal DB
    2. Estrai testo se non già fatto
    3. Prepara metadata arricchiti
    4. Indicizza in ChromaDB con tags
    5. Update doc: indexed_in_rag = True
    """
```

---

### 5. RAG Service Enhancement

**File da modificare:**
- `/backend/app/services/rag_service.py`

**Modifiche richieste al metodo `search()`:**
```python
def search(
    query: str,
    filter_categoria: Optional[str] = None,
    filter_tags: Optional[List[str]] = None,  # NUOVO
    filter_tipo_documento: Optional[str] = None,  # NUOVO
    filter_source: Optional[str] = None,  # "email" o "knowledge_base"
    filter_date_range: Optional[tuple] = None,  # NUOVO
    limit: int = 10,
    min_relevance_score: float = 0.5
):
    # Costruisci where clause ChromaDB con tutti i filtri
    # Query con filtri applicati
    # Return results filtrati per score
```

---

## 📋 TODO - Frontend & Testing

### 6. Frontend Knowledge Base
**File da creare:** `/frontend/src/pages/KnowledgeBase.tsx`

**Features richieste:**
- [ ] Upload area (drag & drop)
- [ ] Form metadati: titolo, tipo, categoria, tags, ente, data, protocollo
- [ ] Tabella documenti con filtri avanzati
- [ ] Tags input con autocomplete
- [ ] Visualizzazione PDF inline
- [ ] Edit metadati
- [ ] Delete con conferma
- [ ] Badge "Indicizzato in RAG"
- [ ] Reindex button per singolo doc

**Componenti da creare:**
- `TagsInput.tsx` - Input tags con chips
- `DocumentUploadForm.tsx` - Form upload completo
- `DocumentViewer.tsx` - Viewer PDF inline
- `AdvancedFilters.tsx` - Pannello filtri

### 7. Frontend Draft Enhancement
**File da modificare:** `/frontend/src/pages/EmailDetail.tsx`

**Features da aggiungere:**
- [ ] Mostra draft generate automaticamente
- [ ] Lista documenti referenziati
- [ ] Link a knowledge docs citati
- [ ] Badge "Arricchito con RAG"
- [ ] Indicatore stato task (pending/completed)

---

## 🧪 Testing Completo

### Test Interpelli Background
- [x] Email #79 schedulata e processata
- [x] Timeout 5 minuti funziona
- [ ] Interpello creato con dati corretti
- [ ] Frontend mostra interpello
- [ ] Filtri funzionano
- [ ] Stats corrette

### Test Draft Intelligenti
- [ ] Upload normativa GPS in knowledge base
- [ ] Email richiesta info GPS
- [ ] Draft generata con citazioni normativa
- [ ] referenced_documents popolato
- [ ] Frontend mostra docs citati
- [ ] Fallback senza RAG funziona

### Test Knowledge Base
- [ ] Upload PDF
- [ ] Testo estratto correttamente
- [ ] Indicizzazione RAG completa
- [ ] Ricerca con filtri tags
- [ ] Ricerca per tipo documento
- [ ] Delete rimuove da RAG
- [ ] Reindex aggiorna ChromaDB

### Test RAG Enhanced
- [ ] Search con filter_tags
- [ ] Search con filter_source
- [ ] Search con date_range
- [ ] Hybrid search semantic + keyword
- [ ] Relevance score filtering

---

## 📦 Deployment Checklist

### Backend
- [x] Migrazioni database applicate
- [x] Celery tasks registrati
- [ ] Restart backend: `docker-compose restart backend`
- [ ] Restart celery-worker: `docker-compose restart celery-worker`
- [ ] Verificare logs: `docker logs snals-backend --tail 50`
- [ ] Verificare tasks: `docker logs snals-celery-worker | grep registered`

### Frontend
- [x] Routes aggiunte
- [x] Components creati (Interpelli)
- [ ] Components da creare (KnowledgeBase)
- [ ] Build: `npm run build` (se necessario)
- [ ] Verificare HMR aggiornamento

### Testing
- [ ] API swagger docs: http://localhost:8001/docs
- [ ] Frontend: http://localhost:3001
- [ ] Test manuale flusso completo
- [ ] Verificare performance Ollama

---

## 📝 Comandi Utili

### Celery Worker Status
```bash
docker logs snals-celery-worker --tail 30
docker logs snals-celery-worker --follow
```

### Testare API Interpelli
```bash
# Statistiche
curl http://localhost:8001/api/interpelli/statistiche | jq

# Lista
curl http://localhost:8001/api/interpelli?limit=10 | jq

# Parse email
curl -X POST http://localhost:8001/api/interpelli/parse/79
```

### Database
```bash
# Migrations
docker exec snals-backend alembic upgrade head
docker exec snals-backend alembic current
docker exec snals-backend alembic history

# Check tables
docker exec -it snals-db psql -U snals_user -d snals_db -c "\dt"
docker exec -it snals-db psql -U snals_user -d snals_db -c "SELECT COUNT(*) FROM interpelli;"
docker exec -it snals-db psql -U snals_user -d snals_db -c "SELECT COUNT(*) FROM knowledge_documents;"
```

---

## 🎯 Prossimi Passi Prioritari

1. **Completare API Knowledge Base** (2-3h)
   - Creare `/backend/app/api/routes/knowledge.py`
   - Implementare upload file handler
   - Text extraction (PyPDF2/python-docx)
   - Integrazione con task Celery

2. **Creare Task Knowledge** (1-2h)
   - File `/backend/app/tasks/knowledge_tasks.py`
   - Indicizzazione RAG con metadati
   - Update database post-indicizzazione

3. **Potenziare RAG Service** (1-2h)
   - Modificare `search()` method
   - Aggiungere filtri avanzati
   - Testing filtri

4. **Frontend Knowledge Base** (4-6h)
   - Pagina principale
   - Componenti UI
   - Form upload
   - Filtri advanced

5. **Testing End-to-End** (2-3h)
   - Ogni funzionalità testata
   - Fix bugs
   - Ottimizzazioni performance

**Tempo totale stimato rimanente:** 10-16 ore

---

## 📚 Documentazione di Riferimento

- Implementation Plan: `/home/ubuntu/Snals-Mail/IMPLEMENTATION_PLAN.md`
- Progress Status: `/home/ubuntu/Snals-Mail/PROGRESS_STATUS.md` (questo file)
- API Docs: http://localhost:8001/docs (quando backend running)

---

## ⚡ Performance Note

### Ollama Timeouts Configurati
- Categorizzazione: 60s
- Interpretazione: 60s
- Draft generazione: 180s (3 min)
- Interpello parsing: 300s (5 min)

### Celery Task Limits
- Hard limit: 600s (10 min)
- Soft limit: 540s (9 min)
- Worker concurrency: 4 processi

### ChromaDB
- Collection: "snals_documents"
- Persist dir: `storage/chroma_db`
- Embedding model: sentence-transformers (locale)

---

**Fine documento di stato** ✅
