COMPOSE_DEV = docker compose --env-file .env.dev -f docker-compose.yml -f docker-compose.dev.yml

.PHONY: run-dev down-dev build-dev logs-dev shell-service-dev env-init keys-init seed-rbac migrate test auth-test-db lint lint-fix format format-check check

# =======
# HELPERS
# =======
define ensure_db
	@echo "Ensuring test database $(1)..."
	@$(COMPOSE_DEV) exec -T db psql -U postgres -tc "SELECT 1 FROM pg_database WHERE datname = '$(1)';" | grep -q 1 || $(COMPOSE_DEV) exec -T db psql -U postgres -c "CREATE DATABASE $(1);"
endef

# ============
# DEV COMMANDS
# ============
run-dev:
	$(COMPOSE_DEV) up -d $(ARGS)

down-dev:
	$(COMPOSE_DEV) down

build-dev:
	$(COMPOSE_DEV) build $(ARGS)

logs-dev:
	$(COMPOSE_DEV) logs $(SERVICE)

shell-service-dev:
	$(COMPOSE_DEV) exec -it $(SERVICE) sh -lc 'command -v bash >/dev/null 2>&1 && exec bash || exec sh'

# =======
# SCRIPTS
# =======
env-init:
	./scripts/init-env.sh

keys-init:
	./scripts/init-jwt-keys.sh $(ARGS)

seed-rbac:
	$(COMPOSE_DEV) exec -T app sh -lc 'cd /app && PYTHONPATH=/app uv run python scripts/seed_rbac.py'

migrate:
	$(COMPOSE_DEV) exec -T app uv run alembic upgrade head

# =============
# TEST COMMANDS
# =============
lint:
	@echo "Running ruff lint..."
	@$(COMPOSE_DEV) exec -T app uv run --extra dev ruff check .

lint-fix:
	@echo "Running ruff lint with fixes..."
	@$(COMPOSE_DEV) exec -T app uv run --extra dev ruff check . --fix

format:
	@echo "Running ruff format..."
	@$(COMPOSE_DEV) exec -T app uv run --extra dev ruff format .

format-check:
	@echo "Checking ruff format..."
	@$(COMPOSE_DEV) exec -T app uv run --extra dev ruff format --check .

check: lint format-check test

test: auth-test-db
	@echo "Running auth-service tests..."
	@$(COMPOSE_DEV) exec -T app uv run --extra dev pytest $(PYTEST_ARGS)

auth-test-db:
	$(call ensure_db,auth_db_test)
