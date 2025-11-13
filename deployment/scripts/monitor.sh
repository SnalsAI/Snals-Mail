#!/bin/bash

# Script monitoring servizi

echo "=== SNALS Email Agent - Status ==="
echo ""

# Servizi systemd
echo "--- Servizi ---"
for service in snals-backend snals-celery-worker snals-celery-beat; do
    status=$(systemctl is-active $service)
    if [ "$status" = "active" ]; then
        echo "✓ $service: $status"
    else
        echo "✗ $service: $status"
    fi
done
echo ""

# Database
echo "--- Database ---"
pg_isready -U snals_user -d snals_email_agent > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✓ PostgreSQL: connesso"
    psql -U snals_user -d snals_email_agent -c "SELECT COUNT(*) as email_count FROM emails;" -t
else
    echo "✗ PostgreSQL: non raggiungibile"
fi
echo ""

# Redis
echo "--- Redis ---"
redis-cli ping > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✓ Redis: attivo"
else
    echo "✗ Redis: non attivo"
fi
echo ""

# Ollama
echo "--- Ollama ---"
curl -s http://localhost:11434/api/tags > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✓ Ollama: attivo"
else
    echo "✗ Ollama: non attivo"
fi
echo ""

# Spazio disco
echo "--- Spazio Disco ---"
df -h /home/claude/snals-email-agent | tail -1
echo ""

# Ultimi errori log
echo "--- Ultimi Errori ---"
tail -5 /home/claude/snals-email-agent/logs/errors.log 2>/dev/null || echo "Nessun errore recente"
