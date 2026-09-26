"""Exercise catalog service."""

from sqlalchemy import or_
from sqlalchemy.orm import Query, Session

from app.config import settings
from app.domain import DomainError
from app.models import Exercise, ExerciseSelection, PlanExercise, WorkoutSet
from app.schemas import ExerciseCreate, ExerciseUpdate
from app.services.muscle_map import MUSCLE_TO_REGION, REGION_TO_MUSCLES


class ExerciseService:
    """Der Katalog ist geteilt, der Umgang damit nicht.

    ``exercise`` steht bewusst nicht unter dem Mandanten-Scoping in
    app/tenant.py: die Eintraege aus dem Seed sollen allen zur Verfuegung
    stehen, statt je Nutzer 67-mal zu existieren. Was daraus folgt, stand
    bisher nirgends und war deshalb offen:

    - sichtbar ist der Seed (``created_by_sub IS NULL``) plus das Eigene,
    - aendern und loeschen darf nur, wer den Eintrag angelegt hat,
    - Seed-Eintraege aendert niemand,
    - was in einem Plan oder Workout haengt, wird nicht geloescht.
    """

    def __init__(self, db: Session):
        self.db = db

    @property
    def _sub(self) -> str:
        return self.db.info.get("owner_sub") or settings.DEFAULT_OWNER_SUB

    def _sichtbar(self, q: Query) -> Query:
        """Seed-Eintraege und eigene. Fremd angelegte bleiben fremd."""
        return q.filter(or_(
            Exercise.created_by_sub.is_(None),
            Exercise.created_by_sub == self._sub,
        ))

    def list_all(
        self,
        category: str | None = None,
        equipment: str | None = None,
        search: str | None = None,
        muster: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Exercise]:
        q = self._sichtbar(self.db.query(Exercise))
        if category:
            q = q.filter(Exercise.category == category)
        if equipment:
            q = q.filter(Exercise.equipment == equipment)
        if muster:
            q = q.filter(Exercise.muster == muster)
        if search:
            pattern = f"%{search}%"
            q = q.filter(
                or_(
                    Exercise.name.ilike(pattern),
                    Exercise.primary_muscles_json.ilike(pattern),
                    Exercise.secondary_muscles_json.ilike(pattern),
                )
            )
        return q.order_by(Exercise.name).offset(skip).limit(limit).all()

    def list_by_muscle(self, muscle_name: str, category: str | None = None) -> list[tuple[Exercise, str]]:
        """Return exercises that train the given muscle, with 'primary' or 'secondary' tag.

        Sorted: primary first, then secondary, alphabetically within each group.
        """
        q = self._sichtbar(self.db.query(Exercise))
        if category:
            q = q.filter(Exercise.category == category)
        all_exercises = q.order_by(Exercise.name).all()
        results: list[tuple[Exercise, str]] = []
        muscle_lower = muscle_name.lower()

        for ex in all_exercises:
            if any(m.lower() == muscle_lower for m in ex.primary_muscles):
                results.append((ex, "primary"))
            elif any(m.lower() == muscle_lower for m in ex.secondary_muscles):
                results.append((ex, "secondary"))

        # Sort: primary first
        results.sort(key=lambda x: (0 if x[1] == "primary" else 1, x[0].name))
        return results

    def list_by_region(self, region: str, category: str | None = None) -> list[Exercise]:
        """Uebungen einer Koerperregion, nach Anteil sortiert.

        Rechnet seit 2026-09 ueber ``regionenanteile`` statt ueber die alte
        Namensliste. Der Unterschied: die Reihenfolge sagt jetzt etwas aus.
        Vorher kam die Liste alphabetisch, eine Uebung, die die Region nur
        streift, stand also womoeglich vor der, die sie trifft.
        """
        from app.services.anteile import regionenanteile

        q = self._sichtbar(self.db.query(Exercise))
        if category:
            q = q.filter(Exercise.category == category)

        bewertet: list[tuple[float, str, Exercise]] = []
        for ex in q.all():
            anteil = regionenanteile(ex).get(region, 0.0)
            if anteil > 0:
                bewertet.append((anteil, ex.name, ex))
        bewertet.sort(key=lambda t: (-t[0], t[1]))
        return [ex for _anteil, _name, ex in bewertet]

    def nach_muskel(self, muskel: str, category: str | None = None) -> list[Exercise]:
        """Uebungen fuer EINEN Muskel, nach Anteil sortiert.

        ★ Das ist der Fund, der dieses Modul geaendert hat: vorher gab es nur
        ``list_by_region``, und das Koerpermodell bildete jeden angetippten
        Oberschenkelmuskel auf die Region ``quads`` ab. Wer den Vastus
        medialis antippte, bekam die Liste des ganzen Oberschenkels, also
        exakt dieselbe wie beim Antippen des Rectus femoris. Die Feinauswahl
        war da und fuehrte nirgendwo hin.

        Nimmt eine Muskelkennung (``vastus_medialis``) oder einen alten
        Freitextnamen ("Quadrizeps") und loest beides auf.
        """
        from app.services.anteile import anteile
        from app.services.muskulatur import MUSKELN, muskel_aufloesen

        if muskel in MUSKELN:
            gesucht = {muskel}
        else:
            gesucht = set(muskel_aufloesen(muskel))
        if not gesucht:
            return []

        q = self._sichtbar(self.db.query(Exercise))
        if category:
            q = q.filter(Exercise.category == category)

        bewertet: list[tuple[float, str, Exercise]] = []
        for ex in q.all():
            werte = anteile(ex)
            hoechster = max((werte.get(m, 0.0) for m in gesucht), default=0.0)
            if hoechster > 0:
                bewertet.append((hoechster, ex.name, ex))
        bewertet.sort(key=lambda t: (-t[0], t[1]))
        return [ex for _anteil, _name, ex in bewertet]

    def nach_gruppe(self, gruppe: str, category: str | None = None) -> list[Exercise]:
        """Uebungen fuer eine Muskelgruppe, nach Anteil sortiert."""
        from app.services.anteile import gruppenanteile

        q = self._sichtbar(self.db.query(Exercise))
        if category:
            q = q.filter(Exercise.category == category)

        bewertet: list[tuple[float, str, Exercise]] = []
        for ex in q.all():
            anteil = gruppenanteile(ex).get(gruppe, 0.0)
            if anteil > 0:
                bewertet.append((anteil, ex.name, ex))
        bewertet.sort(key=lambda t: (-t[0], t[1]))
        return [ex for _anteil, _name, ex in bewertet]

    def get(self, exercise_id: int) -> Exercise:
        ex = self.db.get(Exercise, exercise_id)
        if not ex or not self._ist_sichtbar(ex):
            raise DomainError("Übung nicht gefunden", {"exercise_id": exercise_id})
        return ex

    def _ist_sichtbar(self, ex: Exercise) -> bool:
        return ex.created_by_sub is None or ex.created_by_sub == self._sub

    def _eigener_eintrag(self, ex: Exercise) -> None:
        """Wirft, wenn der Eintrag nicht dem aktuellen Mandanten gehoert."""
        if ex.created_by_sub is None:
            raise DomainError(
                "Diese Übung gehört zum gemeinsamen Katalog und ist nicht änderbar",
                {"exercise_id": ex.id},
            )
        if ex.created_by_sub != self._sub:
            raise DomainError("Übung nicht gefunden", {"exercise_id": ex.id})

    def create(self, data: ExerciseCreate) -> Exercise:
        # Der Name ist in der Datenbank fuer den ganzen Katalog eindeutig.
        # Deshalb hier ohne Sichtbarkeitsfilter pruefen: sonst laeuft der
        # Aufruf in einen Datenbankfehler statt in eine klare Meldung.
        existing = self.db.query(Exercise).filter(Exercise.name == data.name).first()
        if existing:
            raise DomainError("Übung existiert bereits", {"name": data.name})
        ex = Exercise(
            name=data.name,
            category=data.category,
            equipment=data.equipment,
            is_compound=data.is_compound,
            notes=data.notes,
            # Auch ein leerer Mandant wird gestempelt, nicht auf NULL gesetzt:
            # NULL heisst "gehoert dem gemeinsamen Katalog und ist von
            # niemandem aenderbar". Ein selbst angelegter Eintrag waere damit
            # sofort nach dem Anlegen gesperrt. Leer bleibt leer, so wie
            # app/tenant.py die uebrigen Tabellen stempelt.
            created_by_sub=self._sub,
        )
        ex.primary_muscles = data.primary_muscles
        ex.secondary_muscles = data.secondary_muscles
        self.db.add(ex)
        return ex

    def update(self, exercise_id: int, data: ExerciseUpdate) -> Exercise:
        ex = self.get(exercise_id)
        self._eigener_eintrag(ex)
        if data.name is not None:
            dup = self.db.query(Exercise).filter(
                Exercise.name == data.name, Exercise.id != exercise_id
            ).first()
            if dup:
                raise DomainError("Name bereits vergeben", {"name": data.name})
            ex.name = data.name
        if data.category is not None:
            ex.category = data.category
        if data.equipment is not None:
            ex.equipment = data.equipment
        if data.primary_muscles is not None:
            ex.primary_muscles = data.primary_muscles
        if data.secondary_muscles is not None:
            ex.secondary_muscles = data.secondary_muscles
        if data.is_compound is not None:
            ex.is_compound = data.is_compound
        if data.notes is not None:
            ex.notes = data.notes
        return ex

    def delete(self, exercise_id: int) -> None:
        ex = self.get(exercise_id)
        self._eigener_eintrag(ex)

        # Verwendung ueber ALLE Mandanten pruefen (``skip_tenant``): eine
        # Uebung, die in einem fremden Plan oder Workout haengt, darf nicht
        # verschwinden. Der Fremdschluessel wuerde den Loeschversuch ohnehin
        # mit einem Datenbankfehler beenden, und ein 500er sagt dem Nutzer
        # nicht, was los ist.
        in_workouts = (
            self.db.query(WorkoutSet.id)
            .filter(WorkoutSet.exercise_id == exercise_id)
            .execution_options(skip_tenant=True)
            .first()
        )
        in_plaenen = (
            self.db.query(PlanExercise.id)
            .filter(PlanExercise.exercise_id == exercise_id)
            .execution_options(skip_tenant=True)
            .first()
        )
        if in_workouts or in_plaenen:
            raise DomainError(
                "Übung wird verwendet und kann nicht gelöscht werden. "
                "In der Übungsliste abwählen blendet sie aus, ohne die Historie zu verlieren.",
                {"exercise_id": exercise_id,
                 "in_workouts": bool(in_workouts),
                 "in_plaenen": bool(in_plaenen)},
            )

        self.db.delete(ex)

    # --- Auswahl je Mandant ---

    def auswahl(self, exercise_ids: list[int]) -> dict[int, bool]:
        """Abgewaehlte Uebungen des aktuellen Mandanten. Kein Eintrag = gewaehlt."""
        if not exercise_ids:
            return {}
        zeilen = (
            self.db.query(ExerciseSelection)
            .filter(ExerciseSelection.exercise_id.in_(exercise_ids))
            .all()
        )
        return {z.exercise_id: z.is_selected for z in zeilen}

    def auswahl_setzen(self, exercise_id: int, is_selected: bool) -> Exercise:
        ex = self.get(exercise_id)
        zeile = (
            self.db.query(ExerciseSelection)
            .filter(ExerciseSelection.exercise_id == exercise_id)
            .first()
        )
        if zeile is None:
            # ``owner_sub`` stempelt app/tenant.py beim Schreiben.
            zeile = ExerciseSelection(exercise_id=exercise_id, is_selected=is_selected)
            self.db.add(zeile)
        else:
            zeile.is_selected = is_selected
        return ex
