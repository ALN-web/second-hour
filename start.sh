#!/usr/bin/env bash
# One-command start: MCP server (:8001), agent host (:8000), frontend dev server (:5173).
# Usage: ./start.sh            (first run seeds the demo DB automatically)
#        SEED=1 ./start.sh     (force re-seed)
set -e
cd "$(dirname "$0")"
PY=python
[ -x .venv/bin/python ] && PY=.venv/bin/python
[ -x .venv/Scripts/python.exe ] && PY=.venv/Scripts/python.exe
export PYTHONIOENCODING=utf-8
if [ "${SEED:-0}" = "1" ] || [ ! -f data/secondhour.db ]; then $PY -m scripts.seed; fi
$PY -m app.mcp_server & MCP_PID=$!
sleep 2
$PY -m uvicorn app.api:app --host 127.0.0.1 --port 8000 & API_PID=$!
trap 'kill $MCP_PID $API_PID 2>/dev/null' EXIT INT TERM
if [ -d frontend/node_modules ]; then
  (cd frontend && npm run dev)
else
  echo "Frontend deps not installed: run 'cd frontend && npm install'. Serving built UI (if any) at http://localhost:8000"
  wait
fi
