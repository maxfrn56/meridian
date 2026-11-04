FROM node:22-bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip python3-venv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY apps/api/requirements.txt /app/apps/api/requirements.txt
RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir -r /app/apps/api/requirements.txt

COPY apps/web/package.json apps/web/package-lock.json /app/apps/web/
WORKDIR /app/apps/web
RUN npm ci

COPY apps/web /app/apps/web
COPY apps/api /app/apps/api
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh \
    && npm run build

ENV API_URL=http://127.0.0.1:8000 \
    NEXT_TELEMETRY_DISABLED=1 \
    PYTHONUNBUFFERED=1 \
    MOCK_LLM=auto

WORKDIR /app
EXPOSE 3000
CMD ["/app/start.sh"]
