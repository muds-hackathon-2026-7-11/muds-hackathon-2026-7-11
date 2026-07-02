.PHONY: help install dev dev-build down logs ps lint typecheck test format migrate migration db-shell clean

help: ## show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## install JS and Python dependencies
	pnpm install
	cd apps/api && uv sync
	cd services/slack-bot && uv sync

dev: ## start db/api/web via docker compose (build if needed)
	docker compose up --build

dev-build: ## force-rebuild images and start
	docker compose up --build --force-recreate

down: ## stop and remove containers
	docker compose down

logs: ## tail logs from all services
	docker compose logs -f

ps: ## show running containers
	docker compose ps

lint: ## lint web (biome/eslint), api and slack-bot (ruff)
	pnpm turbo run lint
	cd apps/api && uv run ruff check .
	cd services/slack-bot && uv run ruff check .

typecheck: ## typecheck web (tsc), api and slack-bot (mypy)
	pnpm turbo run typecheck
	cd apps/api && uv run mypy .
	cd services/slack-bot && uv run mypy .

test: ## run web, api and slack-bot test suites (starts+migrates db if needed)
	docker compose up -d --wait db
	cd apps/api && uv run alembic upgrade head
	pnpm turbo run test
	cd apps/api && uv run pytest
	cd services/slack-bot && uv run pytest

format: ## format web (biome), api and slack-bot (ruff)
	pnpm exec biome format --write .
	cd apps/api && uv run ruff format .
	cd services/slack-bot && uv run ruff format .

migrate: ## apply pending Alembic migrations to the dev db
	cd apps/api && uv run alembic upgrade head

migration: ## generate a new Alembic migration (usage: make migration m="message")
	cd apps/api && uv run alembic revision --autogenerate -m "$(m)"

db-shell: ## open a psql shell against the dev db
	docker compose exec db psql -U postgres -d seminar_platform

clean: ## remove containers, volumes, and local build artifacts
	docker compose down -v
	rm -rf apps/web/.next apps/web/node_modules apps/api/.venv services/slack-bot/.venv node_modules
