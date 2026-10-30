"""Was jetzt trainiert wird, in der Zeit, die da ist.

Die Zusagen, die hier festgehalten werden, sind die des Entscheids vom
2026-09-14: der Kalender plant **wann**, diese App haelt bereit **was**. Zwei
davon sind es wert, dass ein Test sie bewacht, weil ihr Bruch keinen Fehler
erzeugt, sondern eine plausible falsche Antwort:

* Eine geratene Dauer darf nie wie eine gemessene aussehen (``minuten_quelle``).
* Gekuerzt wird an den Saetzen, nicht an den Uebungen, sonst kippt die
  Aufteilung des Plans, um die es beim Plan gerade geht.
"""



from app.services.jetzt import KURZ_MINUTEN, VORGABE_MINUTEN, JetztService


def _plan_mit_uebungen(client, tage: dict[str, list[int]]):
    """Aktiver Plan; je Tag eine Liste von exercise_ids."""
    plan = client.post("/api/plans", json={"name": "PPL", "is_active": True}).json()
    if not plan["is_active"]:
        client.post(f"/api/plans/{plan['id']}/activate")
    ids = {}
    for i, (name, uebungen) in enumerate(tage.items()):
        tag = client.post(
            f"/api/plans/{plan['id']}/days", json={"name": name, "sort_order": i}
        ).json()
        ids[name] = tag["id"]
        for platz, ex_id in enumerate(uebungen):
            # Der Pfad haengt am Tag, nicht am Plan. Die erste Fassung schrieb
            # `/api/plans/{plan}/days/{tag}/exercises` und bekam 404; die Plaene
            # blieben leer, und der Dienst fiel voellig korrekt auf die
            # Bedarfsstrecke zurueck. Ohne das `assert` haette das wie ein
            # Fehler im Dienst ausgesehen.
            antwort = client.post(
                f"/api/plans/days/{tag['id']}/exercises",
                json={"exercise_id": ex_id, "sort_order": platz, "target_sets": 3},
            )
            assert antwort.status_code == 201, antwort.text
    return plan, ids


def _koerpergewichts_uebungen(client, anzahl: int) -> list[int]:
    """Uebungen ohne Geraet, im Test selbst angelegt.

    Bewusst nicht aus dem Katalog gelesen: der wird in der Testdatenbank
    nicht geseedet, ``/api/exercises`` liefert dort eine leere Liste. Die erste
    Fassung dieser Hilfe las von dort und uebersprang daraufhin genau die vier
    Tests, die den Plan und das Kuerzen pruefen, also die einzigen, die etwas
    Nicht-Offensichtliches zusagen. Ein uebersprungener Test sieht im Bericht
    aus wie eine bestandene Zusage.
    """
    kategorien = ["Brust", "Rücken", "Beine", "Schultern", "Arme", "Rumpf"]
    ids = []
    for i in range(anzahl):
        antwort = client.post("/api/exercises", json={
            "name": f"Koerpergewicht {i}",
            "category": kategorien[i % len(kategorien)],
            "equipment": "Körpergewicht",
        })
        assert antwort.status_code == 201, antwort.text
        ids.append(antwort.json()["id"])
    return ids


# ---------------------------------------------------------------------------
# Die Dauer und ihre Herkunft
# ---------------------------------------------------------------------------


def test_ohne_dauer_wird_die_vorgabe_ausgewiesen(client):
    """Der Kern der Trennung: geraten darf nicht wie gemessen aussehen."""
    daten = client.get("/api/training/jetzt").json()
    assert daten["minuten"] == VORGABE_MINUTEN
    assert daten["minuten_quelle"] == "vorgabe"


def test_angefragte_dauer_wird_als_solche_gefuehrt(client):
    daten = client.get("/api/training/jetzt?minuten=30").json()
    assert daten["minuten"] == 30
    assert daten["minuten_quelle"] == "angefragt"


def test_kalender_als_quelle_bleibt_erhalten(client, db_session):
    """Der Weg, den der Kalender nimmt: Dauer aus dem Trainingsblock."""
    ergebnis = JetztService(db_session).training(minuten=75, minuten_quelle="kalender")
    assert ergebnis.minuten == 75
    assert ergebnis.minuten_quelle == "kalender"


def test_ohne_dauer_wird_der_kalender_gefragt(client, db_session):
    """Die Zahl lag im Haus und wurde nie geholt.

    Bis zum 2026-10-24 fragte diese App den Kalender nur nach dem Tagestyp.
    ``minuten_quelle: 'kalender'`` setzte allein der Kalender, wenn er die
    Fitness-App aufrief; wer die App direkt oeffnete, bekam die Vorgabe.
    """
    dienst = JetztService(db_session)
    dienst._kalender = _KalenderMit(50)

    ergebnis = dienst.training()

    assert ergebnis.minuten == 50
    assert ergebnis.minuten_quelle == "kalender"


def test_genannte_dauer_schlaegt_den_kalender(client, db_session):
    """Wer im Gym auf '30 min' tippt, weiss mehr als jede Planung."""
    dienst = JetztService(db_session)
    dienst._kalender = _KalenderMit(50)

    ergebnis = dienst.training(minuten=30)

    assert ergebnis.minuten == 30
    assert ergebnis.minuten_quelle == "angefragt"


def test_ohne_trainingsblock_gilt_die_vorgabe(client, db_session):
    """Ein Tag ohne eingeplante Zeit ist kein Fehler.

    ⚠️ Und die Vorgabe muss weiter als Vorgabe dastehen. Wuerde sie hier als
    ``kalender`` gefuehrt, saehe eine geratene Zahl wie eine geplante aus,
    also genau das, was die Trennung verhindern soll.
    """
    dienst = JetztService(db_session)
    dienst._kalender = _KalenderMit(None)

    ergebnis = dienst.training()

    assert ergebnis.minuten == VORGABE_MINUTEN
    assert ergebnis.minuten_quelle == "vorgabe"


class _KalenderMit:
    """Ein Kalender, der genau eine Antwort kennt."""

    def __init__(self, minuten):
        self._minuten = minuten

    def trainingsminuten(self, tag):
        return self._minuten

    def tagestyp(self, tag):
        return None

    @property
    def available(self):
        return True


def test_sehr_kurze_zeit_wird_benannt(client):
    daten = client.get(f"/api/training/jetzt?minuten={KURZ_MINUTEN - 5}").json()
    assert any("Ergänzung" in h for h in daten["hinweise"])


def test_keine_zeitangabe_im_ergebnis(client):
    """Nirgends ein Zeitpunkt.

    Diese App schlaegt keine Uhrzeit und keinen Wochentag vor. Der Test liest
    die ganze Antwort und besteht darauf, dass keine Terminzusage darin steht.
    """
    daten = client.get("/api/training/jetzt").json()
    # ``warnungen`` gehoert seit dem 2026-10-24 dazu. Als die fehlende
    # Ausruestung aus ``hinweise`` dorthin wanderte, haette dieser Waechter
    # sonst still einen Teil der Antwort aufgehoert zu lesen und waere weiter
    # gruen geblieben.
    text = " ".join(
        [daten["titel"], daten["begruendung"],
         *daten["hinweise"], *daten["warnungen"]]
    ).lower()
    for verboten in ("montag", "dienstag", "mittwoch", "donnerstag", "freitag",
                     "samstag", "sonntag", " uhr"):
        assert verboten not in text, f"Terminzusage in der Antwort: {verboten!r}"


# ---------------------------------------------------------------------------
# Der Plan schlaegt die Rechnung
# ---------------------------------------------------------------------------


def test_ohne_plan_kommt_die_bedarfsstrecke(client):
    daten = client.get("/api/training/jetzt").json()
    assert daten["quelle"] == "bedarf"
    assert daten["plantag"] is None


def test_aktiver_plan_gewinnt(client):
    uebungen = _koerpergewichts_uebungen(client, 3)
    _plan, _ids = _plan_mit_uebungen(client, {"Druecken": uebungen})

    daten = client.get("/api/training/jetzt?minuten=60").json()
    assert daten["quelle"] == "plan"
    assert daten["plantag"] == "Druecken"
    assert daten["uebungen"]


def test_rotation_ohne_wochentag(client):
    """Der naechste Tag ergibt sich aus dem letzten Training, nicht aus dem
    Wochentag. Ein Plan, der 'Montag ist Druecken' sagt, traefe eine Aussage
    ueber den Kalender, und die gehoert seit dem Entscheid dorthin."""
    uebungen = _koerpergewichts_uebungen(client, 4)
    _plan, ids = _plan_mit_uebungen(
        client, {"Druecken": uebungen[:2], "Ziehen": uebungen[2:4]}
    )

    assert client.get("/api/training/jetzt").json()["plantag"] == "Druecken"
    client.post("/api/workouts", json={"plan_day_id": ids["Druecken"]})
    assert client.get("/api/training/jetzt").json()["plantag"] == "Ziehen"


# ---------------------------------------------------------------------------
# Zuschnitt auf die Zeit
# ---------------------------------------------------------------------------


def test_kuerzen_nimmt_saetze_und_nicht_uebungen(client):
    """Die Aufteilung bleibt erhalten.

    Wer eine Einheit kuerzt, indem er die letzten Uebungen streicht, trainiert
    die erste Gruppe dreifach und die letzte gar nicht. Genau dafuer hat man
    keinen Plan gemacht.
    """
    uebungen = _koerpergewichts_uebungen(client, 4)
    _plan, _ids = _plan_mit_uebungen(client, {"Ganzkoerper": uebungen})

    lang = client.get("/api/training/jetzt?minuten=90").json()
    kurz = client.get("/api/training/jetzt?minuten=25").json()

    assert len(kurz["uebungen"]) >= 2, "zu frueh Uebungen gestrichen"
    saetze_lang = sum(u["saetze"] for u in lang["uebungen"])
    saetze_kurz = sum(u["saetze"] for u in kurz["uebungen"])
    assert saetze_kurz < saetze_lang


def test_gekuerzte_uebung_sagt_es_dazu(client):
    uebungen = _koerpergewichts_uebungen(client, 4)
    _plan, _ids = _plan_mit_uebungen(client, {"Ganzkoerper": uebungen})

    kurz = client.get("/api/training/jetzt?minuten=25").json()
    gekuerzt = [u for u in kurz["uebungen"] if u["gekuerzt_von"] is not None]
    if gekuerzt:
        for u in gekuerzt:
            assert u["gekuerzt_von"] > u["saetze"]


def test_geplante_minuten_passen_in_die_zeit(client):
    """Die Einheit darf das Fenster nicht sprengen, sonst ist der Zuschnitt
    Zierde. Eine Minute Toleranz fuer das Runden."""
    for minuten in (25, 45, 90):
        daten = client.get(f"/api/training/jetzt?minuten={minuten}").json()
        assert daten["geplante_minuten"] <= minuten + 1, (
            f"{daten['geplante_minuten']} min geplant fuer ein Fenster von {minuten}"
        )


# ---------------------------------------------------------------------------
# Fehlende Ausruestung
#
# Ein Plan aus der Zeit vor dem Ausruestungsprofil trifft das regelmaessig
# mehrfach. Bis 2026-10-24 stand je betroffener Uebung eine eigene, fast
# gleichlautende Zeile in den Hinweisen; die Startseite zeigte sie nicht an,
# weil sie die Auskunft gar nicht abrief.
# ---------------------------------------------------------------------------


def _uebung_mit_geraet(client, db_session, name, kategorie, benoetigt):
    """Uebung anlegen und ihren Geraetebedarf setzen.

    ``benoetigt`` laesst sich ueber die API nicht setzen: ``ExerciseCreate``
    kennt das Feld nicht, es kommt sonst aus dem Katalog-Seed, der in der
    Testdatenbank fehlt. Die erste Fassung dieser Tests legte die Uebungen nur
    per POST an, womit jede als machbar galt und beide Tests gegen eine leere
    Liste liefen. Der Code war dabei richtig, der Aufbau falsch.
    """
    from app.models import Exercise

    eid = client.post("/api/exercises", json={
        "name": name, "category": kategorie, "equipment": "Langhantel",
    }).json()["id"]
    uebung = db_session.get(Exercise, eid)
    uebung.benoetigt = benoetigt
    db_session.commit()
    return eid


def test_fehlende_geraete_stehen_in_einer_zeile(client, db_session):
    """Drei betroffene Uebungen ergeben einen Hinweis, nicht drei."""
    client.put("/api/profil", json={"geraete": []})
    langhantel = [
        _uebung_mit_geraet(client, db_session, f"Langhantelübung {i}", "Brust",
                           ["langhantel", "bank"])
        for i in range(3)
    ]
    frei = _koerpergewichts_uebungen(client, 1)
    _plan_mit_uebungen(client, {"Push": [*langhantel, *frei]})

    daten = client.get("/api/training/jetzt?minuten=45").json()

    # Seit dem 2026-10-24 in ``warnungen``, weil dazu ein Weg gehoert.
    geraete_zeilen = [w for w in daten["warnungen"] if "Geräte" in w]
    assert len(geraete_zeilen) == 1, f"eine Zeile erwartet, nicht {geraete_zeilen}"
    for i in range(3):
        assert f"Langhantelübung {i}" in geraete_zeilen[0], "alle Namen genannt"
    assert not [h for h in daten["hinweise"] if "Geräte" in h], \
        "nicht zusaetzlich bei den Erklaerungen"


def test_fehlende_geraete_auch_als_liste(client, db_session):
    """Die Oberflaeche braucht sie strukturiert, um einen Weg anzubieten."""
    client.put("/api/profil", json={"geraete": []})
    schwer = _uebung_mit_geraet(client, db_session, "Kreuzheben", "Rücken",
                                ["langhantel"])
    frei = _koerpergewichts_uebungen(client, 2)
    _plan_mit_uebungen(client, {"Pull": [schwer, *frei]})

    daten = client.get("/api/training/jetzt?minuten=45").json()

    assert daten["fehlende_ausruestung"] == ["Kreuzheben"]
    assert all(u["name"] != "Kreuzheben" for u in daten["uebungen"]), \
        "nicht machbare Uebung darf nicht in der Einheit stehen"


def test_ohne_luecke_bleibt_die_liste_leer(client):
    """Gegenprobe: kein Hinweis, wo nichts fehlt."""
    frei = _koerpergewichts_uebungen(client, 3)
    _plan_mit_uebungen(client, {"Ganzkörper": frei})

    daten = client.get("/api/training/jetzt?minuten=45").json()

    assert daten["fehlende_ausruestung"] == []
    assert not [h for h in daten["hinweise"] if "Geräte" in h]
    assert daten["warnungen"] == []


# ---------------------------------------------------------------------------
# Warnung gegen Erklaerung
# ---------------------------------------------------------------------------


def test_erklaerung_steht_nicht_bei_den_warnungen(client, db_session):
    """Owner-Beobachtung am Bild vom 2026-10-24.

    Der Warnkasten der Startseite zog mehr Aufmerksamkeit als die
    Uebungsliste darueber, weil auch "Brust kam diese Woche zu kurz" darin
    stand. Was nur erklaert, gehoert nicht in denselben Topf wie das, wozu ein
    Weg gehoert, sonst entwertet die Erklaerung die Warnung daneben.
    """
    client.put("/api/profil", json={"geraete": []})
    schwer = _uebung_mit_geraet(client, db_session, "Kreuzheben W", "Rücken",
                                ["langhantel"])
    frei = _koerpergewichts_uebungen(client, 2)
    _plan_mit_uebungen(client, {"Pull": [schwer, *frei]})

    daten = client.get("/api/training/jetzt?minuten=90").json()

    assert len(daten["warnungen"]) == 1, "genau die fehlende Ausruestung"
    assert "Geräte" in daten["warnungen"][0]
    # Das 90-Minuten-Fenster laesst Platz, also wird ergaenzt. Diese Erklaerung
    # verlangt nichts und gehoert deshalb auf die andere Seite.
    assert daten["hinweise"], "die Ergaenzung soll weiter erklaert werden"
    for h in daten["hinweise"]:
        assert "Geräte" not in h


def test_jede_uebung_nennt_die_herkunft_ihres_gewichts(client, db_session):
    """Der Kernbefund dieser Runde, am Endpunkt gemessen.

    Vorher trug jede Uebung ``gewicht_kg: null``. Jetzt traegt eine
    Hanteluebung eine geschaetzte Zahl und eine Koerpergewichtsuebung
    weiterhin keine, und beide sagen, warum.
    """
    client.put("/api/profil", json={
        "geraete": ["kurzhantel"], "koerpergewicht_kg": 82.0,
        "erfahrung": "fortgeschritten", "geschlecht": "m",
        "gewichtsschritt_kg": 2.0,
    })
    hantel = client.post("/api/exercises", json={
        "name": "Kurzhantel-Schulterdrücken", "category": "Schultern",
        "equipment": "Kurzhantel",
    }).json()["id"]
    frei = _koerpergewichts_uebungen(client, 1)
    _plan_mit_uebungen(client, {"Push": [hantel, *frei]})

    daten = client.get("/api/training/jetzt?minuten=45").json()
    je_name = {u["name"]: u for u in daten["uebungen"]}

    mit_hantel = je_name["Kurzhantel-Schulterdrücken"]
    assert mit_hantel["gewicht_kg"] is not None
    assert mit_hantel["gewicht_quelle"] == "geschaetzt"

    ohne = je_name["Koerpergewicht 0"]
    assert ohne["gewicht_kg"] is None
    assert ohne["gewicht_quelle"] == "ohne"
