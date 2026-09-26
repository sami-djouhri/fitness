#!/usr/bin/env bash
# Testlauf von fitness.
#
# Gelaufen wird in einem Wegwerf-Container aus dem GEBAUTEN Image, nicht gegen
# eine Host-Umgebung. Das ist Absicht und folgt der Lehre aus dem Saganta-Lauf
# vom 30.08.2026: ein Test gegen den Quellbaum beweist, dass die Datei stimmt,
# nicht dass der laufende Dienst sie hat.
#
# pytest und httpx gehoeren bewusst NICHT ins Produktionsimage. Sie werden fuer
# den Lauf nach /tmp installiert, wie es der Kalender vormacht. Faellt die
# Installation aus (kein Netz), bricht der Lauf ab, statt stillschweigend
# weniger Tests zu sammeln.
#
# Erwartung: "274 passed" oder mehr, und KEIN "skipped". Laeuft eine kleinere
# Zahl durch oder erscheint ein Uebersprungener, wurde ein Modul still
# ausgelassen. Das ist nicht als gruen zu verbuchen.
set -euo pipefail
cd "$(dirname "$0")"

IMAGE="${IMAGE:-fitness-fitness}"

if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  echo "Image '$IMAGE' fehlt. Erst bauen:  docker compose build"
  exit 1
fi

# tests MUSS unter /app/tests liegen: die Suite importiert `tests.conftest`.
# --user 0:0 nur fuer den Lauf, die Rechte im Quellbaum bleiben unberuehrt.
# --entrypoint sh ist noetig: das fitness-Image hat einen Entrypoint, der
# Migrationen faehrt und uvicorn startet. Ohne die Umgehung wird der Testbefehl
# verschluckt und der Lauf haengt am laufenden Server, bis das Zeitlimit greift.
#
# ADMIN_TOKEN ist ein Wegwerfwert fuer den Lauf. Die Admin-Routen sind
# fail-closed (503 ohne Token, app/api/routes_admin.py), und tests/test_admin.py
# erwartet sie erreichbar. Ohne diese Zeile meldet der Lauf 12 Fehler, die
# nichts mit dem Code zu tun haben, und ein Lauf, der immer rot ist, erzieht
# dazu, ihn zu ignorieren.
# ★ `frontend/src/koerper` muss mit hinein: tests/test_koerpermodell.py gleicht
# die Muskelkennungen des 3D-Modells gegen die Registry im Backend ab. Ohne den
# Mount ueberspringt er sich selbst mit `pytest.skip`, und ein still
# uebersprungener Test ist schlimmer als keiner: der Lauf meldet gruen, und der
# Fehler, den er faengt (ein Muskel, der nie eingefaerbt wird), sieht in der
# Oberflaeche wie ein Messergebnis aus.
exec docker run --rm --user 0:0 --entrypoint sh \
  -v "$PWD/tests:/app/tests:ro" \
  -v "$PWD/app:/app/app:ro" \
  -v "$PWD/frontend/src/koerper:/app/frontend/src/koerper:ro" \
  -w /app \
  -e PYTHONPATH=/tmp/p:/app \
  -e ADMIN_TOKEN=pruflauf-wegwerfwert \
  "$IMAGE" \
  -c 'pip install -q --target /tmp/p pytest httpx || exit 1
      python -m pytest tests -q -p no:cacheprovider'
