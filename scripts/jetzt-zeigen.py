"""Zeigt die Einheit fuer jetzt im Klartext, damit man sie liest statt sie zu testen.

Gegenstueck zur Testsuite: die prueft Zusagen, dies zeigt das Ergebnis. Eine
Einheit kann jede Invariante erfuellen und trotzdem unbrauchbar sein, und zwar
auf eine Art, die kein assert findet: acht Saetze Bauch hintereinander, eine
Uebung mit einem einzigen Satz, eine Begruendung, die etwas ueber den Nutzer
behauptet, was er nie gesagt hat.

Am 2026-09-14 fand genau diese Bauart drei Fehler in der Tagesdecke, die 58
gruene Tests nicht gesehen hatten (Memory
``feedback_alle_tests_gruen_klartext_zeigt_fehler``).

Aufruf (eigene Datenbank unter /tmp, Produktionsdaten bleiben unberuehrt):

    docker compose run --rm -e DATABASE_URL=sqlite:////tmp/jetzt-schau.db \\
      -v "$(pwd)":/work -w /work --entrypoint python fitness scripts/jetzt-zeigen.py
"""
import os
import sys

if "/tmp/" not in os.environ.get("DATABASE_URL", ""):
    sys.exit("DATABASE_URL muss unter /tmp liegen. Abbruch, um Produktionsdaten zu schuetzen.")

from app.db import Base, engine, SessionLocal  # noqa: E402
from app.models import Exercise, Plan, PlanDay, PlanExercise  # noqa: E402
from app.services.jetzt import JetztService  # noqa: E402

# Ein Alltagsplan, wie ihn jemand wirklich haette: drei Tage, je drei bis vier
# Uebungen, alle ohne Geraet.
#
# ★ Die Namen stammen wortgleich aus ``data/uebungskatalog.py``. Die erste
# Fassung erfand plausible Namen ("Dips am Stuhl", "Klimmzüge"), von denen
# sieben von zwoelf nicht im Katalog stehen. Uebrig blieb ein Plantag mit einer
# einzigen Uebung, und die Probe zeigte daraufhin ein Verhalten, das es so gar
# nicht gibt.
PLAN = {
    "Druecken": [
        "Liegestütze",
        "Diamant-Liegestütze",
        "Pike-Liegestütze",
    ],
    "Ziehen": [
        "Klimmzüge Obergriff",
        "Klimmzüge Untergriff",
        "Chin-Up-Halten",
    ],
    "Beine": [
        "Kniebeugen Körpergewicht",
        "Ausfallschritte",
        "Bulgarische Kniebeugen",
        "Plank",
    ],
}


def aufbauen(db) -> None:
    """Echter Katalog, echter Plan.

    ★★ Der Katalog wird eingespielt und die Planuebungen werden **aus ihm**
    genommen, nicht neu angelegt. Die erste Fassung legte zwoelf eigene
    Uebungen an, und die tragen keine Muskelanteile: damit fiel jede von ihnen
    durch den Anteilsfilter der Empfehlung, das Auffuellen des Zeitfensters
    fand nie einen Kandidaten und meldete "es passt nichts Sinnvolles mehr
    dazu". Das sah wie ein Befund im Dienst aus und war einer in der Probe.
    """
    from app.services.katalog import katalog_einspielen

    katalog_einspielen(db)
    db.commit()

    plan = Plan(name="Push/Pull/Legs", is_active=True)
    db.add(plan)
    db.flush()
    for reihenfolge, (tagname, uebungen) in enumerate(PLAN.items()):
        tag = PlanDay(plan_id=plan.id, name=tagname, sort_order=reihenfolge)
        db.add(tag)
        db.flush()
        platz = 0
        for name in uebungen:
            uebung = db.query(Exercise).filter(Exercise.name == name).first()
            if uebung is None:
                # Ein Name, den es im Katalog nicht gibt, ist ein Fehler in
                # dieser Datei und keine Lage, die es abzubilden gaebe.
                raise SystemExit(f"Nicht im Katalog: {name!r}. Probe korrigieren.")
            db.add(PlanExercise(
                plan_day_id=tag.id, exercise_id=uebung.id,
                sort_order=platz, target_sets=3, rest_seconds=90,
            ))
            platz += 1
    db.commit()


def zeigen(db, ueberschrift: str, minuten: int | None, quelle: str) -> None:
    ergebnis = JetztService(db).training(minuten=minuten, minuten_quelle=quelle)
    strich = "=" * 68
    print(f"\n{strich}\n{ueberschrift}")
    print(f"{ergebnis.titel}   ({ergebnis.quelle})")
    print(f"Fenster {ergebnis.minuten} min [{ergebnis.minuten_quelle}], "
          f"geplant {ergebnis.geplante_minuten} min")
    print(f"{ergebnis.begruendung}")
    print("-" * 68)
    for uebung in ergebnis.uebungen:
        last = ""
        if uebung.gewicht_kg:
            last = f" {uebung.gewicht_kg:g} kg"
        if uebung.wdh:
            last += f" x{uebung.wdh}"
        gekuerzt = (f"   (von {uebung.gekuerzt_von} gekuerzt)"
                    if uebung.gekuerzt_von else "")
        # "+" markiert, was nicht aus dem Plan kommt, sondern das Fenster fuellt.
        marke = "+ " if uebung.ergaenzt else "  "
        print(f"{marke}{uebung.saetze} x {uebung.name:<22}{last:<12}"
              f" Pause {uebung.pause_s}s  [{uebung.gruppenname}]{gekuerzt}")
    if not ergebnis.uebungen:
        print("  (nichts)")
    print("-" * 68)
    for hinweis in ergebnis.hinweise:
        print(f"  Hinweis: {hinweis}")


def main() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.info["owner_sub"] = os.environ.get("DEFAULT_OWNER_SUB", "schau-owner")
    aufbauen(db)

    zeigen(db, "VOLLE EINHEIT (Kalenderblock 60 min)", 60, "kalender")
    zeigen(db, "KNAPPE ZEIT (Kalenderblock 25 min)", 25, "kalender")
    zeigen(db, "SEHR KNAPP (Kalenderblock 12 min)", 12, "kalender")
    zeigen(db, "NIEMAND WEISS ES (keine Angabe)", None, "angefragt")


if __name__ == "__main__":
    main()
