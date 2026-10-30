"""Den Uebungskatalog aus dem Quelltext in die Datenbank abgleichen.

Laeuft bei jedem Start. Idempotent, und es wird **nichts geloescht**: eine
Uebung, die im Katalog nicht mehr steht, bleibt in der Datenbank stehen, weil
an ihr die Historie und womoeglich ein fremder Trainingsplan haengt. Wer sie
loswerden will, waehlt sie in seiner Uebungsliste ab.

Drei Regeln, die den Abgleich sicher machen:

1. **Selbst angelegte Uebungen werden nie angefasst.** Erkennbar an
   ``created_by_sub IS NOT NULL``. Ein Abgleich, der fremde Eintraege
   ueberschreibt, waere ein Datenverlust ohne Meldung.
2. **Umbenennungen vor dem Anlegen.** Aus "Klimmzüge" wird "Klimmzüge
   Obergriff". Ohne diesen Schritt entstuenden zwei Eintraege: der alte mit
   der ganzen Historie und der neue ohne, und der Nutzer saehe seinen
   Fortschritt verschwinden.
3. **Nur Stammdaten werden nachgezogen**, nicht der Zustand. Was ein Nutzer
   an einer Uebung eingestellt hat, liegt ohnehin in ``exercise_selection``
   und nicht am Katalog.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.data.uebungskatalog import KATALOG, UMBENENNUNGEN, Katalogeintrag
from app.models import Exercise
from app.services.muskulatur import GRUPPEN, MUSKELN

log = logging.getLogger(__name__)

# Ab diesem Anteil gilt ein Muskel als Hauptziel und landet in
# ``primary_muscles``. Die beiden alten Listen werden weiter befuellt, damit
# aeltere Clients und die Freitextsuche nicht ins Leere laufen.
SCHWELLE_PRIMAER = 0.6


def _alte_listen(anteile: dict[str, float]) -> tuple[list[str], list[str]]:
    """Anteile auf die alten primary/secondary-Listen abbilden.

    Ausgegeben werden **Gruppennamen**, nicht Muskelnamen: in der Oberflaeche
    steht dort ein Kurzhinweis, und "Brust" liest sich besser als "Mittlere
    Brust, Untere Brust". Die Feinheit steckt in ``muskel_anteile``.
    """
    primaer: list[str] = []
    sekundaer: list[str] = []
    for mid, anteil in sorted(anteile.items(), key=lambda kv: -kv[1]):
        muskel = MUSKELN.get(mid)
        if not muskel:
            continue
        gruppe = GRUPPEN.get(muskel.gruppe)
        name = gruppe.name if gruppe else muskel.name
        ziel = primaer if anteil >= SCHWELLE_PRIMAER else sekundaer
        if name not in primaer and name not in sekundaer:
            ziel.append(name)
    return primaer, sekundaer


def _uebernehmen(zeile: Exercise, eintrag: Katalogeintrag) -> bool:
    """Stammdaten setzen. Rueckgabe: hat sich etwas geaendert?"""
    primaer, sekundaer = _alte_listen(eintrag.muskeln)
    neu = {
        "category": eintrag.kategorie,
        "equipment": eintrag.equipment,
        "is_compound": eintrag.grunduebung,
        "muster": eintrag.muster,
        "kg_anteil": eintrag.kg_anteil,
        "griff": eintrag.griff or None,
        "reihe": eintrag.reihe or None,
        "stufe": eintrag.stufe,
        "einseitig": eintrag.einseitig,
        "ist_zeit": eintrag.ist_zeit,
        "wdh_min": eintrag.wdh_min,
        "wdh_max": eintrag.wdh_max,
        "pause_s": eintrag.pause_s,
        "ausfuehrung": eintrag.ausfuehrung or None,
        "fehler": eintrag.fehler or None,
    }
    geaendert = False
    for feld, wert in neu.items():
        if getattr(zeile, feld) != wert:
            setattr(zeile, feld, wert)
            geaendert = True

    if zeile.muskel_anteile != eintrag.muskeln:
        zeile.muskel_anteile = dict(eintrag.muskeln)
        geaendert = True
    if zeile.benoetigt != list(eintrag.benoetigt):
        zeile.benoetigt = list(eintrag.benoetigt)
        geaendert = True
    if zeile.primary_muscles != primaer:
        zeile.primary_muscles = primaer
        geaendert = True
    if zeile.secondary_muscles != sekundaer:
        zeile.secondary_muscles = sekundaer
        geaendert = True
    return geaendert


def katalog_einspielen(db: Session) -> dict[str, int]:
    """Abgleich ausfuehren. Gibt die Zaehlstaende zurueck, fuer das Startprotokoll."""
    # Ohne Mandanten-Scoping arbeiten: der Katalog ist geteilt, und dieser
    # Lauf gehoert zu keinem Konto.
    vorhandene = {
        z.name: z
        for z in db.query(Exercise).execution_options(skip_tenant=True).all()
    }

    umbenannt = 0
    for alt, neu in UMBENENNUNGEN.items():
        if alt == neu:
            continue
        zeile = vorhandene.get(alt)
        if zeile is None or neu in vorhandene:
            continue
        if zeile.created_by_sub is not None:
            continue
        zeile.name = neu
        vorhandene[neu] = zeile
        del vorhandene[alt]
        umbenannt += 1

    angelegt = 0
    aktualisiert = 0
    for eintrag in KATALOG:
        zeile = vorhandene.get(eintrag.name)
        if zeile is None:
            zeile = Exercise(name=eintrag.name, created_by_sub=None)
            _uebernehmen(zeile, eintrag)
            db.add(zeile)
            vorhandene[eintrag.name] = zeile
            angelegt += 1
            continue
        if zeile.created_by_sub is not None:
            # Ein Nutzer hat unter diesem Namen etwas Eigenes angelegt. Nicht
            # anfassen, aber melden: sonst fehlt ihm der Katalogeintrag, ohne
            # dass irgendwo steht warum.
            log.info("Katalogeintrag '%s' uebersprungen, existiert als Eigenanlage",
                     eintrag.name)
            continue
        if _uebernehmen(zeile, eintrag):
            aktualisiert += 1

    # Bestandsuebungen ohne Anteile bekommen sie aus ihren alten Listen. Das
    # betrifft Eintraege, die nicht mehr im Katalog stehen, aber in
    # Trainingsplaenen haengen.
    from app.services.anteile import anteile as _anteile
    nachgetragen = 0
    for zeile in vorhandene.values():
        if zeile.muskel_anteile:
            continue
        abgeleitet = _anteile(zeile)
        if abgeleitet:
            zeile.muskel_anteile = abgeleitet
            nachgetragen += 1

    db.commit()
    return {
        "angelegt": angelegt,
        "aktualisiert": aktualisiert,
        "umbenannt": umbenannt,
        "nachgetragen": nachgetragen,
        "gesamt": len(vorhandene),
    }
