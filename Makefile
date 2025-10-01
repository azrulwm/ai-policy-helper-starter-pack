.PHONY: dev dev-ollama prod prod-ollama test fmt check pre-commit down down-all setup env-check
dev:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d

dev-ollama:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml --profile ollama up -d

prod:
	docker compose up --build -d

prod-ollama:
	docker compose --profile ollama up --build -d

test:
	docker compose exec backend bash -c "cd /app && PYTHONPATH=/app pytest -v"

fmt:
	docker compose exec backend black app

check: fmt test
	@echo "✅ All checks passed!"

pre-commit: fmt check test
	@echo "✅ Pre-commit checks completed successfully"

# Clean shutdown commands
down:
	@echo "🛑 Stopping core services..."
	docker compose down

down-all:
	@echo "🛑 Stopping ALL services including Ollama..."
	docker compose --profile ollama down

# Environment setup and validation
setup:
	@echo "🔧 Setting up environment..."
	@if [ ! -f .env ]; then \
		echo "📝 Creating .env from .env.example..."; \
		cp .env.example .env; \
		echo "✅ Created .env file. Please edit it with your configuration."; \
	else \
		echo "✅ .env file already exists."; \
	fi

env-check:
	@echo "🔍 Checking environment configuration..."
	@if [ ! -f .env ]; then \
		echo "❌ .env file not found. Run 'make setup' first."; \
		exit 1; \
	fi
	@echo "✅ Environment file exists"
	@echo "📋 Current configuration:"
	@grep -v "^#" .env | grep -v "^$$" | while read line; do \
		key=$$(echo $$line | cut -d'=' -f1); \
		value=$$(echo $$line | cut -d'=' -f2-); \
		if [[ $$key == *"KEY"* ]] && [[ $$value != "" ]]; then \
			echo "   $$key=****"; \
		else \
			echo "   $$line"; \
		fi; \
	done
