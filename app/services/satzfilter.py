"""Was als Arbeitssatz zaehlt, an einer Stelle.

Die Bedingung stand vorher an zehn Stellen ausgeschrieben (``is_warmup ==
False``, teils zusaetzlich ``set_type != "warmup"``, teils ohne). Mit dem
Vorbefuellen aus dem Trainingstag kam ``is_completed`` als dritte Bedingung
hinzu, und eine an einer Stelle vergessene Bedingung faellt niemandem auf: die
Zahl ist dann nur falsch, nicht kaputt. Deshalb hier zentral.

Benutzung:

    q.filter(*arbeitssatz())          # alle Bedingungen
    q.filter(arbeitssatz_klausel())   # eine UND-Verknuepfung, z.B. in ON-Klauseln
"""

from sqlalchemy import and_
from sqlalchemy.sql.elements import BooleanClauseList

from app.models import WorkoutSet


def arbeitssatz() -> tuple:
    """Bedingungen fuer einen gezaehlten Satz: gemacht und kein Aufwaermsatz."""
    return (
        WorkoutSet.is_completed == True,  # noqa: E712
        WorkoutSet.is_warmup == False,  # noqa: E712
        WorkoutSet.set_type != "warmup",
    )


def arbeitssatz_klausel() -> BooleanClauseList:
    """Dieselben Bedingungen als einzelner Ausdruck.

    Fuer ``outerjoin``: dort gehoert die Bedingung in die ON-Klausel, nicht ins
    WHERE. Im WHERE wuerde sie den Aussenverbund zu einem Innenverbund machen
    und Workouts ohne passenden Satz ganz aus dem Ergebnis werfen.
    """
    return and_(*arbeitssatz())
