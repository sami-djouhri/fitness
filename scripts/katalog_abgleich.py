"""Uebungskatalog aus dem Quelltext in die Datenbank abgleichen.

Laeuft im Entrypoint bei jedem Start. Loest das Seeding der Uebungen aus
``seed_demo_data.py`` ab: dort standen sie in einer Liste, die nur beim
allerersten Start gelesen wurde ("Daten bereits vorhanden, ueberspringe
Seed"). Eine Korrektur an einer Uebung kam damit nie an einer bestehenden
Installation an.

Abschaltbar mit ``SKIP_KATALOG_ABGLEICH=1``, fuer den Fall, dass jemand
seinen Katalog vollstaendig selbst pflegen will.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import SessionLocal  # noqa: E402
from app.services.katalog import katalog_einspielen  # noqa: E402


def main() -> int:
    if os.environ.get("SKIP_KATALOG_ABGLEICH") == "1":
        print("[katalog] uebersprungen (SKIP_KATALOG_ABGLEICH=1)")
        return 0
    db = SessionLocal()
    try:
        zahlen = katalog_einspielen(db)
    finally:
        db.close()
    print(
        "[katalog] {gesamt} Uebungen im Bestand "
        "({angelegt} neu, {aktualisiert} nachgezogen, "
        "{umbenannt} umbenannt, {nachgetragen} Anteile ergaenzt)".format(**zahlen)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
