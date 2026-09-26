"""Das Nutzerprofil: was jemand hat, kann und will.

Genau ein Datensatz je Mandant, angelegt beim ersten Zugriff. Bis dahin
gelten die Vorbelegungen des Modells, und die App verhaelt sich wie vor der
Einfuehrung: sie schlaegt alles vor, was im Katalog steht.

★ ``eingerichtet`` ist das Feld, das den Unterschied traegt zwischen "hat
nichts" und "hat noch nichts gesagt". Ohne diese Unterscheidung waere ein
frisches Konto von einem Konto ohne jedes Geraet nicht zu unterscheiden, und
die App muesste raten, ob sie eine Einrichtung anbieten soll oder nicht.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models import BodyMetric, Nutzerprofil
from app.services.ausruestung import GERAETE, VORLAGEN, geraete_eines_nutzers

# Erfahrungsstufe auf einen Faktor, mit dem die Volumen-Landmarks skaliert
# werden. Ein Einsteiger waechst von deutlich weniger Volumen und vertraegt
# weniger, bevor die Erholung nicht mehr mitkommt.
ERFAHRUNGSFAKTOR: dict[str, float] = {
    "einsteiger": 0.7,
    "fortgeschritten": 1.0,
    "erfahren": 1.2,
}

# Zielsetzung auf den Wiederholungsbereich, in dem vorgeschlagen wird.
ZIELBEREICH: dict[str, tuple[int, int]] = {
    "kraft": (3, 6),
    "hypertrophie": (6, 12),
    "ausdauer": (12, 20),
    "erhaltung": (8, 15),
}


class ProfilService:
    def __init__(self, db: Session):
        self.db = db

    def holen(self) -> Nutzerprofil:
        """Profil des aktuellen Mandanten, angelegt falls es keines gibt.

        Das Anlegen ist kein Schreibvorgang mit Nebenwirkung: der Datensatz
        traegt nur Vorbelegungen und ``eingerichtet=False``. Die Alternative,
        ueberall mit None zu rechnen, verteilt dieselbe Fallunterscheidung
        auf ein Dutzend Stellen.
        """
        profil = self.db.query(Nutzerprofil).first()
        if profil is None:
            profil = Nutzerprofil()
            self.db.add(profil)
            self.db.flush()
        return profil

    def geraete(self) -> frozenset[str]:
        return geraete_eines_nutzers(self.holen().geraete)

    def koerpergewicht(self) -> float | None:
        """Das aktuelle Koerpergewicht, bevorzugt aus der letzten Messung.

        Die Messung schlaegt den Profilwert: sie ist juenger und wurde
        ausdruecklich erfasst. Der Profilwert traegt den Fall, dass jemand nie
        wiegt, aber trotzdem sein Klimmzug-Volumen sehen will.
        """
        letzte = self.db.query(BodyMetric).order_by(desc(BodyMetric.date)).first()
        if letzte and letzte.weight_kg:
            return float(letzte.weight_kg)
        profil = self.holen()
        return float(profil.koerpergewicht_kg) if profil.koerpergewicht_kg else None

    def landmarkfaktor(self) -> float:
        return ERFAHRUNGSFAKTOR.get(self.holen().erfahrung, 1.0)

    def zielbereich(self) -> tuple[int, int]:
        return ZIELBEREICH.get(self.holen().ziel, (6, 12))

    def aktualisieren(self, daten: dict) -> Nutzerprofil:
        profil = self.holen()
        for feld in ("erfahrung", "ziel", "trainingstage_pro_woche",
                     "gewichtsschritt_kg", "kurzhantel_max_kg",
                     "koerpergewicht_kg", "koerpergroesse_cm", "geburtsjahr",
                     "geschlecht"):
            wert = daten.get(feld)
            if wert is not None:
                setattr(profil, feld, wert)

        if daten.get("geraete") is not None:
            # Unbekannte Kennungen fallen weg statt einen Fehler zu werfen:
            # eine aeltere App-Fassung kann ein Geraet schicken, das es
            # inzwischen nicht mehr gibt, und dafuer soll das Speichern des
            # ganzen Profils nicht scheitern.
            profil.geraete = [g for g in daten["geraete"] if g in GERAETE]
            profil.eingerichtet = True
        if daten.get("einschraenkungen") is not None:
            profil.einschraenkungen = list(daten["einschraenkungen"])
        profil.aktualisiert_am = datetime.now(timezone.utc)
        return profil

    def vorlage_anwenden(self, schluessel: str) -> Nutzerprofil:
        vorlage = VORLAGEN.get(schluessel)
        if vorlage is None:
            raise KeyError(schluessel)
        profil = self.holen()
        profil.geraete = list(vorlage["geraete"])
        profil.eingerichtet = True
        profil.aktualisiert_am = datetime.now(timezone.utc)
        return profil
