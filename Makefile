# Makefile per Snals-Mail

.PHONY: help build up down logs clean restart backend frontend mongodb

# Default target
help:
	@echo "Snals-Mail - Comandi Disponibili:"
	@echo ""
	@echo "  make build      - Build di tutti i container Docker"
	@echo "  make up         - Avvia tutti i servizi"
	@echo "  make down       - Ferma tutti i servizi"
	@echo "  make restart    - Riavvia tutti i servizi"
	@echo "  make logs       - Mostra i log di tutti i servizi"
	@echo "  make backend    - Mostra i log del backend"
	@echo "  make frontend   - Mostra i log del frontend"
	@echo "  make mongodb    - Mostra i log di MongoDB"
	@echo "  make clean      - Rimuove container, volumi e immagini"
	@echo "  make install    - Copia .env.example in .env"
	@echo ""

# Build all containers
build:
	docker-compose build --no-cache

# Start all services
up:
	docker-compose up -d

# Stop all services
down:
	docker-compose down

# Restart all services
restart:
	docker-compose restart

# Show logs from all services
logs:
	docker-compose logs -f

# Show backend logs
backend:
	docker-compose logs -f backend

# Show frontend logs
frontend:
	docker-compose logs -f frontend

# Show MongoDB logs
mongodb:
	docker-compose logs -f mongodb

# Clean everything
clean:
	docker-compose down -v
	docker system prune -af

# Install environment file
install:
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "File .env creato da .env.example"; \
		echo "IMPORTANTE: Modifica .env con le tue configurazioni!"; \
	else \
		echo "File .env già esistente"; \
	fi

# Development mode
dev:
	docker-compose up

# Check status
status:
	docker-compose ps

# Execute bash in backend container
backend-shell:
	docker-compose exec backend sh

# Execute bash in frontend container
frontend-shell:
	docker-compose exec frontend sh

# Execute mongo shell
mongo-shell:
	docker-compose exec mongodb mongosh -u admin -p admin123
