# Configurazione Google API (OPZIONALE)

⚠️ **NOTA IMPORTANTE**: L'integrazione Google è **completamente opzionale**.

Il sistema funziona perfettamente anche **senza** Google Calendar/Drive:
- ✅ Tutte le altre azioni continuano a funzionare normalmente
- ✅ Le azioni Google vengono saltate automaticamente con messaggio informativo
- ✅ Puoi configurare Google in seguito quando necessario

## Cosa succede senza Google

Se non configuri le credenziali Google:
- **EVENTO_CALENDARIO**: L'azione viene marcata come "completata" con messaggio che l'evento può essere creato manualmente
- **UPLOAD_DRIVE**: L'azione viene marcata come "completata" con messaggio che gli allegati rimangono nell'email

## Come Ottenere le Credenziali Google (se vuoi usarlo)

### Opzione 1: Service Account (Consigliato per Produzione)

Un **Service Account** è ideale per applicazioni server che girano in background senza interazione utente.

#### Passaggi:

1. **Vai alla Google Cloud Console**:
   - https://console.cloud.google.com/

2. **Crea un Progetto** (se non ne hai già uno):
   - Clicca su "Seleziona un progetto" → "Nuovo progetto"
   - Nome: "SNALS Email Agent"

3. **Abilita le API necessarie**:
   - Vai a "API e servizi" → "Libreria"
   - Cerca e abilita:
     - **Google Calendar API**
     - **Google Drive API**

4. **Crea un Service Account**:
   - Vai a "API e servizi" → "Credenziali"
   - Clicca "+ CREA CREDENZIALI" → "Account di servizio"
   - Nome: "snals-email-agent"
   - Clicca "CREA E CONTINUA"
   - Ruolo: "Editor" (o più specifico se preferisci)
   - Clicca "FINE"

5. **Scarica la Chiave JSON**:
   - Nella lista degli account di servizio, clicca sui tre puntini → "Gestisci chiavi"
   - "AGGIUNGI CHIAVE" → "Crea nuova chiave"
   - Tipo: JSON
   - Clicca "CREA"
   - Il file JSON verrà scaricato automaticamente

6. **Copia il file in questo progetto**:
   ```bash
   # Rinomina il file scaricato e copialo qui
   cp ~/Download/nome-progetto-abc123.json /path/to/Snals-Mail/backend/config/google_credentials.json
   ```

7. **Condividi Calendario e Drive con il Service Account**:
   - **Calendario**:
     - Apri Google Calendar
     - Clicca su "Impostazioni e condivisione" del calendario che vuoi usare
     - In "Condividi con persone specifiche" aggiungi l'email del service account (es: `snals-email-agent@tuo-progetto.iam.gserviceaccount.com`)
     - Assegna permesso "Apporta modifiche agli eventi"

   - **Drive**:
     - Apri Google Drive
     - Condividi le cartelle UST e SNALS con l'email del service account
     - Assegna permesso "Editor"

### Opzione 2: OAuth2 (Solo per Test Manuali)

Per OAuth2 devi:
1. Scaricare il file `credentials.json` dalla console (OAuth Client ID)
2. Eseguire manualmente l'autenticazione la prima volta
3. Il token verrà salvato automaticamente

**Nota**: OAuth2 non è consigliato per produzione perché richiede intervento manuale.

## Verifica Configurazione

1. Assicurati che il file sia in:
   ```
   /path/to/Snals-Mail/backend/config/google_credentials.json
   ```

2. Aggiorna la configurazione nel file `.env`:
   ```env
   GOOGLE_CREDENTIALS_FILE=config/google_credentials.json
   GOOGLE_CALENDAR_ID=primary
   GOOGLE_DRIVE_FOLDER_UST=<ID_FOLDER>
   GOOGLE_DRIVE_FOLDER_SNALS=<ID_FOLDER>
   ```

3. Riavvia i servizi:
   ```bash
   docker-compose restart backend celery-worker celery-beat
   ```

4. Testa la connessione dalla pagina Settings del frontend:
   - Clicca su "Test Google Calendar"
   - Clicca su "Test Google Drive"

## Risoluzione Problemi

### Errore: "File credentials non trovato"
- Verifica che il file esista in `backend/config/google_credentials.json`
- Controlla che il percorso nel `.env` sia corretto

### Errore: "Autenticazione fallita"
- Verifica che il file JSON sia valido (deve avere `"type": "service_account"`)
- Controlla che le API siano abilitate nella Google Cloud Console
- Verifica che il service account abbia i permessi corretti

### Errore: "Access denied" quando crea eventi/file
- Assicurati di aver condiviso il calendario/drive con l'email del service account
- Verifica i permessi (deve essere almeno "Editor")

## Sicurezza

⚠️ **IMPORTANTE**: Il file `google_credentials.json` contiene chiavi private. NON committarlo in Git!

Il file è già in `.gitignore`, ma verifica sempre prima di fare commit:
```bash
git status
```

Se per errore hai committato il file:
1. Revoca immediatamente la chiave dalla Google Cloud Console
2. Genera una nuova chiave
3. Rimuovi il file dalla cronologia Git
