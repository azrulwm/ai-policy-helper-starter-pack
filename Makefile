.PHONY: dev prod test fmt check pre-commit
dev:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d

prod:
	docker compose up --build -d

test:
	docker compose exec backend bash -c "cd /app && PYTHONPATH=/app pytest -v"

fmt:
	docker compose exec backend black app

check: fmt test
	@echo "✅ All checks passed!"

pre-commit: check
	@echo "🚀 Ready to commit!"
