"""Der Loeschweg dieses Dienstes: welche Tabelle in welcher Reihenfolge faellt.

Die Mechanik liegt in ``konto_mechanik.py`` (dort auch, warum es hier keine
Netzroute gibt und wie die vier Kopien abgeglichen werden). Hier steht nur, was
dieser Dienst ueber seine eigenen Tabellen weiss.

    docker exec -w /app fitness python -m app.konto --sub X [--loeschen]

``exercise`` HEISST ANDERS UND IST DESHALB FAST DURCHGERUTSCHT
=================================================================

``app/tenant.py`` fuehrt ``TENANT_MODELS`` mit **zwoelf** Modellen. Tabellen mit
einer Mandantenspalte gibt es aber **dreizehn**: ``exercise`` traegt
``created_by_sub`` und steht nicht im Scoping, weil der Uebungskatalog geteilt
ist. Eine selbst angelegte Uebung traegt dort trotzdem ihren Urheber.

Deshalb hat ``MANDANTEN_SPALTEN`` in der Mechanik eine Liste von Namen und
keinen einzigen: ein Pruefer, der Eigenschaften am Namen erkennt, findet genau
das nicht, was anders benannt ist. Die Bedingung ``created_by_sub = :sub``
trifft die Katalog-Uebungen (``NULL``) nicht, der Katalog bleibt also stehen.

``exercise`` faellt als **letztes**: vier Tabellen verweisen darauf, drei
davon ohne ``ondelete``, und ``PRAGMA foreign_keys=ON`` steht in ``db.py``.

Das Scoping greift beim Loeschen nicht (es prueft ``is_select``), deshalb
steht die Mandantenbedingung in jedem Schritt ausdruecklich.
"""

from __future__ import annotations

from app import konto_mechanik as mechanik

PLAN = mechanik.Plan(
    dienst="fitness",
    schritte=(
        # Von innen nach aussen: was auf anderes zeigt, faellt zuerst.
        mechanik.eigene("personal_record", warum="Bestleistungen, zeigen auf Satz und Uebung"),
        mechanik.eigene("workout_set", warum="einzelne Saetze"),
        mechanik.eigene("workout", warum="Trainingseinheiten"),
        mechanik.eigene("plan_exercise", warum="Uebungen im Trainingsplan"),
        mechanik.eigene("plan_day", warum="Trainingstage"),
        mechanik.eigene("plan", warum="Trainingsplaene"),
        mechanik.eigene("exercise_selection", warum="Uebungsauswahl des Mandanten"),
        mechanik.eigene("body_metric", warum="Koerperwerte"),
        mechanik.eigene("tagesschritte", warum="Schrittzaehlung"),
        mechanik.eigene("anstoss_merker", warum="Merker fuer Anstoesse"),
        mechanik.eigene("nutzerprofil", warum="Profil"),
        # Zuletzt, siehe Modulkopf: anderer Spaltenname, und vieles zeigt darauf.
        mechanik.eigene("exercise", spalte="created_by_sub",
                        warum="SELBST angelegte Uebungen (Katalog hat NULL, bleibt)"),
    ),
    gemeinsam=frozenset(),
)


if __name__ == "__main__":
    from app import models  # noqa: F401  (fuellt Base.metadata, sonst laufen die Pruefungen blind)
    from app.db import Base, SessionLocal

    raise SystemExit(mechanik.als_programm(PLAN, Base.metadata, SessionLocal))
