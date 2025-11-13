# SNALS Email Agent - Frontend

Frontend React + TypeScript + Vite per il sistema di automazione email SNALS.

## Tecnologie

- **React 18** - UI Library
- **TypeScript** - Type Safety
- **Vite** - Build Tool
- **TailwindCSS** - Styling
- **React Router** - Routing
- **TanStack Query** - Data Fetching
- **Recharts** - Grafici e visualizzazioni
- **Axios** - HTTP Client
- **React Hot Toast** - Notifiche
- **Lucide React** - Icone

## Struttura

```
frontend/
├── public/              # File statici
├── src/
│   ├── components/      # Componenti riutilizzabili
│   │   ├── Layout.tsx
│   │   ├── Sidebar.tsx
│   │   ├── PageHeader.tsx
│   │   ├── Badge.tsx
│   │   ├── LoadingSpinner.tsx
│   │   ├── EmptyState.tsx
│   │   └── StatCard.tsx
│   ├── pages/           # Pagine applicazione
│   │   ├── Dashboard.tsx        # Dashboard con statistiche
│   │   ├── Emails.tsx          # Lista email
│   │   ├── EmailDetail.tsx     # Dettaglio email
│   │   ├── Calendar.tsx        # Gestione calendario
│   │   ├── Rules.tsx           # Gestione regole
│   │   ├── Documents.tsx       # Gestione documenti RAG
│   │   ├── Actions.tsx         # Gestione azioni
│   │   └── Settings.tsx        # Impostazioni
│   ├── services/        # API Services
│   │   ├── emailService.ts
│   │   ├── actionService.ts
│   │   ├── ruleService.ts
│   │   ├── calendarService.ts
│   │   ├── documentService.ts
│   │   └── dashboardService.ts
│   ├── lib/            # Utilities
│   │   ├── api.ts      # Axios instance
│   │   └── utils.ts    # Helper functions
│   ├── types/          # TypeScript types
│   │   └── index.ts
│   ├── App.tsx         # App principale con routing
│   ├── main.tsx        # Entry point
│   └── index.css       # Stili globali
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
└── tailwind.config.js
```

## Funzionalità

### 1. Dashboard
- Statistiche real-time (email oggi, non lette, azioni pending)
- Grafici distribuzione categorie email
- Grafici distribuzione azioni
- Quick actions per navigazione rapida

### 2. Gestione Email
- Lista email con filtri avanzati
- Ricerca full-text
- Filtro per categoria, stato, tipo account
- Sincronizzazione POP3 (Normale e PEC)
- Dettaglio email completo
- Visualizzazione allegati
- Cambio stato email
- Gestione azioni associate

### 3. Calendario
- Visualizzazione eventi
- Creazione/modifica/eliminazione eventi
- Sincronizzazione Google Calendar
- Collegamento con email

### 4. Regole
- Visualizzazione regole automazione
- Attivazione/disattivazione regole
- Visualizzazione condizioni e azioni
- Ordinamento per priorità

### 5. Documenti RAG
- **Upload documenti** (PDF, DOCX, TXT, HTML)
- **Scelta tipo documento** (SNALS Centrale, USR/USP, Normativa, etc.)
- **Embedding automatico o manuale**
- **Gestione embedding** (abilita/disabilita per documento)
- **Statistiche RAG** (documenti totali, embeddati, chunks, query)
- **Filtri avanzati** per tipo, stato, embedding
- **Ricerca full-text**
- **Visualizzazione stato processing**

### 6. Azioni
- Visualizzazione azioni per stato (pending, completate, fallite)
- Esecuzione manuale azioni
- Visualizzazione errori
- Statistiche azioni

### 7. Impostazioni
- Configurazione account email (Normale e PEC)
- Configurazione LLM (Ollama/OpenAI)
- **Configurazione RAG**
  - Provider embedding
  - Modello embedding
  - Chunk size e overlap
  - Soglia similarità
  - Toggle RAG enable/disable
- Integrazione Google (Calendar, Drive)
- Database (PostgreSQL, Redis)

## Installazione

```bash
cd frontend
npm install
```

## Sviluppo

```bash
npm run dev
```

Apri [http://localhost:3001](http://localhost:3001)

Il proxy Vite inoltrerà le chiamate API a `http://localhost:8001`

## Build

```bash
npm run build
```

I file di produzione saranno in `dist/`

## Linting

```bash
npm run lint
```

## Integrazione RAG

Il frontend supporta completamente il sistema RAG:

1. **Upload Documenti**: Carica PDF, DOCX, TXT, HTML con scelta tipo
2. **Embedding Automatico**: Opzione per embeddare immediatamente dopo upload
3. **Gestione Embedding**: Abilita/disabilita embedding per ogni documento
4. **Filtri Avanzati**: Filtra per tipo documento e stato embedding
5. **Statistiche**: Visualizza metriche RAG (documenti, chunks, query)
6. **Integrazione API**: Chiamate complete alle API RAG del backend

## API Backend

Il frontend si connette al backend FastAPI su `http://localhost:8001`

Endpoints utilizzati:
- `/api/emails/` - Gestione email
- `/api/azioni/` - Gestione azioni
- `/api/regole/` - Gestione regole
- `/api/calendario/` - Gestione calendario
- `/api/documenti/` - **Gestione documenti RAG**
- `/api/documenti/upload` - **Upload documenti**
- `/api/documenti/{id}/embed` - **Embedding documenti**
- `/api/documenti/rag/query` - **Query RAG**
- `/api/documenti/rag/stats` - **Statistiche RAG**

## Variabili Ambiente

Non ci sono variabili d'ambiente nel frontend. La configurazione è gestita tramite:
- Proxy Vite per API (`vite.config.ts`)
- Settings page per configurazione runtime

## Note

- Il frontend è completamente tipizzato con TypeScript
- Utilizza React Query per caching e sincronizzazione
- Responsive design con TailwindCSS
- Componenti modulari e riutilizzabili
- Toast notifications per feedback utente
- Loading states e error handling
