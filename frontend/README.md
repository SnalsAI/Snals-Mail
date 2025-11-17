# SNALS Email Agent - Frontend

Interfaccia web moderna per il sistema di gestione email SNALS.

## Stack Tecnologico

- **React 18** - UI Library
- **TypeScript** - Type Safety
- **Vite** - Build Tool & Dev Server
- **TailwindCSS** - Utility-first CSS
- **React Router** - Client-side routing
- **React Query** - Server state management
- **Axios** - HTTP Client
- **Recharts** - Data visualization
- **Lucide React** - Icon library
- **date-fns** - Date utilities
- **React Hot Toast** - Notifications

## Funzionalità

### 📊 Dashboard
- Card statistiche (Totali, Oggi, Da Leggere, Azioni Pending)
- Grafico distribuzione categorie (Pie chart)
- Grafico email per account (Bar chart)
- Lista email recenti

### 📧 Gestione Email
- Lista email con filtri (categoria, stato, ricerca fulltext)
- Dettaglio email completo
- Gestione categoria con aggiornamento
- Visualizzazione allegati
- Gestione revisioni
- Badge stati e priorità

### ⚙️ Azioni
- Visualizzazione azioni generate automaticamente
- Esecuzione manuale azioni pending
- Stati con icone colorate
- Dettagli parametri per tipo azione
- Eliminazione azioni

### 🎯 Regole
- Lista regole con priorità
- Attivazione/Disattivazione toggle
- Visualizzazione condizioni (AND/OR logic)
- Visualizzazione azioni associate
- Statistiche utilizzo
- Eliminazione regole

### 📅 Calendario
- Eventi raggruppati per data
- Informazioni complete (luogo, partecipanti, scuola)
- Integrazione Google Calendar
- Formato italiano date

## Setup Locale

### Prerequisiti
- Node.js 18+
- npm o yarn

### Installazione

```bash
cd frontend
npm install
```

### Variabili Ambiente

Crea un file `.env` nella directory `frontend/`:

```env
VITE_API_URL=http://localhost:8001
```

### Sviluppo

```bash
npm run dev
```

L'applicazione sarà disponibile su http://localhost:3001

### Build Produzione

```bash
npm run build
```

I file ottimizzati saranno generati in `dist/`.

### Lint

```bash
npm run lint
```

## Setup con Docker

### Build

```bash
docker-compose build frontend
```

### Avvio

```bash
docker-compose up -d frontend
```

### Logs

```bash
docker-compose logs -f frontend
```

## Struttura Progetto

```
frontend/
├── public/              # File statici
├── src/
│   ├── components/      # Componenti riutilizzabili
│   │   └── Layout.tsx   # Layout principale con sidebar
│   ├── pages/           # Pagine route
│   │   ├── Dashboard.tsx
│   │   ├── Emails.tsx
│   │   ├── EmailDetail.tsx
│   │   ├── Actions.tsx
│   │   ├── Rules.tsx
│   │   └── Calendar.tsx
│   ├── lib/             # Utilities
│   │   └── api.ts       # API client axios
│   ├── types/           # TypeScript types
│   │   └── index.ts     # Type definitions
│   ├── App.tsx          # Router setup
│   ├── main.tsx         # Entry point
│   └── index.css        # Global styles
├── Dockerfile           # Docker image
├── package.json         # Dependencies
├── vite.config.ts       # Vite configuration
├── tailwind.config.js   # Tailwind configuration
└── tsconfig.json        # TypeScript configuration
```

## API Endpoints Utilizzati

Il frontend comunica con il backend FastAPI tramite questi endpoint:

### Email
- `GET /emails/` - Lista email (con filtri)
- `GET /emails/{id}` - Dettaglio email
- `GET /emails/stats` - Statistiche
- `PUT /emails/{id}/categoria` - Aggiorna categoria
- `PUT /emails/{id}/revisiona` - Segna come revisionata
- `DELETE /emails/{id}` - Elimina email

### Azioni
- `GET /azioni/` - Lista azioni
- `GET /azioni/{id}` - Dettaglio azione
- `POST /azioni/` - Crea azione
- `POST /azioni/{id}/execute` - Esegui azione
- `DELETE /azioni/{id}` - Elimina azione

### Regole
- `GET /regole/` - Lista regole
- `GET /regole/{id}` - Dettaglio regola
- `POST /regole/` - Crea regola
- `PUT /regole/{id}` - Aggiorna regola
- `PUT /regole/{id}/toggle` - Attiva/Disattiva
- `DELETE /regole/{id}` - Elimina regola
- `POST /regole/{id}/test` - Testa regola

### Calendario
- `GET /calendario/` - Lista eventi
- `GET /calendario/{id}` - Dettaglio evento
- `POST /calendario/` - Crea evento
- `PUT /calendario/{id}` - Aggiorna evento
- `DELETE /calendario/{id}` - Elimina evento
- `POST /calendario/{id}/sync-google` - Sincronizza con Google

## Personalizzazione

### Colori

I colori principali si configurano in `tailwind.config.js`:

```javascript
colors: {
  primary: {
    50: '#f0f9ff',
    // ...
    900: '#0c4a6e',
  },
}
```

### Componenti Stile

I componenti utility sono definiti in `src/index.css`:
- `.btn`, `.btn-primary`, `.btn-secondary`, `.btn-danger`
- `.card`
- `.input`, `.label`
- `.badge`, `.badge-primary`, `.badge-success`, etc.

## Troubleshooting

### Frontend non si connette al backend

Verifica che:
1. Il backend sia avviato su http://localhost:8001
2. La variabile `VITE_API_URL` sia corretta nel file `.env`
3. Non ci siano problemi CORS (il backend FastAPI ha CORS abilitato)

### Errori di build

```bash
# Pulisci node_modules e reinstalla
rm -rf node_modules package-lock.json
npm install
```

### Hot reload non funziona in Docker

Assicurati che il volume sia montato correttamente in `docker-compose.yml`:

```yaml
volumes:
  - ./frontend:/app
  - /app/node_modules  # Importante: evita di sovrascrivere node_modules
```

## Sviluppi Futuri

- [ ] Rule Builder visuale interattivo
- [ ] Editor WYSIWYG per bozze email
- [ ] Drag & drop per priorità regole
- [ ] Filtri avanzati salvabili
- [ ] Notifiche real-time (WebSocket)
- [ ] Dark mode
- [ ] Export dati (CSV, PDF)
- [ ] Multi-lingua (i18n)
- [ ] Tests (Vitest, React Testing Library)

## Licenza

[Specificare licenza]
