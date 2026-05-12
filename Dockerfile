# Build React, then run FastAPI + static UI (same as local http://127.0.0.1:8000)
FROM node:22-alpine AS frontend
WORKDIR /frontend
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.12-slim-bookworm
WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=frontend /frontend/dist ./web/dist

ENV PORT=8000
ENV FASTAPI_ONLY=1
EXPOSE 8000

CMD ["sh", "-c", "exec uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}"]
