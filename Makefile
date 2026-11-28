.PHONY: dev check seed test mcp api ui build

dev:
	python scripts/dev.py

check:
	python scripts/dev.py --check-only

seed:
	python -m scripts.seed

test:
	python -m pytest -q tests

mcp:
	python -m app.mcp_server

api:
	uvicorn app.api:app --port 8000

ui:
	cd frontend && npm run dev

build:
	cd frontend && npm install && npm run build
