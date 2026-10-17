# Short entry points for the Docker environment (the main one). Logic lives in scripts/.
.DEFAULT_GOAL := help
.PHONY: help up build down restart ps logs shell test verify smoke doctor

help: ## List available commands
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  make %-9s %s\n", $$1, $$2}'

up: ## Start in the background and wait until the API is healthy
	@bash scripts/up.sh

build: ## Rebuild the image and start (after changing requirements.txt or the Dockerfile)
	@bash scripts/up.sh --build

down: ## Stop and remove the containers
	@docker compose down

restart: ## Restart only the API (e.g. after editing .env)
	@docker compose restart app

ps: ## Container status
	@docker compose ps

logs: ## Follow API logs (Ctrl+C leaves the logs, stops nothing)
	@docker compose logs -f app

shell: ## Open a shell inside the API container
	@docker compose exec app bash

test: ## Run pytest inside the container (extra args: make test ARGS="-k csf")
	@docker compose exec -T app pytest tests/ -v $(ARGS)

verify: ## Run what CI runs, before pushing
	@bash scripts/verify.sh

smoke: ## End-to-end check: health + OCR on the sample PDF
	@bash scripts/smoke.sh

doctor: ## Check machine prerequisites (read-only)
	@bash scripts/doctor.sh
