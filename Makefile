# ─────────────────────────────────────────────────────────────────────────────
# Pulse — Makefile
# ─────────────────────────────────────────────────────────────────────────────
.PHONY: help up down dev build logs ps clean redis-cli lint test

COMPOSE      := docker compose
COMPOSE_DEV  := docker compose -f docker-compose.yml -f docker-compose.dev.yml
TAG          ?= $(shell git rev-parse --short HEAD 2>/dev/null || echo dev)

# ── Help ─────────────────────────────────────────────────────────────────────
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?##' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "\033[36m%-20s\033[0m %s\n",$$1,$$2}'

# ── Production ───────────────────────────────────────────────────────────────
up: ## Start all services (production mode)
	$(COMPOSE) up -d

down: ## Stop all services
	$(COMPOSE) down

restart: ## Restart all services
	$(COMPOSE) restart

build: ## Build all Docker images
	$(COMPOSE) build --parallel

logs: ## Tail logs (all services)
	$(COMPOSE) logs -f

ps: ## Show running containers
	$(COMPOSE) ps

# ── Development ──────────────────────────────────────────────────────────────
dev: ## Start in dev mode (hot-reload)
	$(COMPOSE_DEV) up

dev-build: ## Build dev images
	$(COMPOSE_DEV) build

# ── Individual services ───────────────────────────────────────────────────────
backend: ## Start only backend + redis
	$(COMPOSE) up -d redis backend

frontend-dev: ## Run frontend dev server locally (no docker)
	cd frontend && npm run dev

# ── Redis ────────────────────────────────────────────────────────────────────
redis-cli: ## Open Redis CLI
	$(COMPOSE) exec redis redis-cli

redis-flush: ## Flush all Redis keys (CAUTION)
	$(COMPOSE) exec redis redis-cli FLUSHALL

# ── Linting ──────────────────────────────────────────────────────────────────
lint: lint-backend lint-frontend ## Run all linters

lint-backend: ## Lint Python code
	pip install ruff --quiet
	ruff check backend_fresh/

lint-frontend: ## Lint JS/JSX code
	cd frontend && npm run lint

# ── Tests ────────────────────────────────────────────────────────────────────
test: test-backend ## Run all tests

test-backend: ## Run Python tests
	pip install pytest pytest-asyncio --quiet
	pytest ml/ -v

# ── Setup ────────────────────────────────────────────────────────────────────
install: ## Install all dependencies locally
	pip install -r requirements.txt
	cd frontend && npm install

env: ## Copy .env.example to .env
	@test -f .env || (cp .env.example .env && echo "✅ .env created — edit it before starting")

# ── Cleanup ──────────────────────────────────────────────────────────────────
clean: ## Remove stopped containers and dangling images
	$(COMPOSE) down --remove-orphans
	docker image prune -f

clean-all: ## Remove everything including volumes (DESTRUCTIVE)
	$(COMPOSE) down -v --remove-orphans
	docker image prune -af

# ── Deployment ───────────────────────────────────────────────────────────────
push: ## Build & push images to registry
	docker build -t ghcr.io/$(shell git config user.name)/pulse-backend:$(TAG) ./backend_fresh
	docker build -t ghcr.io/$(shell git config user.name)/pulse-frontend:$(TAG) ./frontend
	docker push ghcr.io/$(shell git config user.name)/pulse-backend:$(TAG)
	docker push ghcr.io/$(shell git config user.name)/pulse-frontend:$(TAG)
