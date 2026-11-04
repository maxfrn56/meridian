#!/bin/sh
set -eu

/opt/venv/bin/uvicorn main:app --app-dir /app/apps/api --host 127.0.0.1 --port 8000 &
api_pid=$!

cd /app/apps/web
node node_modules/next/dist/bin/next start --hostname 0.0.0.0 --port "${PORT:-3000}" &
web_pid=$!

term() {
  kill "$api_pid" "$web_pid" 2>/dev/null || true
}

trap term TERM INT

while kill -0 "$api_pid" 2>/dev/null && kill -0 "$web_pid" 2>/dev/null; do
  sleep 1
done

term
wait || true
exit 1
