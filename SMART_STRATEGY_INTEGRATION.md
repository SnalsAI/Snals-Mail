# Smart Strategy Integration - Documentazione

## 📋 Panoramica

È stata completata l'integrazione della **strategia ibrida intelligente** per l'estrazione di interpelli e la generazione di risposte, ottimizzata per **qualità** bilanciando costi e velocità.

## 🎯 Obiettivi Raggiunti

### 1. Smart Interpello Extractor (Estrazione Interpelli)
**Strategia a cascata in 4 step:**
1. **Regex** (50ms) - estrazione veloce con pattern
2. **Validazione LLM locale** (30-120s) - verifica qualità dati regex
3. **Estrazione LLM locale** (45-60s) - estrazione completa se validazione fallisce
4. **OpenAI fallback** (3-5s) - garanzia qualità quando locale fallisce

**Threshold qualità:** 85% completezza (almeno 3.4/4 campi richiesti)

### 2. Smart Response Generator (Generazione Risposte)
**Strategia intelligente:**
1. **Classificazione complessità** - analizza tipo task + keywords + lunghezza
2. **LLM locale per semplici/moderate** - con validazione qualità output
3. **OpenAI per complesse** - o quando validazione locale fallisce
4. **Cache risposte** - per FAQ e query ripetute

**Rate Limiter:** Budget massimo €1/giorno per OpenAI

## 📁 File Modificati/Creati

### Nuovi File (Core Strategy)
1. **`backend/app/services/smart_extractor.py`** (331 righe)
   - Classe `SmartInterpelloExtractor`
   - Cascata: Regex → Validation → Ollama → OpenAI
   - Completeness scoring (85% threshold)
   - Field merging per qualità massima

2. **`backend/app/services/regex_validator.py`** (285 righe)
   - Classe `RegexValidator`
   - Validazione LLM locale dei dati regex
   - Confidence scoring per campo (0.0-1.0)
   - Timeout configurabile (default 120s per qualità)

3. **`backend/app/services/smart_generator.py`** (459 righe)
   - Classe `SmartResponseGenerator`
   - Classificazione complessità (SIMPLE/MODERATE/COMPLEX)
   - Validazione qualità output locale
   - Cache MD5-based per risposte

4. **`backend/app/services/openai_rate_limiter.py`** (219 righe)
   - Classe `OpenAIRateLimiter`
   - Tracking spesa giornaliera OpenAI
   - Blocco richieste oltre budget
   - Persistenza JSON per tracking

### File Integrati
5. **`backend/app/services/interpello_parser.py`**
   - Aggiunto import `SmartInterpelloExtractor`
   - Supporto strategia `'smart'` in `__init__()`
   - Usa SmartInterpelloExtractor quando `INTERPELLO_PARSER_STRATEGY=smart`

6. **`backend/app/services/action_executor.py`**
   - Aggiunto import `SmartResponseGenerator`, `TaskType`
   - Inizializzazione generatore in `__init__()`
   - Integrato in `_execute_sintesi()` per sintesi email
   - Integrato in `_execute_draft_appuntamento()` per bozze appuntamenti
   - Integrato in `_execute_draft_tesseramento()` per bozze tesseramento
   - Logging dettagliato strategia usata + tempo

### Configurazione
7. **`backend/.env`**
   - `INTERPELLO_PARSER_STRATEGY=smart` (era `regex`)
   - `OPENAI_DAILY_LIMIT_EUR=1.0` (nuovo)
   - Commenti aggiornati con opzione `smart`

8. **`backend/app/config.py`**
   - Aggiunto `OPENAI_DAILY_LIMIT_EUR: float = 1.0`
   - Aggiornato default `OPENAI_MODEL` a `gpt-4o-mini`
   - Commenti aggiornati per strategia `smart`

## 🚀 Come Usare

### Interpello Parser con Smart Strategy

```python
from app.services.interpello_parser import InterpelloParser

# Inizializza con strategia smart (legge da .env)
parser = InterpelloParser()

# Oppure forza strategia smart
parser = InterpelloParser(strategy='smart')

# Estrai interpello
risultato = parser.extract_from_email(
    corpo=email_body,
    allegati_testo=attachments_text
)

# Verifica strategia usata
if risultato:
    metadata = risultato['metadata_estrazione']
    print(f"Strategia: {metadata['strategy_final']}")
    print(f"Tempo: {metadata['total_time_ms']}ms")
    print(f"Completezza: {metadata['completeness_scores']}")
```

### Response Generator Diretto

```python
from app.services.smart_generator import SmartResponseGenerator, TaskType
from app.config import get_settings

settings = get_settings()

generator = SmartResponseGenerator(
    openai_api_key=settings.OPENAI_API_KEY,
    openai_model=settings.OPENAI_MODEL,
    daily_limit_eur=settings.OPENAI_DAILY_LIMIT_EUR
)

# Genera risposta semplice
result = generator.generate(
    prompt="Sintetizza questa email...",
    task_type=TaskType.SINTESI,
    max_tokens=300,
    use_cache=True
)

print(result['risposta'])
print(f"Strategia: {result['metadata']['strategy_final']}")

# Genera risposta complessa
result = generator.generate(
    prompt="Fornisci consulenza legale su...",
    task_type=TaskType.CONSULENZA,
    max_tokens=500
)
```

### Action Executor (Automatico)

L'integrazione è **automatica** per le azioni:
- `SINTESI` - generazione sintesi email
- `BOZZA_APPUNTAMENTO` - risposta appuntamento
- `BOZZA_TESSERAMENTO` - risposta tesseramento

```python
from app.services.action_executor import ActionExecutor

executor = ActionExecutor(db)

# Esegui azione sintesi (usa automaticamente SmartResponseGenerator)
executor.execute_action(azione_id)

# Il sistema:
# 1. Classifica complessità
# 2. Tenta LLM locale con validazione
# 3. Fallback a OpenAI se necessario
# 4. Logga strategia usata
```

## 📊 Monitoring e Statistiche

### Smart Extractor Stats

```python
stats = extractor.get_stats()
# Output:
# {
#   'regex_only': 10,          # Risolti solo con regex
#   'regex_validated': 5,      # Regex validato da LLM
#   'regex_local': 3,          # Regex + LLM locale
#   'openai_fallback': 2,      # Richiedevano OpenAI
#   'total': 20,
#   'regex_only_pct': 50.0,
#   'regex_local_pct': 15.0,
#   'openai_fallback_pct': 10.0
# }
```

### Smart Generator Stats

```python
stats = generator.get_stats()
# Output:
# {
#   'local_validated': 15,        # Risposte locali validate
#   'openai_direct': 3,           # OpenAI per task complessi
#   'local_fallback_openai': 2,   # Locale fallito → OpenAI
#   'openai_blocked_budget': 0,   # Bloccati per budget
#   'cache_hits': 5,              # Cache hit
#   'total': 25,
#   'local_validated_pct': 60.0,
#   'openai_usage_pct': 20.0,
#   'cache_hit_rate': 16.7
# }
```

### OpenAI Rate Limiter

```python
from app.services.openai_rate_limiter import get_rate_limiter

limiter = get_rate_limiter()

# Verifica budget
remaining = limiter.get_remaining_budget()
print(f"Budget rimanente oggi: €{remaining:.4f}")

# Statistiche ultimi 7 giorni
stats = limiter.get_stats(days=7)
print(stats)
```

## 🔧 Configurazione Avanzata

### Timeout e Threshold

**Smart Extractor (`smart_extractor.py`):**
```python
# Threshold completezza
if completeness_regex >= 0.85:  # 85% = almeno 3.4/4 campi
    return dati_regex

# Timeout validazione
validation_result = self.regex_validator.validate_extracted_data(
    timeout=120.0  # Privilegia qualità su velocità
)

# Confidence threshold
if confidence >= 0.85:  # Alta soglia per garantire qualità
    return validated_data
```

**Smart Generator (`smart_generator.py`):**
```python
# Classificazione complessità
if max_tokens > 400:
    complexity = ResponseComplexity.COMPLEX

if complex_keyword_count >= 3:
    complexity = ResponseComplexity.COMPLEX

# Validazione qualità
if len(risposta) < min_length:
    return False, "troppo_corta"

if common_keywords < 2:
    return False, "off_topic"
```

### Budget OpenAI

**Rate Limiter (`openai_rate_limiter.py`):**
```python
# Storage persistente
storage_path = "storage/openai_usage.json"

# Warning threshold
if budget_used_pct >= 80:
    logger.warning(f"Budget quasi esaurito: {budget_used_pct:.1f}%")

# Blocco richieste
def can_make_request(self, estimated_cost_eur: float):
    remaining = self.get_remaining_budget()
    return remaining >= estimated_cost_eur
```

## 🎯 Performance Attese

### Interpello Extraction
- **70-85% casi:** Risolti con Regex + Validazione (veloce, free)
- **10-20% casi:** Richiedono Ollama completo (~60s, free)
- **5-10% casi:** Fallback OpenAI (~3s, ~€0.0001)

### Response Generation
- **Sintesi semplici:** LLM locale (~10-20s, free)
- **FAQ/Standard:** LLM locale + validazione (~30s, free)
- **Consulenza complessa:** OpenAI (~3-5s, ~€0.0003)

### Costo Medio Giornaliero
Con limite €1/giorno e uso ottimizzato:
- ~50-100 interpelli processati
- ~200-300 risposte generate
- ~70% richieste risolte localmente (free)
- ~30% richiedono OpenAI (budget controlled)

## 🐛 Troubleshooting

### Problema: Budget OpenAI esaurito

**Sintomo:** Log `🚫 Budget OpenAI esaurito`

**Soluzione:**
```bash
# Aumenta limite in .env
OPENAI_DAILY_LIMIT_EUR=2.0

# Oppure resetta manualmente
rm storage/openai_usage.json
```

### Problema: Validazione LLM locale timeout

**Sintomo:** Log `⚠️ Errore validazione: timeout`

**Soluzione:**
```python
# In smart_extractor.py, aumenta timeout
validation_result = self.regex_validator.validate_extracted_data(
    timeout=180.0  # Aumentato da 120s
)
```

### Problema: Qualità locale insufficiente

**Sintomo:** Troppe chiamate OpenAI (>40%)

**Soluzione:**
```python
# In smart_generator.py, abbassa threshold validazione
if overall_confidence >= 0.75:  # Era 0.85
    is_valid = True
```

## ✅ Test e Verifica

### Test Manuale (Docker)

```bash
# Entra nel container backend
docker exec -it snals-mail-backend-1 bash

# Esegui test integration
python test_smart_integration.py
```

### Test via API

```bash
# Test parsing interpello con strategia smart
curl -X POST http://localhost:8001/api/v1/interpelli/parse \
  -H "Content-Type: application/json" \
  -d '{
    "email_id": 123,
    "strategy": "smart"
  }'

# Verifica strategia usata nei log
docker logs snals-mail-backend-1 | grep "strategy_final"
```

### Verifica Budget

```bash
# Controlla file usage
docker exec snals-mail-backend-1 cat storage/openai_usage.json

# Output:
# {
#   "daily_usage": {
#     "2025-11-19": 0.0234
#   },
#   "total_requests": 45,
#   "total_cost_eur": 0.1523
# }
```

## 📈 Metriche Chiave

### KPI da Monitorare

1. **Tasso successo locale:**
   - Target: >70% risposte con LLM locale
   - Monitorare: `local_validated_pct` in stats

2. **Costo OpenAI giornaliero:**
   - Target: <€1/giorno
   - Monitorare: `openai_usage.json`

3. **Completezza estrazione:**
   - Target: >85% campi estratti
   - Monitorare: `completeness_scores` in metadata

4. **Tempo medio risposta:**
   - Sintesi: <30s (locale) o <5s (OpenAI)
   - Interpelli: <120s (completo) o <100ms (regex)

## 🔄 Prossimi Passi

1. **Monitoraggio produzione:**
   - Dashboard Grafana per visualizzare metriche
   - Alerting se budget >80%

2. **Ottimizzazione continua:**
   - Analisi errori validazione
   - Tuning threshold basato su dati reali
   - Cache intelligente per pattern comuni

3. **Miglioramenti possibili:**
   - Fine-tuning modello locale su dataset interpelli
   - Regex patterns più avanzati per ridurre fallback
   - Context window expansion per LLM locale

## 📝 Note Implementative

### Qualità vs Velocità
Il sistema è stato ottimizzato per **qualità** come richiesto:
- Timeout validazione: 120s (privilegia accuratezza)
- Confidence threshold: 0.85 (alta barra qualità)
- Field merging: preserva campi validati anche se LLM locale fallisce

### Cache Strategy
La cache è abilitata solo per:
- Sintesi (task ripetitivi)
- FAQ (risposte standard)
- NON per consulenze (sempre fresche)

### OpenAI Fallback
OpenAI viene usato quando:
- Task classificato come COMPLEX (consulenza, analisi normativa)
- Validazione locale fallisce (confidence <0.85)
- LLM locale non produce output valido
- Budget ancora disponibile

---

**Implementazione completata:** 2025-11-19
**Versione:** 1.0
**Strategia:** Quality-first hybrid cascade (Regex → LLM validate → Ollama → OpenAI)
