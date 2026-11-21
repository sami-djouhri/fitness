"""Anstoss-Lauf im Container, fuer den Timer am Wirt.

    docker exec fitness python -m app.anstoss_lauf [--trockenlauf | --probe]

``--probe`` meldet nichts an Nutzer, sondern schickt eine Pruefnachricht an
``homelab/fitness/probe/test`` (keine brain-bus-Regel) und sagt, ob der Broker
Anmeldung und Nachricht bestaetigt hat. Fuer das Einrichten des Timers.

Derselbe Vorgang wie ``POST /api/anstoss/pruefen``, aber ohne HTTP und damit
ohne Token: wer ``docker exec`` darf, kommt ohnehin an alles. Bis zum
2026-11-21 lief die Erinnerung nie, weil der Weg ueber den Endpunkt einen
Token in zwei Dateien brauchte, die nie angelegt wurden.

Exit 0 heisst: geprueft, und alles Faellige hat den Ausgang erreicht. Exit 1:
mindestens eine Meldung kam nicht an. Exit 2: kein Ausgang eingerichtet
(``MQTT_HOST`` leer), der Lauf haette nichts melden koennen. So scheitert der
Timer sichtbar statt still gruen zu laufen.
"""

from __future__ import annotations

import json
import sys

from app.mqtt import publisher
from app.services import anstoss


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    trockenlauf = "--trockenlauf" in argv
    if "--probe" in argv:
        return _probe()
    if not trockenlauf and not publisher.konfiguriert:
        print("kein Ausgang eingerichtet (MQTT_HOST leer), nichts geprueft", file=sys.stderr)
        return 2
    try:
        ergebnis = anstoss.alle_pruefen(trockenlauf=trockenlauf)
    finally:
        publisher.trennen()
    print(json.dumps(ergebnis, ensure_ascii=False, default=str))
    if not trockenlauf and any(not m["gesendet"] for m in ergebnis["meldungen"]):
        return 1
    return 0


def _probe() -> int:
    if not publisher.konfiguriert:
        print("kein Ausgang eingerichtet (MQTT_HOST leer)", file=sys.stderr)
        return 2
    try:
        ok = publisher.publish("probe", "test", {"quelle": "fitness", "probe": True})
    finally:
        publisher.trennen()
    print(json.dumps(publisher.zustand(), ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
