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

from app.main import resolve_spa_path


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
