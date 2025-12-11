# Riepilogo Categorie e Sottocategorie - SNALS Email Agent

**Data:** 2025-11-21
**Sistema:** SNALS Email Agent v0.1.0

---

## Panoramica

Il sistema di categorizzazione automatica utilizza **10 categorie principali** per classificare le email in arrivo. Ogni categoria ha:
- **Priorità** (0-10): determina l'importanza nella classificazione
- **Parole chiave**: termini che caratterizzano la categoria
- **Pattern mittenti/oggetto**: espressioni regolari per il riconoscimento automatico
- **Sottocategorie predefinite**: classificazioni più specifiche (generate automaticamente dal contenuto)

---

## 📋 Categorie Dettagliate

### 1. 💬 INFO GENERICHE
**Chiave:** `info_generiche`
**Priorità:** 1/10 (bassa)
**Descrizione:** Informazioni generali, richieste di informazioni

**Parole chiave:**
- info, informazioni, chiarimenti, domanda

**Pattern riconoscimento:**
- Oggetto: `richiesta.*info`, `info.*`

**Sottocategorie:** Nessuna predefinita (generate automaticamente)

---

### 2. 📅 RICHIESTA APPUNTAMENTO
**Chiave:** `richiesta_appuntamento`
**Priorità:** 5/10 (media)
**Descrizione:** Richieste di appuntamento da iscritti o potenziali iscritti

**Parole chiave:**
- appuntamento, incontrare, visita, disponibilità

**Pattern riconoscimento:**
- Oggetto: `appuntamento`, `incontro`

**Sottocategorie predefinite:**
- Prima consulenza
- Follow-up
- Urgente

---

### 3. 📋 RICHIESTA TESSERAMENTO
**Chiave:** `richiesta_tesseramento`
**Priorità:** 6/10 (medio-alta)
**Descrizione:** Richieste di iscrizione al sindacato

**Parole chiave:**
- tesseramento, iscrizione, iscriversi, modulo

**Pattern riconoscimento:**
- Oggetto: `tesseramento`, `iscrizione`

**Sottocategorie predefinite:**
- Nuovo iscritto
- Rinnovo
- Disdetta

---

### 4. 📣 CONVOCAZIONE SCUOLA
**Chiave:** `convocazione_scuola`
**Priorità:** 10/10 (MASSIMA)
**Descrizione:** Convocazioni a riunioni sindacali, assemblee, RSU da parte di scuole

**Parole chiave:**
- convocazione, riunione RSU, assemblea sindacale, tavolo di contrattazione, incontro OO.SS

**Pattern riconoscimento:**
- Mittente: scuole con codice meccanografico `[a-z]{4}\d{5}[a-z]?@(pec.)?istruzione.it`
- Oggetto: `convocazione`, `riunione.*RSU`, `assemblea`, `tavolo.*contrattazione`

**Sottocategorie predefinite:**
- Convocazione RSU
- Convocazione (generica)
- Assemblea sindacale
- Contrattazione
- Interpello

**Note:** Priorità massima perché sono comunicazioni urgenti che richiedono azione immediata.

---

### 5. 🏛️ COMUNICAZIONE UST/USR
**Chiave:** `comunicazione_ust_usr`
**Priorità:** 9/10 (molto alta)
**Descrizione:** Comunicazioni ufficiali da Uffici Scolastici Territoriali o Regionali

**Parole chiave:**
- graduatoria, GPS, convocazione, nomina, incarico, utilizzazione, assegnazione provvisoria

**Pattern riconoscimento:**
- Mittente: `uspta@`, `usprpu@`, `usp.ta@`, `usr.puglia@`, `aoouspta@`, `aoousr@`
- Oggetto: `GPS`, `graduatoria`, `convocazione.*supplenze`, `utilizzazioni`, `assegnazioni provvisorie`

**Sottocategorie predefinite:**
- GPS (Graduatorie Provinciali Supplenze)
- Convocazioni supplenze
- Utilizzazioni
- Assegnazioni provvisorie
- Graduatorie

**Note:** Include comunicazioni da UST Taranto e USR Puglia.

---

### 6. 🏫 COMUNICAZIONE SCUOLA
**Chiave:** `comunicazione_scuola`
**Priorità:** 7/10 (alta)
**Descrizione:** Comunicazioni da scuole (non convocazioni)

**Parole chiave:**
- invito sottoscrizione, contratto, pubblicazione, informativa, contrattazione integrativa

**Pattern riconoscimento:**
- Mittente: scuole con codice meccanografico `[a-z]{4}\d{5}[a-z]?@(pec.)?istruzione.it`
- Oggetto: `invito.*sottoscrizione`, `contratto`, `informativa`, `contrattazione.*integrativa`

**Sottocategorie predefinite:**
- Contrattazione Integrativa
- Contratto integrativo
- Informativa
- Circolare
- Comunicazione

**Note:** Si differenzia da "Convocazione Scuola" perché include comunicazioni informative anziché convocazioni a riunioni.

---

### 7. 🏢 COMUNICAZIONE SNALS CENTRALE
**Chiave:** `comunicazione_snals_centrale`
**Priorità:** 8/10 (alta)
**Descrizione:** Comunicazioni dalla sede centrale SNALS

**Parole chiave:**
- circolare, comunicazione, aggiornamento

**Pattern riconoscimento:**
- Mittente: `info@snals.it`

**Sottocategorie predefinite:**
- Circolare
- Comunicazione
- Aggiornamento normativo

**Note:** Include tutte le comunicazioni ufficiali dalla sede nazionale del sindacato.

---

### 8. 🚫 SPAM
**Chiave:** `spam`
**Priorità:** 0/10 (minima)
**Descrizione:** Email indesiderate, phishing, tentativi di truffa

**Parole chiave:**
- phishing, truffa, virus, malware, sospetto

**Pattern riconoscimento:**
- Oggetto: `phishing`, `virus`, `malware`

**Sottocategorie:** Nessuna predefinita

**Note:** Include email pericolose, tentativi di phishing e truffe. Può essere configurato per l'eliminazione automatica.

---

### 9. 📢 PUBBLICITÀ
**Chiave:** `pubblicita`
**Priorità:** 0/10 (minima)
**Descrizione:** Materiale promozionale, pubblicità commerciale

**Parole chiave:**
- pubblicità, offerta, sconto, vinci, premio, promozione

**Pattern riconoscimento:**
- Oggetto: `pubblicità`, `offerta.*speciale`, `sconto`, `promozione`

**Sottocategorie:** Nessuna predefinita

**Note:** Si differenzia da "Spam" perché include materiale promozionale legittimo (non pericoloso).

---

### 10. 📦 VARIE
**Chiave:** `varie`
**Priorità:** 2/10 (bassa)
**Descrizione:** Email che non rientrano in altre categorie specifiche

**Parole chiave:** Nessuna (categoria catch-all)

**Pattern riconoscimento:** Nessuno (categoria di default)

**Sottocategorie:** Nessuna predefinita (generate automaticamente)

**Note:** Categoria di fallback per email che non corrispondono ad altre categorie.

---

## 🔍 Funzionamento della Categorizzazione

### Processo Automatico
1. **Analisi Rule-Based** (prioritaria):
   - Verifica pattern mittenti
   - Verifica pattern oggetto/corpo
   - Calcola confidence score

2. **Analisi LLM** (fallback se confidence < 0.85):
   - Usa modello Ollama o OpenAI
   - Analizza contenuto completo
   - Genera categoria e confidence

3. **Estrazione Sottocategoria**:
   - Analisi pattern specifici nel testo
   - Generazione automatica basata su contenuto
   - Mapping su sottocategorie predefinite

### Priorità di Categorizzazione
Le categorie con priorità più alta vengono considerate prima:

1. **Convocazione Scuola** (10/10) - Massima priorità
2. **Comunicazione UST/USR** (9/10)
3. **Comunicazione SNALS Centrale** (8/10)
4. **Comunicazione Scuola** (7/10)
5. **Richiesta Tesseramento** (6/10)
6. **Richiesta Appuntamento** (5/10)
7. **Varie** (2/10)
8. **Info Generiche** (1/10)
9. **Spam/Pubblicità** (0/10) - Minima priorità

---

## 📊 Sottocategorie: Logica di Generazione

### Sottocategorie Predefinite
Definite nella configurazione come riferimento, ma il sistema può generarne altre.

### Sottocategorie Automatiche
Generate dal sistema in base a:
- Pattern regex specifici nel testo
- Analisi semantica del contenuto
- Informazioni estratte (es. nome scuola, tipo evento)

### Esempi di Generazione Automatica

**Convocazione Scuola:**
- Se trova "RSU" → "Convocazione RSU"
- Se trova "assemblea" → "Assemblea sindacale"
- Se trova "tavolo.*contrattazione" → "Contrattazione"

**Comunicazione UST/USR:**
- Se trova "GPS" e anno → "GPS 24/25"
- Se trova "graduatoria" → "Graduatorie"
- Se trova "utilizzazione" → "Utilizzazioni"

**Comunicazione Scuola:**
- Se trova "contrattazione.*integrativa" → "Contrattazione Integrativa"
- Se trova "informativa" → "Informativa"

---

## ⚙️ Configurazione e Personalizzazione

### Parametri Configurabili
Per ogni categoria è possibile personalizzare:
- **Label** (nome visualizzato)
- **Icona** (emoji)
- **Descrizione**
- **Priorità** (0-10)
- **Parole chiave**
- **Pattern mittenti** (regex)
- **Pattern oggetto** (regex)
- **Sottocategorie predefinite**

### Parametri Fissi (Non Modificabili)
- **Chiavi categorie** (es. `convocazione_scuola`)
- **Numero di categorie** (fisso a 10)
- **Enum PostgreSQL** (valori in minuscolo)

### Dove Configurare
- **Interfaccia:** Settings → Tab "Categorie"
- **File:** `/app/config/categories.json` (generato automaticamente)
- **Default:** Definiti in `backend/app/api/routes/settings.py`

---

## 📝 Note Tecniche

### Storage Database
- **Categoria:** Memorizzata come `String(50)` (non più Enum per flessibilità)
- **Sottocategoria:** Memorizzata come `String(100)`
- **Valori:** In minuscolo (es. `convocazione_scuola`)

### Compatibilità
- Il sistema valida sempre che le categorie appartengano all'enum `EmailCategory`
- Le sottocategorie sono libere (nessuna validazione enum)
- I nomi scuola NON vengono più aggiunti alle sottocategorie

### File Correlati
- `backend/app/models/email.py` - Modello Email con categorie
- `backend/app/services/categorizer.py` - Logica categorizzazione
- `backend/app/services/rule_based_classifier.py` - Classificatore rule-based
- `backend/app/api/routes/settings.py` - API configurazione categorie
- `frontend/src/pages/Settings.tsx` - Interfaccia configurazione

---

## 🚀 Best Practices

### Configurazione Categorie
1. Mantenere la priorità corretta (convocazioni > comunicazioni > altro)
2. Usare pattern regex specifici per migliorare accuratezza
3. Aggiungere parole chiave in italiano
4. Testare le modifiche su email reali

### Gestione Sottocategorie
1. Non preoccuparsi se il sistema genera sottocategorie non previste
2. Le sottocategorie predefinite sono solo un riferimento
3. Verificare periodicamente le sottocategorie generate

### Manutenzione
1. Resettare alle impostazioni default se ci sono problemi
2. Salvare configurazioni personalizzate prima di modifiche importanti
3. Monitorare il confidence score della categorizzazione

---

**Documento generato automaticamente il 2025-11-21**
