"""Welche Koerpermasse es gibt und wie man sie misst.

Eine Liste fuer Web und App: beide holen sie ueber ``GET /api/body/masse``,
damit die Anleitung nicht an zwei Stellen gepflegt wird und auseinanderlaeuft.
Die Reihenfolge ist die des Messdurchgangs, von oben nach unten, und je Seite
erst links, dann rechts, damit man das Massband nicht hin und her legt.
"""
from dataclasses import asdict, dataclass

ALLGEMEIN = (
    "Am besten morgens vor dem Essen, immer an derselben Stelle. Das Maßband "
    "liegt waagerecht und eng an, ohne einzuschneiden. Locker stehen, nicht "
    "anspannen."
)


@dataclass(frozen=True)
class Massdefinition:
    id: str
    name: str
    anleitung: str
    # l | r | m (Mitte, nur einmal)
    seite: str
    # Gruppe fuer die Anzeige: oberkoerper | arme | beine
    bereich: str


_ARM = "Arm locker hängen lassen"
_BEIN = "Aufrecht stehen, Gewicht auf beiden Beinen"

MASSE: tuple[Massdefinition, ...] = (
    Massdefinition("nacken", "Nacken", "Knapp unter dem Kehlkopf waagerecht um den Hals.", "m", "oberkoerper"),
    Massdefinition("schultern", "Schultern", "Arme hängen locker. Um die breiteste Stelle, über beide Schulterknochen.", "m", "oberkoerper"),
    Massdefinition("brust", "Brust", "Unter den Achseln über die breiteste Stelle der Brust. Normal ausatmen, dann ablesen.", "m", "oberkoerper"),
    Massdefinition("bauch", "Bauch", "Auf Höhe des Bauchnabels, entspannt, nach dem Ausatmen.", "m", "oberkoerper"),
    Massdefinition("huefte", "Hüfte", "Füße zusammen. Um die breiteste Stelle des Gesäßes.", "m", "oberkoerper"),
    Massdefinition("oberarm_l", "Oberarm links", f"{_ARM}. In der Mitte zwischen Schulter und Ellbogen.", "l", "arme"),
    Massdefinition("oberarm_r", "Oberarm rechts", f"{_ARM}. In der Mitte zwischen Schulter und Ellbogen.", "r", "arme"),
    Massdefinition("unterarm_l", "Unterarm links", f"{_ARM}. An der dicksten Stelle knapp unter dem Ellbogen.", "l", "arme"),
    Massdefinition("unterarm_r", "Unterarm rechts", f"{_ARM}. An der dicksten Stelle knapp unter dem Ellbogen.", "r", "arme"),
    Massdefinition("oberschenkel_l", "Oberschenkel links", f"{_BEIN}. Eine Handbreit unter dem Schritt, an der dicksten Stelle.", "l", "beine"),
    Massdefinition("oberschenkel_r", "Oberschenkel rechts", f"{_BEIN}. Eine Handbreit unter dem Schritt, an der dicksten Stelle.", "r", "beine"),
    Massdefinition("wade_l", "Wade links", f"{_BEIN}. An der dicksten Stelle der Wade.", "l", "beine"),
    Massdefinition("wade_r", "Wade rechts", f"{_BEIN}. An der dicksten Stelle der Wade.", "r", "beine"),
)
KENNUNGEN = frozenset(m.id for m in MASSE)


def definitionen() -> list[dict]:
    return [asdict(m) for m in MASSE]
