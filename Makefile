.PHONY: up down logs migrate seed-model backend-shell worker-shell fmt lint test

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f backend worker

migrate:
	docker compose exec backend alembic upgrade head

revision:
	docker compose exec backend alembic revision --autogenerate -m "$(m)"

seed-model:
	# Pulls into the native host Ollama install that backend/worker point at by default
	# (see docs/DEPLOYMENT.md "Running Ollama natively"). If you're running the ollama-cpu
	# or ollama container profile instead, pull into that container directly, e.g.:
	# docker compose exec ollama-cpu ollama pull llama3.1
	ollama pull llama3.1

backend-shell:
	docker compose exec backend bash

worker-shell:
	docker compose exec worker bash

fmt:
	cd backend && ruff format . && ruff check --fix .

lint:
	cd backend && ruff check . && mypy app

test:
	cd backend && pytest
