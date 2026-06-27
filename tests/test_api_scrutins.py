"""Tests API des endpoints scrutins (TDD).

Couvre :
  - GET /communes/{insee}/scrutins : 200 sur commune existante, 404 sur absente
  - GET /communes/{insee}/scrutins/{scrutin_id} : 200 sur couple existant,
    404 sur commune absente, 404 sur scrutin absent
  - Structure des réponses
"""

import pytest


# ---------------------------------------------------------------------------
# GET /communes/{insee}/scrutins
# ---------------------------------------------------------------------------

def test_liste_scrutins_saint_denis_200(client):
    """Saint-Denis (93066) existe → 200 + liste des scrutins inclus."""
    r = client.get("/communes/93066/scrutins")
    assert r.status_code == 200
    body = r.json()
    assert "insee" in body
    assert body["insee"] == "93066"
    assert "scrutins" in body
    assert isinstance(body["scrutins"], list)
    assert len(body["scrutins"]) > 0
    for s in body["scrutins"]:
        assert "scrutin_id" in s
        assert "type" in s
        assert "date" in s
        assert "poids_relatif" in s
        assert isinstance(s["poids_relatif"], (int, float))


def test_liste_scrutins_nice_200(client):
    """Nice (06088) existe → 200 + liste des scrutins inclus."""
    r = client.get("/communes/06088/scrutins")
    assert r.status_code == 200
    body = r.json()
    assert body["insee"] == "06088"
    assert isinstance(body["scrutins"], list)
    assert len(body["scrutins"]) > 0


def test_liste_scrutins_404_commune_absente(client):
    """Commune absente de couleurs_ville → 404."""
    r = client.get("/communes/99999/scrutins")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# GET /communes/{insee}/scrutins/{scrutin_id}
# ---------------------------------------------------------------------------

def test_detail_scrutin_saint_denis_euro_200(client):
    """Saint-Denis (93066), europeennes_2024 → 200 + détail par famille."""
    r = client.get("/communes/93066/scrutins/europeennes_2024")
    assert r.status_code == 200
    body = r.json()
    assert body["insee"] == "93066"
    assert body["scrutin_id"] == "europeennes_2024"
    assert "familles" in body
    assert isinstance(body["familles"], list)
    assert len(body["familles"]) > 0
    for f in body["familles"]:
        assert "famille" in f
        assert "voix" in f
        assert "pourcentage" in f
    assert "participation" in body
    assert "couleur" in body
    assert "l" in body["couleur"]
    assert "c" in body["couleur"]
    assert "h" in body["couleur"]


def test_detail_scrutin_nice_pres_200(client):
    """Nice (06088), presidentielle_2022_t1 → 200 + détail par famille."""
    r = client.get("/communes/06088/scrutins/presidentielle_2022_t1")
    assert r.status_code == 200
    body = r.json()
    assert body["insee"] == "06088"
    assert body["scrutin_id"] == "presidentielle_2022_t1"
    assert isinstance(body["familles"], list)
    assert len(body["familles"]) > 0
    assert "participation" in body
    assert "couleur" in body


def test_detail_scrutin_404_commune_absente(client):
    """Commune absente → 404 même si scrutin_id existe."""
    r = client.get("/communes/99999/scrutins/europeennes_2024")
    assert r.status_code == 404


def test_detail_scrutin_404_scrutin_absent(client):
    """Commune existante mais scrutin absent → 404."""
    r = client.get("/communes/93066/scrutins/scrutin_inexistant")
    assert r.status_code == 404


def test_detail_scrutin_pourcentages_coherents(client):
    """La somme des pourcentages par famille doit être ~1.0 (100%)."""
    r = client.get("/communes/93066/scrutins/europeennes_2024")
    assert r.status_code == 200
    body = r.json()
    total = sum(f["pourcentage"] for f in body["familles"])
    assert abs(total - 1.0) < 0.01, f"Somme des pourcentages = {total}, attendu ~1.0"