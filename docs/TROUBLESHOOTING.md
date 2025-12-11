# Troubleshooting - SNALS Email Agent

Guida per la risoluzione dei problemi comuni.

## Indice

1. [Email](#email)
2. [Calendario](#calendario)
3. [LLM / AI](#llm--ai)
4. [Database](#database)
5. [Docker](#docker)
6. [Frontend](#frontend)

---

## Email

### Email non scaricate

**Sintomi:** Nessuna nuova email nel sistema nonostante la casella sia piena

**Diagnosi:**
```bash
# Verifica polling attivo
docker-compose logs backend | grep -i "poll" | tail -20

# Verifica configurazione
docker-compose exec backend cat /app/.env | grep EMAIL
```

**Cause comuni:**
1. Credenziali POP3 errate
2. Server POP3 non raggiungibile
3. Polling task non in esecuzione

**Soluzione:**
```bash
# Riavvia worker
docker-compose restart backend

# Test manuale POP3
docker-compose exec backend python -c "
from app.services.email_polling import poll_emails
poll_emails()
"
```

### Email spam non eliminate dal server

**Sintomi:** Email marcate spam nel DB ma ancora sul server

**Diagnosi:**
```bash
docker-compose logs backend | grep -i "imap" | tail -20
```

**Cause comuni:**
1. Server IMAP derivato erroneamente (es. `imap.truemail.it` non esiste)
2. Credenziali IMAP diverse da POP3
3. Message-ID non presente

**Soluzione:**
```python
# Verifica mapping in email_deletion.py
# TrueMail: mail.truemail.it (stesso per POP3 e IMAP!)
# Aruba PEC: pop3s.pec.aruba.it � imaps.pec.aruba.it
```

### Rate limiting troppo aggressivo

**Sintomi:** Email in coda per troppo tempo

**Diagnosi:**
```bash
curl http://localhost:8000/api/rate-limiter/status
```

**Soluzione:**
```python
# Modifica limiti in email_rate_limiter.py
rate_limiter.configure(
    max_per_hour=50,      # Default: 30
    max_per_minute=10,    # Default: 5
    min_delay=5           # Default: 10
)
```

---

## Calendario

### Eventi non creati

**Sintomi:** Email di convocazione processata ma nessun evento

**Diagnosi:**
```bash
# Verifica azione
curl "http://localhost:8000/api/azioni/?email_id={email_id}"

# Verifica log estrazione
docker-compose logs backend | grep -i "SmartConvocazione" | tail -20
```

**Cause comuni:**
1. Sottocategoria non "convocazione"
2. Completezza dati < 40%
3. Sanity check fallito (data passata, ora invalida)

**Soluzione:**
```sql
-- Verifica email
SELECT id, categoria, sottocategoria, oggetto
FROM emails WHERE id = {email_id};

-- Verifica azione
SELECT * FROM azioni WHERE email_id = {email_id};
```

### Stato evento inconsistente

**Sintomi:** Titolo dice [RINVIATO] ma stato è "confermato"

**Diagnosi:**
```bash
curl http://localhost:8001/api/calendario/report/anomalie
```

**Soluzione Automatica (Consigliata):**
```bash
# Risolve tutte le anomalie automaticamente
curl -X POST http://localhost:8001/api/calendario/report/anomalie/risolvi-auto

# Response:
# {
#   "success": true,
#   "risolte": {
#     "eventi_completati": 8,
#     "stati_corretti": 2,
#     "google_aggiornati": 10
#   }
# }
```

**Soluzione Manuale (Singolo Evento):**
```bash
# Cambia stato singolo evento
curl -X DELETE "http://localhost:8001/api/calendario/report/anomalie/{evento_id}?azione=rinviato"
```

**Soluzione SQL (se necessario):**
```sql
-- Fix manuale
UPDATE eventi_calendario
SET stato = 'rinviato'
WHERE id = {evento_id}
  AND titolo LIKE '%[RINVIATO]%'
  AND titolo NOT LIKE '%[POST RINVIO]%';
```

### Eventi passati ancora confermati

**Sintomi:** Eventi con data passata ancora in stato "confermato"

**Diagnosi:**
```bash
curl http://localhost:8001/api/calendario/report/anomalie | jq '.anomalie[] | select(.tipo == "evento_passato_confermato")'
```

**Soluzione Automatica:**
```bash
# Marca tutti gli eventi passati come completati
curl -X POST http://localhost:8001/api/calendario/report/anomalie/risolvi-auto
```

### Eventi da email non-convocazione

**Sintomi:** Evento creato da email con sottocategoria errata (es. "Risposta personale")

**Diagnosi:**
```bash
curl http://localhost:8001/api/calendario/report/anomalie | jq '.anomalie[] | select(.tipo == "sottocategoria_errata")'
```

**Soluzione:**
```bash
# Elimina evento errato
curl -X DELETE http://localhost:8001/api/calendario/{evento_id}

# L'evento viene eliminato sia dal database locale che da Google Calendar
```

### Evento duplicato dopo rinvio

**Sintomi:** Due eventi per la stessa convocazione

**Causa:** `_find_existing_event()` non ha trovato l'originale

**Diagnosi:**
```sql
SELECT * FROM eventi_calendario
WHERE scuola = '{codice_meccanografico}'
  AND data_inizio BETWEEN '{data-7}' AND '{data+7}';
```

**Soluzione:**
```sql
-- Elimina duplicato
DELETE FROM eventi_calendario WHERE id = {duplicato_id};

-- Aggiorna originale se necessario
UPDATE eventi_calendario
SET titolo = '[POST RINVIO] ...',
    data_inizio = '2025-12-15 10:00:00',
    data_inizio_originale = data_inizio
WHERE id = {originale_id};
```

### Google Calendar non sincronizzato

**Sintomi:** Eventi nel sistema ma non su Google

**Diagnosi:**
```sql
SELECT id, titolo, google_event_id, sincronizzato
FROM eventi_calendario
WHERE sincronizzato = false;
```

**Soluzione:**
```bash
# Forza sync
curl -X POST http://localhost:8000/api/calendario/{id}/sync-google

# Verifica token Google
curl http://localhost:8000/api/google/status
```

---

## LLM / AI

### Ollama non risponde

**Sintomi:** Timeout su chiamate LLM, errori 500

**Diagnosi:**
```bash
# Verifica Ollama attivo
curl http://localhost:11434/api/tags

# Verifica modelli
docker-compose exec ollama ollama list
```

**Soluzione:**
```bash
# Riavvia Ollama
docker-compose restart ollama

# Scarica modello se mancante
docker-compose exec ollama ollama pull llama3.2:3b
```

### Coda LLM bloccata

**Sintomi:** Richieste LLM in stato IN_ELABORAZIONE da troppo tempo

**Diagnosi:**
```sql
SELECT * FROM richieste_llm
WHERE stato = 'IN_ELABORAZIONE'
ORDER BY created_at DESC;
```

**Soluzione:**
```sql
-- Reset richieste bloccate
UPDATE richieste_llm
SET stato = 'IN_CODA'
WHERE stato = 'IN_ELABORAZIONE'
  AND updated_at < NOW() - INTERVAL '10 minutes';
```

### Classificazione errata

**Sintomi:** Email categorizzate in modo sbagliato

**Diagnosi:**
```bash
# Verifica pattern
docker-compose logs backend | grep -i "classificazione" | tail -20
```

**Soluzione:**
```bash
# Riclassifica email
curl -X POST http://localhost:8000/api/emails/{id}/classify
```

---

## Database

### Connessione rifiutata

**Sintomi:** `connection refused` su PostgreSQL

**Diagnosi:**
```bash
docker-compose ps db
docker-compose logs db | tail -20
```

**Soluzione:**
```bash
# Riavvia database
docker-compose restart db

# Verifica spazio disco
df -h
```

### Migration fallita

**Sintomi:** Errore Alembic all'avvio

**Diagnosi:**
```bash
docker-compose exec backend alembic current
docker-compose exec backend alembic history
```

**Soluzione:**
```bash
# Applica migrations
docker-compose exec backend alembic upgrade head

# Se corrotta, reset
docker-compose exec backend alembic stamp head
```

---

## Docker

### Container non parte

**Sintomi:** Container in restart loop

**Diagnosi:**
```bash
docker-compose logs {service} | tail -50
docker-compose ps
```

**Soluzione:**
```bash
# Ricostruisci container
docker-compose build {service}
docker-compose up -d {service}
```

### Spazio disco esaurito

**Sintomi:** Errori di scrittura, container che crashano

**Diagnosi:**
```bash
df -h
docker system df
```

**Soluzione:**
```bash
# Pulizia Docker
docker system prune -a --volumes

# Rimuovi log vecchi
truncate -s 0 /var/lib/docker/containers/*/*-json.log
```

---

## Frontend

### Pagina bianca

**Sintomi:** Frontend non carica

**Diagnosi:**
```bash
# Verifica build
docker-compose logs frontend | tail -20

# Verifica nginx
curl -I http://localhost:80
```

**Soluzione:**
```bash
# Ricostruisci frontend
docker-compose build frontend
docker-compose up -d frontend
```

### API non raggiungibile

**Sintomi:** Errori CORS o 502

**Diagnosi:**
```bash
# Test diretto backend
curl http://localhost:8000/api/health

# Verifica proxy nginx
docker-compose logs nginx | tail -20
```

**Soluzione:**
```bash
# Verifica configurazione nginx
docker-compose exec nginx cat /etc/nginx/conf.d/default.conf
```

---

## Comandi Utili

### Logs

```bash
# Tutti i servizi
docker-compose logs -f

# Solo backend
docker-compose logs -f backend

# Filtra per errori
docker-compose logs backend 2>&1 | grep -i "error\|exception"
```

### Database

```bash
# Shell PostgreSQL
docker-compose exec db psql -U snals_user -d snals

# Backup
docker-compose exec db pg_dump -U snals_user snals > backup.sql

# Restore
docker-compose exec -T db psql -U snals_user snals < backup.sql
```

### Restart pulito

```bash
# Stop tutto
docker-compose down

# Rimuovi volumi (ATTENZIONE: cancella dati!)
docker-compose down -v

# Ricostruisci e avvia
docker-compose build
docker-compose up -d
```

---

**Ultimo aggiornamento:** 2025-12-11
