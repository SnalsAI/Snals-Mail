# NLP Training System Redesign

## Obiettivo
Riprogettare completamente il sistema di NLP Training separando spaCy e BERT con UI parallela, workflow guidato, e gestione pattern manuale.

## Requisiti Confermati
- **UI**: Sezioni parallele spaCy/BERT per confronto diretto
- **Approval**: Review semplificato (solo campi chiave, JSON nascosto)
- **Benchmark**: Sia confronto diretto che indipendenti
- **Entity Types**: Mantieni attuali (interpello, calendario, generico)
- **spaCy Training**: Ibrido (auto + pattern manuali)
- **BERT Training**: Opzionale (non obbligatorio nel workflow)
- **Workflow**: Guidato step-by-step

---

## Architettura Proposta

### Frontend - Nuova Struttura Componenti
```
frontend/src/
├── pages/
│   └── NLPTraining.tsx (orchestratore ~300 righe)
└── components/nlp-training/
    ├── types.ts
    ├── hooks/
    │   ├── useTrainingStatus.ts
    │   ├── useEmailSelection.ts
    │   ├── useSamples.ts
    │   ├── useBenchmark.ts
    │   └── useAsyncJob.ts
    ├── WorkflowStepper.tsx
    ├── EmailSelector.tsx
    ├── EnginePanel.tsx (riusabile spaCy/BERT)
    ├── SimplifiedSampleCard.tsx
    ├── PatternEditor.tsx
    ├── BenchmarkPanel.tsx
    └── BenchmarkComparison.tsx
```

### Backend - Separazione Routes
```
backend/app/api/routes/
├── training.py (semplificato - samples + analisi)
├── training_spacy.py (NUOVO - apply, benchmark, rollback)
├── training_bert.py (NUOVO - train, benchmark, rollback)
└── training_patterns.py (NUOVO - CRUD pattern manuali)

backend/app/services/
├── training_service.py (samples + ChatGPT analysis)
├── pattern_service.py (NUOVO - gestione pattern)
├── bert_training_service.py (esistente)
└── nlp_service.py (esistente)
```

---

## Layout UI

```
+----------------------------------------------------------+
|  NLP Training con ChatGPT                                |
+----------------------------------------------------------+
| [Status Cards: ChatGPT | Samples | Approvati | Benchmark]|
+----------------------------------------------------------+
| [Workflow Stepper: 1→2→3→4→5→6→7]                        |
+----------------------------------------------------------+
| [Email Selection + Tipo Analisi]                         |
+----------------------------------------------------------+
|  spaCy Panel            |  BERT Panel                    |
|  ─────────────────────  |  ─────────────────────         |
|  Pattern: 157           |  Modello: Non addestrato       |
|  F1: 78.5%              |  F1: --                        |
|  [Applica Training]     |  [Avvia Fine-tuning]           |
|  [Benchmark]            |  [Benchmark]                   |
|  [Pattern Editor]       |  [Config: epochs, lr]          |
|  [Storico Versioni]     |  [Storico Modelli]             |
+----------------------------------------------------------+
| [Confronto Diretto: spaCy vs BERT]                       |
+----------------------------------------------------------+
| [Sample Review Area - Pending Approval]                  |
|  +------------------+  +------------------+               |
|  | Interpello #240  |  | Calendario #253 |               |
|  | CC: A040         |  | Data: 03/12     |               |
|  | Mec: LTTF09000X  |  | Ora: 10:00      |               |
|  | [Approva][Rif.]  |  | [Approva][Rif.] |               |
|  +------------------+  +------------------+               |
+----------------------------------------------------------+
```

---

## Workflow Steps

1. **Select** - Seleziona email da analizzare
2. **Analyze** - Analizza con ChatGPT (async)
3. **Approve** - Rivedi e approva sample
4. **Benchmark Before** - [Opzionale] Misura performance attuale
5. **Apply** - Applica training (spaCy patterns e/o BERT)
6. **Benchmark After** - [Opzionale] Misura nuove performance
7. **Compare** - Confronta risultati

---

## Nuovi Endpoint Backend

### Pattern Management (`/training/patterns/`)
```
GET  /training/patterns          - Lista tutti i pattern
POST /training/patterns          - Aggiungi pattern manuale
PUT  /training/patterns/{id}     - Modifica pattern
DEL  /training/patterns/{id}     - Elimina pattern
POST /training/patterns/preview  - Anteprima su testo
```

### spaCy (`/training/spacy/`)
```
GET  /training/spacy/status      - Stato modello
POST /training/spacy/apply       - Applica sample approvati
POST /training/spacy/benchmark   - Benchmark solo spaCy
POST /training/spacy/rollback    - Ripristina versione
```

### BERT (`/training/bert/`)
```
GET  /training/bert/status       - Stato modello
POST /training/bert/train        - Fine-tuning
POST /training/bert/benchmark    - Benchmark solo BERT
POST /training/bert/rollback     - Ripristina versione
```

---

## Nuovi File Dati

### `manual_patterns.json`
```json
[
  {
    "id": "manual_cc_A041",
    "label": "CLASSE_CONCORSO",
    "pattern": "A041",
    "source": "manual",
    "created_at": "2025-12-15T10:00:00"
  }
]
```

### Benchmark con `engine` field
```json
{
  "name": "spacy_pre_20251215",
  "engine": "spacy",  // 'spacy' | 'bert'
  "metrics": {...}
}
```

---

## Fasi di Implementazione

### Fase 1: Foundation (Backend)
1. Creare `pattern_service.py` - CRUD pattern manuali
2. Creare `training_patterns.py` routes
3. Separare `training_spacy.py` routes
4. Separare `training_bert.py` routes
5. Aggiungere campo `engine` ai benchmark

### Fase 2: Frontend Types & Hooks
6. Creare `types.ts` con tutte le interfacce
7. Estrarre `useTrainingStatus.ts`
8. Estrarre `useEmailSelection.ts`
9. Estrarre `useSamples.ts`
10. Estrarre `useAsyncJob.ts`
11. Creare `useBenchmark.ts`

### Fase 3: Frontend Components
12. `WorkflowStepper.tsx` - Progress indicator
13. `SimplifiedSampleCard.tsx` - Review semplificato
14. `PatternEditor.tsx` - Editor pattern manuali
15. `EnginePanel.tsx` - Panel riusabile
16. `BenchmarkComparison.tsx` - Confronto side-by-side

### Fase 4: Integration
17. Riscrivere `NLPTraining.tsx` usando i nuovi componenti
18. Test integrazione
19. Fix e polish

---

## File Critici da Modificare

| File | Azione |
|------|--------|
| `frontend/src/pages/NLPTraining.tsx` | Riscrivere completamente |
| `backend/app/api/routes/training.py` | Semplificare, spostare logica |
| `backend/app/services/training_service.py` | Refactor per separazione engine |
| `backend/app/services/nlp_service.py` | Hook per pattern preview |

## Nuovi File da Creare

| File | Descrizione |
|------|-------------|
| `frontend/src/components/nlp-training/types.ts` | TypeScript interfaces |
| `frontend/src/components/nlp-training/hooks/*.ts` | Custom hooks (5 file) |
| `frontend/src/components/nlp-training/*.tsx` | Componenti UI (7 file) |
| `backend/app/api/routes/training_spacy.py` | Routes spaCy |
| `backend/app/api/routes/training_bert.py` | Routes BERT |
| `backend/app/api/routes/training_patterns.py` | Routes pattern |
| `backend/app/services/pattern_service.py` | Service pattern |
| `backend/app/data/training/manual_patterns.json` | Storage pattern manuali |

---

## Stima Effort
- Fase 1 (Backend): 2-3 giorni
- Fase 2 (Hooks): 2 giorni
- Fase 3 (Components): 3-4 giorni
- Fase 4 (Integration): 2-3 giorni
- **Totale: 9-12 giorni**
