"""Tests du routeur communes (intégration BDD ; ignoré sans DATABASE_URL)."""

import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL non définie (test d'intégration BDD)",
)


def test_search(client):
    r = client.get("/communes/search", params={"q": "Saint-Den"})
    assert r.status_code == 200
    codes = {c["code_insee"] for c in r.json()}
    assert "93066" in codes


def test_couleur(client):
    r = client.get("/communes/93066/couleur")
    assert r.status_code == 200
    body = r.json()
    assert 5 <= body["h"] <= 45          # Saint-Denis → rouge
    assert body["hex"].startswith("#")
    assert body["scrutins_inclus"]


def test_couleur_404(client):
    assert client.get("/communes/00000/couleur").status_code == 404


def test_fiche(client):
    r = client.get("/communes/06088")
    assert r.status_code == 200
    body = r.json()
    assert body["nom"] == "Nice"
    assert 240 <= body["couleur"]["h"] <= 275   # Nice → marine


def test_proximite(client):
    # autour de Nice
    r = client.get("/communes/proximite", params={"lat": 43.70, "lon": 7.27, "rayon_m": 6000})
    assert r.status_code == 200
    items = r.json()
    assert any(i["code_insee"] == "06088" for i in items)
    # triées par distance croissante
    dists = [i["distance_m"] for i in items]
    assert dists == sorted(dists)
