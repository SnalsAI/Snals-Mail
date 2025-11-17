.PHONY: help build up down restart logs test clean init-ollama

help: ## Mostra questo help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

build: ## Build di tutti i container
	docker-compose build

up: ## Avvia tutti i servizi
	docker-compose up -d
	@echo "✅ Servizi avviati!"
	@echo "   - Backend API: http://localhost:8001"
	@echo "   - PostgreSQL: localhost:5433"
	@echo "   - Redis: localhost:6380"
	@echo "   - Ollama: http://localhost:11434"

down: ## Ferma tutti i servizi
	docker-compose down

restart: down up ## Riavvia tutti i servizi

logs: ## Mostra logs di tutti i servizi
	docker-compose logs -f

logs-backend: ## Mostra logs del backend
	docker-compose logs -f backend

logs-celery: ## Mostra logs di Celery worker
	docker-compose logs -f celery-worker

logs-beat: ## Mostra logs di Celery beat
	docker-compose logs -f celery-beat

ps: ## Mostra status servizi
	docker-compose ps

init-db: ## Inizializza database (migrations)
	docker-compose exec backend alembic upgrade head
	@echo "✅ Database inizializzato!"

init-ollama: ## Scarica modelli Ollama
	./backend/scripts/init_ollama.sh
	@echo "✅ Modelli Ollama pronti!"

test: ## Esegue test sistema
	docker-compose exec backend python scripts/test_system.py

shell-backend: ## Shell nel container backend
	docker-compose exec backend /bin/bash

shell-db: ## Connessione PostgreSQL
	docker-compose exec postgres psql -U snals_user -d snals_email_agent

clean: ## Rimuove container, volumi e immagini
	docker-compose down -v
	docker system prune -f

setup: build up init-db init-ollama ## Setup completo (build + up + init)
	@echo "🎉 Sistema pronto!"
	@echo "   Esegui 'make test' per verificare il funzionamento"

.DEFAULT_GOAL := help
