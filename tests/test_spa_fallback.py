"""Regressionstest fuer den SPA-Fallback (Pfad-Traversal).

Der Fallback lieferte frueher jede Datei aus, die der Prozess lesen kann:
`GET /..%2f..%2fdata%2fapp.db` gab die SQLite-DB heraus, `/etc/passwd` ebenso.
`path` kommt URL-dekodiert an, ein `".." not in path`-Test greift nur den
`..`-Vektor und keine Symlinks.

Der Test geht bewusst ueber `resolve_spa_path` statt ueber einen HTTP-Client:
`app/static` entsteht erst im Image-Build, auf dem Host existiert es nicht,
und ein Client-Test wuerde hier still nichts pruefen.
"""

import pytest

from app.main import ist_api_pfad, resolve_spa_path


@pytest.fixture
def spa_root(tmp_path):
    root = tmp_path / "static"
    (root / "assets").mkdir(parents=True)
    (root / "index.html").write_text("<!doctype html>ok")
    (root / "assets" / "app.js").write_text("console.log(1)")
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "app.db").write_text("SQLite format 3")
    return root


@pytest.mark.parametrize(
    "path",
    ["../data/app.db", "../../etc/passwd", "assets/../../data/app.db", "../main.py"],
)
def test_traversal_wird_abgewiesen(spa_root, path):
    assert resolve_spa_path(spa_root, path) is None


def test_symlink_aus_der_wurzel_heraus_wird_abgewiesen(spa_root, tmp_path):
    (spa_root / "leak.db").symlink_to(tmp_path / "data" / "app.db")
    assert resolve_spa_path(spa_root, "leak.db") is None


def test_echte_datei_wird_weiter_ausgeliefert(spa_root):
    assert resolve_spa_path(spa_root, "index.html") == spa_root / "index.html"
    assert resolve_spa_path(spa_root, "assets/app.js") == spa_root / "assets" / "app.js"


def test_unbekannte_route_faellt_auf_index_zurueck(spa_root):
    assert resolve_spa_path(spa_root, "bestand") is None


@pytest.mark.parametrize("path", ["api", "api/achievements", "api/gibt-es-nicht",
                                  "api/training/jetzt"])
def test_api_pfade_gehoeren_nicht_der_oberflaeche(path):
    """Unbekanntes unter /api muss 404 geben, nicht die App mit 200.

    ⚠️ Bewusst gegen ``ist_api_pfad`` und nicht ueber einen HTTP-Client,
    aus demselben Grund wie oben: der Rueckfall wird nur angelegt, wenn
    ``app/static`` existiert, und im Testlauf ist der Quellbaum gemountet, wo
    es fehlt. Ein Client-Test bekaeme dort 404, weil es die Route gar nicht
    gibt, waere gruen und pruefte nichts. Die Verdrahtung wurde stattdessen
    am laufenden Dienst gemessen (vorher 200 mit HTML, nachher 404).
    """
    assert ist_api_pfad(path)


@pytest.mark.parametrize("path", ["", "zahlen", "workout/12", "apixel",
                                  "assets/app.js", "api-doku"])
def test_die_oberflaeche_faellt_weiter_auf_index_zurueck(path):
    """Gegenprobe. ``apixel`` und ``api-doku`` fangen den Praefix-Fehler ab:
    mit ``path.startswith("api")`` waeren beide faelschlich API-Pfade."""
    assert not ist_api_pfad(path)
