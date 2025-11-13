#!/bin/bash

# Script deployment SNALS Email Agent
# Usage: ./deploy.sh [production|staging]

set -e

ENVIRONMENT=${1:-production}
PROJECT_DIR="/home/claude/snals-email-agent"

echo "=== SNALS Email Agent - Deployment ==="
echo "Environment: $ENVIRONMENT"
echo "Project Dir: $PROJECT_DIR"
echo ""

# Backup database
echo "1. Backup database..."
./backup.sh

# Pull latest code (se git)
# cd $PROJECT_DIR
# git pull origin main

# Backend deployment
echo "2. Deploying backend..."
cd $PROJECT_DIR/backend
source venv/bin/activate
pip install -r requirements.txt --upgrade

# Database migrations
echo "3. Running migrations..."
alembic upgrade head

# Frontend deployment
echo "4. Deploying frontend..."
cd $PROJECT_DIR/frontend
npm install
npm run build

# Restart services
echo "5. Restarting services..."
sudo systemctl restart snals-backend
sudo systemctl restart snals-celery-worker
sudo systemctl restart snals-celery-beat

# Reload Nginx
echo "6. Reloading Nginx..."
sudo nginx -t && sudo systemctl reload nginx

echo ""
echo "✓ Deployment completato!"
echo ""
echo "Verifica servizi:"
echo "  - Backend: curl http://localhost:8001/health"
echo "  - Frontend: http://your-domain.com"
