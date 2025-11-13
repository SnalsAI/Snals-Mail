# Snals-Mail

**Analizzatore Email dello SNALS** - Sistema completo per la gestione, sincronizzazione e analisi automatica delle email.

## 🚀 Caratteristiche

- **Dashboard Interattiva**: Visualizzazione completa delle statistiche email
- **Gestione Email**: Lettura, ricerca, categorizzazione e archiviazione
- **Analisi Automatica**: Sentiment analysis, rilevamento spam, categorizzazione e estrazione keywords
- **Sincronizzazione IMAP**: Import automatico da server email via IMAP
- **Autenticazione Sicura**: Sistema di login/registrazione con JWT
- **Multi-utente**: Supporto per più utenti con configurazioni email separate
- **Responsive Design**: Interfaccia moderna con Material-UI

## 🏗️ Architettura

Il progetto è composto da 3 servizi Docker:

1. **Frontend** (React + Vite + Material-UI) - Porta 3000
2. **Backend** (Node.js + Express) - Porta 5000
3. **MongoDB** - Porta 27017

## 📋 Prerequisiti

- Docker (versione 20.10+)
- Docker Compose (versione 2.0+)
- Make (opzionale, per i comandi facilitati)

## 🔧 Installazione e Setup

### 1. Clona il repository

```bash
git clone <repository-url>
cd Snals-Mail
```

### 2. Configura le variabili d'ambiente

```bash
# Copia il file di esempio
cp .env.example .env

# Oppure usa make
make install
```

Modifica il file `.env` con le tue configurazioni:

```env
# Modifica almeno questi valori in produzione
MONGO_ROOT_PASSWORD=la-tua-password-sicura
JWT_SECRET=il-tuo-jwt-secret-molto-lungo-e-sicuro
```

### 3. Avvia i servizi

#### Usando Make (raccomandato)

```bash
# Build e avvio
make build
make up

# Verifica lo stato
make status

# Visualizza i log
make logs
```

#### Usando Docker Compose direttamente

```bash
# Build delle immagini
docker-compose build

# Avvio dei servizi
docker-compose up -d

# Visualizza i log
docker-compose logs -f
```

### 4. Accedi all'applicazione

Apri il browser e vai a:

```
http://localhost:3000
```

L'API backend è disponibile su:

```
http://localhost:5000/api
```

## 📖 Utilizzo

### Prima Configurazione

1. **Registra un account**: Clicca su "Registrati" nella pagina di login
2. **Configura IMAP**: Vai in Impostazioni e inserisci:
   - Host IMAP (es. `imap.gmail.com`)
   - Porta (solitamente `993`)
   - Username/Email
   - Password (per Gmail usa una App Password)
3. **Sincronizza**: Clicca su "Sincronizza Ora"

### Funzionalità Principali

#### Dashboard
- Visualizza statistiche totali email
- Conta email non lette, lette, spam
- Quick access alle varie categorie

#### Gestione Email
- Lista completa delle email con ricerca
- Filtri per stato (lette/non lette)
- Visualizzazione dettaglio email
- Azioni: Analizza, Archivia, Elimina

#### Analisi Email
- Analisi automatica del sentiment
- Calcolo spam score
- Categorizzazione automatica
- Estrazione keywords
- Determinazione priorità

## 🛠️ Comandi Make Disponibili

```bash
make help       # Mostra tutti i comandi disponibili
make build      # Build di tutti i container
make up         # Avvia tutti i servizi
make down       # Ferma tutti i servizi
make restart    # Riavvia tutti i servizi
make logs       # Mostra i log di tutti i servizi
make backend    # Mostra solo i log del backend
make frontend   # Mostra solo i log del frontend
make mongodb    # Mostra solo i log di MongoDB
make clean      # Rimuove container, volumi e immagini
make status     # Verifica lo stato dei container
```

## 🔌 API Endpoints

### Autenticazione

- `POST /api/auth/register` - Registrazione utente
- `POST /api/auth/login` - Login
- `GET /api/auth/me` - Profilo utente corrente
- `PUT /api/auth/email-config` - Aggiorna configurazione email

### Email

- `GET /api/emails` - Lista email (con paginazione, ricerca, filtri)
- `GET /api/emails/:id` - Dettaglio email
- `POST /api/emails/:id/analyze` - Analizza email
- `PATCH /api/emails/:id` - Aggiorna stato/folder
- `DELETE /api/emails/:id` - Elimina email
- `POST /api/emails/sync` - Sincronizza da IMAP

### Health Check

- `GET /api/health` - Verifica stato API

## 🗂️ Struttura del Progetto

```
Snals-Mail/
├── backend/                 # Backend Node.js/Express
│   ├── src/
│   │   ├── config/         # Configurazioni (database)
│   │   ├── controllers/    # Controller API
│   │   ├── models/         # Modelli MongoDB
│   │   ├── routes/         # Routes API
│   │   ├── utils/          # Utility (middleware auth)
│   │   └── server.js       # Entry point
│   ├── Dockerfile
│   └── package.json
│
├── frontend/               # Frontend React
│   ├── src/
│   │   ├── components/    # Componenti React
│   │   ├── pages/         # Pagine
│   │   ├── services/      # API client
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── Dockerfile
│   ├── nginx.conf         # Configurazione Nginx
│   ├── vite.config.js
│   └── package.json
│
├── docker-compose.yml     # Orchestrazione servizi
├── .env.example           # Template variabili d'ambiente
├── .gitignore
├── Makefile              # Comandi facilitati
└── README.md
```

## 🔐 Sicurezza

- **JWT Authentication**: Token sicuri per l'autenticazione
- **Password Hashing**: Bcrypt per l'hash delle password
- **Helmet.js**: Security headers per Express
- **CORS**: Configurazione CORS appropriata
- **Input Validation**: Validazione input con express-validator
- **Environment Variables**: Credenziali in variabili d'ambiente

## 🚧 Troubleshooting

### I container non si avviano

```bash
# Verifica i log
make logs

# Riavvia i servizi
make restart
```

### Errore di connessione al database

```bash
# Verifica che MongoDB sia healthy
docker-compose ps

# Riavvia solo MongoDB
docker-compose restart mongodb
```

### Errore IMAP durante la sincronizzazione

- Verifica le credenziali IMAP
- Per Gmail, usa una [App Password](https://support.google.com/accounts/answer/185833)
- Verifica che IMAP sia abilitato nel tuo provider email

### Pulire tutto e ricominciare

```bash
# Rimuove tutto (ATTENZIONE: cancella i dati!)
make clean

# Riavvia da zero
make build
make up
```

## 🧪 Testing

```bash
# Backend tests
docker-compose exec backend npm test

# Build production
docker-compose exec frontend npm run build
```

## 📝 Sviluppo

### Modalità Development

Per sviluppare con hot-reload:

```bash
# Frontend
cd frontend
npm install
npm run dev

# Backend
cd backend
npm install
npm run dev
```

### Accesso ai Container

```bash
# Backend shell
make backend-shell
# oppure
docker-compose exec backend sh

# Frontend shell
make frontend-shell

# MongoDB shell
make mongo-shell
# oppure
docker-compose exec mongodb mongosh -u admin -p admin123
```

## 📦 Deployment

Per il deployment in produzione:

1. Modifica `.env` con valori sicuri
2. Usa HTTPS con un reverse proxy (nginx, traefik)
3. Configura backup regolari del volume MongoDB
4. Monitora i log e le metriche

## 🤝 Contribuire

Contributi, issue e feature request sono benvenuti!

## 📄 Licenza

MIT

## 👥 Autori

Snals-Mail Team

---

**Made with ❤️ for SNALS**
