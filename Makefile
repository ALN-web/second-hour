.PHONY: dev seed test mcp api ui build

dev:
	./start.sh

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
