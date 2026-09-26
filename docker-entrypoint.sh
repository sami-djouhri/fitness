#!/bin/sh
# docker-entrypoint.sh: boot pipeline für fitness-Container.
#
# Reihenfolge:
#   1. alembic upgrade head    (idempotent, no-op wenn DB up-to-date)
#   2. katalog_abgleich.py     (Übungskatalog aus dem Quelltext nachziehen, bei JEDEM Start)
#   3. exec uvicorn            (Server läuft als PID 1, Signale kommen korrekt an)
#
# ★ Schritt 2 hieß bis 2026-09 `seed_demo_data.py` und lief faktisch genau einmal:
# es stieg mit "Daten bereits vorhanden" aus, sobald eine einzige Übung existierte.
# Eine Korrektur am Katalog kam damit an einer laufenden Installation nie an.
# Der Abgleich legt an, zieht nach und löscht nie; selbst angelegte Übungen fasst
# er nicht an (app/services/katalog.py).
#
# Jeder Step loggt explizit. Fehler bedeutet exit 1 mit klarer Status-Zeile, damit
# Restart-Loops diagnostizierbar bleiben.

set -eu

echo "[entrypoint] --- fitness-Container Startup ---"

echo "[entrypoint] (1/3) alembic upgrade head"
if ! alembic upgrade head; then
  echo "[entrypoint] FATAL: alembic upgrade head failed (exit $?)" >&2
  exit 1
fi

echo "[entrypoint] (2/3) katalog_abgleich.py"
if ! python scripts/katalog_abgleich.py; then
  echo "[entrypoint] FATAL: katalog_abgleich.py failed (exit $?)" >&2
  exit 1
fi

echo "[entrypoint] (3/3) starting uvicorn on 0.0.0.0:8000"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
