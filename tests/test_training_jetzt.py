"""Was jetzt trainiert wird, in der Zeit, die da ist.

Die Zusagen, die hier festgehalten werden, sind die des Owner-Entscheids vom
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
            # ★ Der Pfad haengt am Tag, nicht am Plan. Die erste Fassung schrieb
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

    ★ Bewusst nicht aus dem Katalog gelesen: der wird in der Testdatenbank
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
    """★ Der Kern der Trennung: geraten darf nicht wie gemessen aussehen."""
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


def test_sehr_kurze_zeit_wird_benannt(client):
    daten = client.get(f"/api/training/jetzt?minuten={KURZ_MINUTEN - 5}").json()
    assert any("Ergänzung" in h for h in daten["hinweise"])


def test_keine_zeitangabe_im_ergebnis(client):
    """★★ Nirgends ein Zeitpunkt.

    Diese App schlaegt keine Uhrzeit und keinen Wochentag vor. Der Test liest
    die ganze Antwort und besteht darauf, dass keine Terminzusage darin steht.
    """
    daten = client.get("/api/training/jetzt").json()
    text = " ".join(
        [daten["titel"], daten["begruendung"], *daten["hinweise"]]
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
    """★ Der naechste Tag ergibt sich aus dem letzten Training, nicht aus dem
    Wochentag. Ein Plan, der 'Montag ist Druecken' sagt, traefe eine Aussage
    ueber den Kalender, und die gehoert seit dem Owner-Entscheid dorthin."""
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
    """★★ Die Aufteilung bleibt erhalten.

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
