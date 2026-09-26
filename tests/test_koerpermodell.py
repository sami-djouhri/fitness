"""Das 3D-Modell und die Registry muessen dieselben Kennungen benutzen.

★★ Warum dieser Test in Python steht, obwohl er eine TypeScript-Datei liest:
weil der Fehler, den er faengt, sonst gar nicht auffaellt. Steht im Modell
``vastus_medialis`` und in der Registry ``vastus_med``, dann wird dieser
Muskel nie eingefaerbt und ist nie anklickbar. Es gibt keine Fehlermeldung,
keine rote Konsole und keinen fehlgeschlagenen Aufruf: der Muskel ist einfach
grau, und grau heisst in dieser Ansicht "diese Woche nicht trainiert". Der
Fehler sieht also aus wie ein Messergebnis.

Gelesen wird mit einem Muster statt mit einem TypeScript-Parser. Das reicht,
weil die Kennungen im Quelltext als ``id: 'name'`` stehen, und es haelt den
Testlauf frei von einer Node-Abhaengigkeit.
"""

import re
from pathlib import Path

import pytest

from app.data.uebungskatalog import KATALOG, bewegungsmuster
from app.services.muskulatur import MUSKELN

FRONTEND = Path(__file__).resolve().parent.parent / "frontend" / "src" / "koerper"


def _datei(name: str) -> str:
    pfad = FRONTEND / name
    if not pfad.exists():
        pytest.skip(f"{pfad} nicht im Testbild vorhanden")
    return pfad.read_text(encoding="utf-8")


def _modell_muskeln() -> set[str]:
    inhalt = _datei("muskelformen.ts")
    return set(re.findall(r"\{\s*id:\s*'([a-z_]+)'", inhalt))


def _modell_muster() -> set[str]:
    inhalt = _datei("bewegungen.ts")
    block = inhalt.split("export const BEWEGUNGEN", 1)[-1]
    block = block.split("export const LAGEN", 1)[0]
    return set(re.findall(r"^\s{2}([a-z_]+):\s*\{", block, re.MULTILINE))


def test_jeder_modellmuskel_existiert_in_der_registry():
    unbekannt = _modell_muskeln() - set(MUSKELN)
    assert not unbekannt, (
        f"Das Körpermodell kennt Muskeln, die die Registry nicht hat: "
        f"{sorted(unbekannt)}. Sie wären im Modell anklickbar und lieferten "
        f"eine leere Übungsliste.")


def test_jeder_registrymuskel_ist_im_modell_dargestellt():
    """Ausnahme ist ``herz_kreislauf``: das ist kein Muskel und hat keine
    Stelle im Körper."""
    fehlend = set(MUSKELN) - _modell_muskeln() - {"herz_kreislauf"}
    assert not fehlend, (
        f"Diese Muskeln stehen in der Registry, aber nicht im Modell: "
        f"{sorted(fehlend)}. Sie blieben im Bild unsichtbar, obwohl Übungen "
        f"auf sie zeigen.")


def test_jedes_bewegungsmuster_des_katalogs_ist_animiert():
    """★ Sonst steht bei einer Übung eine reglose Figur, ohne Hinweis warum."""
    fehlend = bewegungsmuster() - _modell_muster()
    assert not fehlend, (
        f"Bewegungsmuster ohne Animation: {sorted(fehlend)}")


def test_keine_animation_ohne_uebung():
    """Umgekehrt: eine Animation, die kein Katalogeintrag benutzt, ist toter
    Ballast und faellt beim Aufräumen niemandem auf."""
    ungenutzt = _modell_muster() - bewegungsmuster()
    assert not ungenutzt, f"Animation ohne Übung: {sorted(ungenutzt)}"


def test_jede_uebung_hat_ein_muster():
    ohne = [e.name for e in KATALOG if not e.muster]
    assert not ohne, f"Übungen ohne Bewegungsmuster: {ohne}"
