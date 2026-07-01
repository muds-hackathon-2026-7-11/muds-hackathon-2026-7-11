.PHONY: help install dev dev-build down logs ps lint typecheck test format db-shell clean

help: ## show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## install JS and Python dependencies
	pnpm install
	cd apps/api && uv sync

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

lint: ## lint web (biome/eslint) and api (ruff)
	pnpm turbo run lint
	cd apps/api && uv run ruff check .

typecheck: ## typecheck web (tsc) and api (mypy)
	pnpm turbo run typecheck
	cd apps/api && uv run mypy .

test: ## run web and api test suites
	pnpm turbo run test
	cd apps/api && uv run pytest

format: ## format web (biome) and api (ruff)
	pnpm exec biome format --write .
	cd apps/api && uv run ruff format .

db-shell: ## open a psql shell against the dev db
	docker compose exec db psql -U postgres -d seminar_platform

clean: ## remove containers, volumes, and local build artifacts
	docker compose down -v
	rm -rf apps/web/.next apps/web/node_modules apps/api/.venv node_modules
