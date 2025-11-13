#!/bin/bash

# Restore da backup

set -e

if [ $# -eq 0 ]; then
    echo "Usage: ./restore.sh <backup_date>"
    echo "Example: ./restore.sh 20241113_120000"
    exit 1
fi

BACKUP_DATE=$1
BACKUP_DIR="/home/claude/backups/snals-email-agent"
PROJECT_DIR="/home/claude/snals-email-agent"

echo "=== Restore SNALS Email Agent ==="
echo "Backup: $BACKUP_DATE"
echo ""

# Verifica esistenza backup
if [ ! -f "$BACKUP_DIR/db_$BACKUP_DATE.sql.gz" ]; then
    echo "✗ Backup non trovato!"
    exit 1
fi

# Stop servizi
echo "Stop servizi..."
sudo systemctl stop snals-backend snals-celery-worker snals-celery-beat

# Restore database
echo "Restore database..."
gunzip -c $BACKUP_DIR/db_$BACKUP_DATE.sql.gz | psql -U snals_user snals_email_agent

# Restore storage
echo "Restore storage..."
tar -xzf $BACKUP_DIR/storage_$BACKUP_DATE.tar.gz -C $PROJECT_DIR

# Restore config
echo "Restore config..."
tar -xzf $BACKUP_DIR/config_$BACKUP_DATE.tar.gz -C $PROJECT_DIR/backend

# Restart servizi
echo "Restart servizi..."
sudo systemctl start snals-backend snals-celery-worker snals-celery-beat

echo ""
echo "✓ Restore completato!"
