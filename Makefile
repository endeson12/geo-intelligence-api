.PHONY: install lint format type test migrate seed run up down
install:
	uv sync --all-groups
lint:
	uv run ruff check .
	uv run ruff format --check .
format:
	uv run ruff check --fix .
	uv run ruff format .
type:
	uv run mypy
test:
	uv run pytest --cov=geo_intelligence_api --cov-report=term-missing
migrate:
	uv run alembic upgrade head
seed:
	uv run python scripts/seed.py
run:
	uv run uvicorn geo_intelligence_api.main:app --reload
up:
	docker compose up --build -d
down:
	docker compose down
