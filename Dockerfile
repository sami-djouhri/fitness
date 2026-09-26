# Stage 1: Frontend build
FROM node:20-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci || npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Backend + Frontend
FROM python:3.13-slim AS backend
# Sicherheitsstand des Basis-Image nachziehen. Ein Upstream-Image friert die Paketstaende
# vom Tag seines Baus ein, Debian-security ist regelmaessig weiter, und ein `--pull` holt
# nur ein neueres Bild derselben Verspaetung: gemessen am 2026-09-13 trug das aktuelle
# python:3.13-slim aus der Registry dieselben drei perl-CVEs wie das monatealte lokale.
# `upgrade`, nicht `dist-upgrade`: letzteres darf Pakete entfernen, um Konflikte zu loesen.
RUN apt-get update \
 && apt-get -y upgrade \
 && rm -rf /var/lib/apt/lists/*


WORKDIR /app

COPY pyproject.toml .
COPY app/ app/
COPY migrations/ migrations/
COPY alembic.ini .
COPY scripts/ scripts/
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

RUN pip install --no-cache-dir . && \
    mkdir -p /app/data && \
    chmod 0755 /usr/local/bin/docker-entrypoint.sh

COPY --from=frontend /app/frontend/dist app/static/

RUN adduser --disabled-password --gecos "" --uid 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

ENV DATABASE_URL=sqlite:////app/data/app.db

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
