#!/bin/bash

# Backup database e file

set -e

BACKUP_DIR="/home/claude/backups/snals-email-agent"
DATE=$(date +%Y%m%d_%H%M%S)
PROJECT_DIR="/home/claude/snals-email-agent"

echo "=== Backup SNALS Email Agent ==="
echo "Data: $DATE"

# Crea directory backup
mkdir -p $BACKUP_DIR

# Backup database PostgreSQL
echo "Backup database..."
pg_dump -U snals_user snals_email_agent | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Backup storage (allegati)
echo "Backup storage..."
tar -czf $BACKUP_DIR/storage_$DATE.tar.gz -C $PROJECT_DIR storage

# Backup config
echo "Backup configurazioni..."
tar -czf $BACKUP_DIR/config_$DATE.tar.gz -C $PROJECT_DIR/backend .env config

# Rimuovi backup vecchi (>30 giorni)
echo "Pulizia backup vecchi..."
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete

echo "✓ Backup completato: $BACKUP_DIR"
ls -lh $BACKUP_DIR | tail -5
