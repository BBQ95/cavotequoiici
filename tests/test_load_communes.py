"""Tests des fonctions pures du chargeur de communes (TDD, sans BDD).

L'écriture en base (`upsert_communes`) est testée séparément en intégration (Étape 1.3).
"""

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import MultiPolygon, Polygon

from pipeline.load_communes import (
    normalize_insee,
    to_multipolygon,
    prepare_communes,
    COLONNES_CIBLE,
)


# --- normalize_insee -------------------------------------------------------

@pytest.mark.parametrize(
    "brut, attendu",
    [
        ("01001", "01001"),     # déjà normalisé
        ("1001", "01001"),      # padding zéro à gauche
        (1001, "01001"),        # entier
        (75056, "75056"),       # Paris
        ("97401", "97401"),     # DOM (La Réunion)
        ("2a004", "2A004"),     # Corse : lettre en majuscule
        (" 2B033 ", "2B033"),   # espaces parasites
    ],
)
def test_normalize_insee(brut, attendu):
    assert normalize_insee(brut) == attendu


def test_normalize_insee_refuse_vide():
    for v in (None, "", "   ", float("nan")):
        with pytest.raises(ValueError):
            normalize_insee(v)


# --- to_multipolygon -------------------------------------------------------

def _carre(x=0.0):
    return Polygon([(x, 0), (x + 1, 0), (x + 1, 1), (x, 1)])


def test_to_multipolygon_depuis_polygon():
    g = to_multipolygon(_carre())
    assert isinstance(g, MultiPolygon)
    assert len(g.geoms) == 1


def test_to_multipolygon_conserve_multipolygon():
    mp = MultiPolygon([_carre(0), _carre(2)])
    g = to_multipolygon(mp)
    assert isinstance(g, MultiPolygon)
    assert len(g.geoms) == 2


def test_to_multipolygon_refuse_none():
    with pytest.raises(ValueError):
        to_multipolygon(None)


# --- prepare_communes ------------------------------------------------------

def _gdf_source():
    """Reproduit la structure du GeoJSON Etalab (code/nom/departement/region + extras)."""
    return gpd.GeoDataFrame(
        {
            "code": ["01001", "1002", "2a004"],
            "nom": ["L'Abergement-Clémenciat", "L'Abergement-de-Varey", "Ajaccio"],
            "departement": ["01", "01", "2A"],
            "region": ["84", "84", "94"],
            "epci": ["200069193", "240100883", "249740087"],
            "plm": [None, None, None],
            "geometry": [_carre(0), _carre(2), _carre(4)],
        },
        crs="EPSG:4326",
    )


def test_prepare_communes_colonnes_cible():
    out = prepare_communes(_gdf_source())
    assert list(out.columns) == COLONNES_CIBLE
    assert out.crs == "EPSG:4326"


def test_prepare_communes_normalise_insee():
    out = prepare_communes(_gdf_source())
    assert list(out["code_insee"]) == ["01001", "01002", "2A004"]


def test_prepare_communes_geom_en_multipolygon():
    out = prepare_communes(_gdf_source())
    assert set(out.geometry.geom_type) == {"MultiPolygon"}


def test_prepare_communes_sans_doublon_insee():
    gdf = _gdf_source()
    gdf = gpd.GeoDataFrame(
        pd.concat([gdf, gdf.iloc[[0]]], ignore_index=True), crs="EPSG:4326"
    )  # duplique la 1re commune
    out = prepare_communes(gdf)
    assert out["code_insee"].is_unique


def test_prepare_communes_nom_recherche():
    out = prepare_communes(_gdf_source())
    assert list(out["nom_recherche"]) == [
        "l abergement clemenciat",
        "l abergement de varey",
        "ajaccio",
    ]
