# Sistema Email - Documentazione Tecnica

Questo documento descrive il funzionamento del sistema di gestione email, inclusa l'eliminazione spam dal server e il rate limiting per prevenire blocchi IP.

## Indice

1. [Architettura Sistema Email](#architettura-sistema-email)
2. [Eliminazione Email dal Server](#eliminazione-email-dal-server)
3. [Rate Limiting](#rate-limiting)
4. [Configurazione Provider](#configurazione-provider)
5. [Troubleshooting](#troubleshooting)

---

## Architettura Sistema Email

### Flusso Ricezione Email

```
┌─────────────────────────────────────────────────────────────────────┐
│ EMAIL POLLING (email_polling.py)                                    │
│ - POP3 polling ogni 2 minuti                                        │
│ - Due account: normale + PEC                                        │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ SALVATAGGIO DATABASE                                                │
│ - Email salvata con account_type: 'normale' | 'pec'                 │
│ - Preservato message_id per riferimento server                      │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ CLASSIFICAZIONE                                                     │
│ - Automatica con ML/LLM                                             │
│ - Possibile marcatura come SPAM                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Account Email Configurati

| Account | Tipo | Server POP3 | Server IMAP | Uso |
|---------|------|-------------|-------------|-----|
| info@snals.it | Normale | mail.truemail.it | mail.truemail.it | Email ordinarie |
| pec@snals.legalmail.it | PEC | pop3s.pec.aruba.it | imaps.pec.aruba.it | Email certificate |

---

## Eliminazione Email dal Server

### Overview

Il sistema permette di eliminare email classificate come spam non solo dal database locale, ma anche dal server email originale.

File: `backend/app/services/email_deletion.py`

### Flusso Eliminazione

```
┌─────────────────────────────────────────────────────────────────────┐
│ 1. RICHIESTA ELIMINAZIONE                                           │
│    API: DELETE /api/emails/{id}?from_server=true                    │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 2. DETERMINA ACCOUNT                                                │
│    - Legge email.account_type ('normale' | 'pec')                   │
│    - Seleziona credenziali corrispondenti                           │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 3. DERIVA SERVER IMAP DA POP3                                       │
│    _derive_imap_from_pop3():                                        │
│    - mail.truemail.it → mail.truemail.it (stesso server!)           │
│    - pop3s.pec.aruba.it → imaps.pec.aruba.it                        │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 4. CONNESSIONE IMAP SSL                                             │
│    - IMAP4_SSL su porta 993                                         │
│    - Login con stesse credenziali POP3                              │
│    - Seleziona INBOX                                                │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 5. RICERCA EMAIL                                                    │
│    - Cerca per Message-ID header                                    │
│    - Criterio: HEADER Message-ID "xxx"                              │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
              ┌────────────────┴────────────────┐
              │                                 │
          TROVATA                          NON TROVATA
              │                                 │
              ▼                                 ▼
┌─────────────────────────┐      ┌─────────────────────────────────────┐
│ 6a. ELIMINA             │      │ 6b. WARNING                         │
│ - Flag \Deleted         │      │ - Email non presente sul server     │
│ - EXPUNGE               │      │ - Probabilmente già eliminata       │
└─────────────────────────┘      └─────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 7. SOFT DELETE DATABASE                                             │
│    - is_deleted = true                                              │
│    - Storico preservato per audit                                   │
└─────────────────────────────────────────────────────────────────────┘
```

### Mappatura Server IMAP

La funzione `_derive_imap_from_pop3()` gestisce la derivazione del server IMAP:

```python
def _derive_imap_from_pop3(self, pop_host: str) -> str:
    # Mappatura specifica per provider noti
    imap_mappings = {
        'pop3s.pec.aruba.it': 'imaps.pec.aruba.it',
        'pop.pec.aruba.it': 'imap.pec.aruba.it',
        'mail.truemail.it': 'mail.truemail.it',  # IMPORTANTE: stesso server!
    }

    if host_lower in imap_mappings:
        return imap_mappings[host_lower]

    # Derivazione generica per altri provider
    if host_lower.startswith('pop3s.'):
        return pop_host.replace('pop3s.', 'imaps.', 1)
    elif host_lower.startswith('pop3.'):
        return pop_host.replace('pop3.', 'imap.', 1)
    # ...
```

### Nota Importante su TrueMail

TrueMail (provider email usato per account normale) utilizza lo **stesso server** per POP3 e IMAP:
- POP3: `mail.truemail.it:995`
- IMAP: `mail.truemail.it:993`

**NON** esiste `imap.truemail.it` - il tentativo di connessione fallisce con DNS NXDOMAIN.

### Esempio Codice Eliminazione

```python
from app.services.email_deletion import get_deletion_service

# Ottieni servizio
deletion_service = get_deletion_service(db)

# Elimina singola email
success = deletion_service.delete_from_server(email)

# Elimina multiple email
results = deletion_service.delete_multiple_from_server(email_list)
# results = {'total': 10, 'success': 8, 'failed': 2, 'errors': [...]}
```

---

## Rate Limiting

### Overview

Il rate limiter previene il blocco dell'IP da parte dei provider email limitando la frequenza di invio.

File: `backend/app/services/email_rate_limiter.py`

### Limiti Default

| Parametro | Valore | Descrizione |
|-----------|--------|-------------|
| `max_emails_per_hour` | 30 | Max email inviate per ora |
| `max_emails_per_minute` | 5 | Max email per minuto |
| `min_delay_seconds` | 10 | Delay minimo tra invii |
| `burst_delay_seconds` | 60 | Pausa dopo burst |
| `burst_threshold` | 3 | Email consecutive prima di pausa |

### Singleton Pattern

Il rate limiter usa il pattern Singleton per condividere lo stato tra tutti i thread:

```python
class EmailRateLimiter:
    _instance = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
```

### Utilizzo

```python
from app.services.email_rate_limiter import get_email_rate_limiter

rate_limiter = get_email_rate_limiter()

# Prima di inviare, attendi se necessario
wait_info = rate_limiter.wait_if_needed()
# wait_info = {'waited': True, 'wait_seconds': 10, 'reason': 'min_delay'}

# Invia email...

# Dopo invio, registra
rate_limiter.record_send(success=True)

# Verifica stato
status = rate_limiter.get_status()
# status = {
#     'emails_last_hour': 5,
#     'emails_last_minute': 2,
#     'consecutive_sends': 2,
#     'can_send': True
# }
```

### Logica Wait

```
┌─────────────────────────────────────────────────────────────────────┐
│ wait_if_needed()                                                    │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 1. CHECK DELAY MINIMO                                               │
│    Se elapsed < min_delay_seconds → sleep(remaining)                │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 2. CHECK LIMITE ORARIO                                              │
│    Se emails_last_hour >= max → sleep fino a scadenza più vecchia   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 3. CHECK LIMITE MINUTO                                              │
│    Se emails_last_minute >= max → sleep(60s)                        │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 4. CHECK BURST                                                      │
│    Se consecutive_sends >= threshold → sleep(burst_delay)           │
└─────────────────────────────────────────────────────────────────────┘
```

### Configurazione Runtime

```python
rate_limiter.configure(
    max_per_hour=50,      # Aumenta limite orario
    max_per_minute=10,    # Aumenta limite per minuto
    min_delay=5,          # Riduci delay minimo
    burst_delay=30,       # Riduci pausa burst
    burst_threshold=5     # Aumenta soglia burst
)
```

---

## Configurazione Provider

### TrueMail (Email Normale)

```env
EMAIL_NORMAL_POP3_HOST=mail.truemail.it
EMAIL_NORMAL_POP3_PORT=995
EMAIL_NORMAL_POP3_USER=info@snals.it
EMAIL_NORMAL_POP3_PASSWORD=xxx

# IMAP usa stesso server!
# Non configurare IMAP separatamente, viene derivato automaticamente
```

### Aruba PEC

```env
EMAIL_PEC_POP3_HOST=pop3s.pec.aruba.it
EMAIL_PEC_POP3_PORT=995
EMAIL_PEC_POP3_USER=xxx@pec.xxx.it
EMAIL_PEC_POP3_PASSWORD=xxx

# IMAP derivato automaticamente: imaps.pec.aruba.it
```

---

## Troubleshooting

### Problema: Email non eliminate dal server

**Sintomi:** Email marcate come spam nel database ma ancora presenti sul server

**Cause possibili:**
1. Message-ID non presente nell'email
2. Server IMAP non derivato correttamente
3. Credenziali non valide

**Soluzione:**
```python
# Verifica message_id
email = db.query(Email).get(id)
print(f"Message-ID: {email.message_id}")

# Test connessione IMAP manuale
from imaplib import IMAP4_SSL
mail = IMAP4_SSL('mail.truemail.it', 993)
mail.login('user', 'pass')
mail.select('INBOX')
```

### Problema: DNS NXDOMAIN per server IMAP

**Sintomi:** `socket.gaierror: [Errno -2] Name or service not known`

**Causa:** Server IMAP derivato erroneamente (es. `imap.truemail.it` non esiste)

**Soluzione:** Aggiornare mappatura in `_derive_imap_from_pop3()`:
```python
imap_mappings = {
    'mail.truemail.it': 'mail.truemail.it',  # Stesso server!
}
```

### Problema: Rate limit troppo restrittivo

**Sintomi:** Email in coda troppo a lungo

**Soluzione:** Aumentare limiti:
```python
rate_limiter = get_email_rate_limiter()
rate_limiter.configure(
    max_per_hour=50,
    max_per_minute=10,
    min_delay=5
)
```

### Problema: IP bloccato dal provider

**Sintomi:** Errore connessione SMTP, timeout

**Soluzione:**
1. Ridurre limiti rate limiting
2. Attendere sblocco (solitamente 24h)
3. Contattare provider se persistente

### Log Diagnostici

I servizi producono log dettagliati:

```
📧 Connessione a mail.truemail.it:993 per eliminare email 243 (account: normale)
✅ Login IMAP riuscito come info@snals.it
🔍 Ricerca email con Message-ID: xxx@truemail.it
🗑️ Email 1234 marcata per eliminazione
✅ 1 email eliminate dal server per email 243

⏳ Rate limit: attendo 10.0s (delay minimo)
📧 Email registrata: 5/ora, 2 consecutive
```

---

## File di Riferimento

| File | Descrizione |
|------|-------------|
| `backend/app/services/email_deletion.py` | Servizio eliminazione email |
| `backend/app/services/email_rate_limiter.py` | Rate limiter singleton |
| `backend/app/services/email_polling.py` | Polling POP3 |
| `backend/app/services/email_sender.py` | Invio email SMTP |
| `backend/app/api/routes/emails.py` | API endpoints email |

---

**Ultimo aggiornamento:** 2025-11-30
**Versione:** 1.4.0
