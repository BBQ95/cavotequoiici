"""Tests unitaires pour pipeline/export_tiles.py — Étape 6.1 (tuiles PMTiles).

TDD strict : tests écrits avant l'implémentation. On ne couvre ici que la
logique pure (`feature_proprietes`, `feature`) ; l'export PostGIS et l'appel
tippecanoe sont des effets de bord vérifiés à l'exécution réelle (`make tiles`).
"""

import pytest

from pipeline.couleur import OKLCH, oklch_to_hex
from pipeline.export_tiles import feature_proprietes, feature


def _ligne(**overrides):
    """Une ligne type de la jointure communes × couleurs_ville."""
    base = {
        "code_insee": "93066",
        "nom": "Saint-Denis",
        "l": 0.72,
        "c": 0.10,
        "h": 28.8,
        "participation_mediane": 0.5123,
        "repartition": [
            {"famille": "gauche", "part": 0.41},
            {"famille": "extreme_gauche", "part": 0.22},
        ],
    }
    base.update(overrides)
    return base


class TestFeatureProprietes:
    def test_hex_precalcule_depuis_oklch(self):
        """Le hex des propriétés est exactement l'OKLCH de synthèse converti —
        la carte montre la même couleur que la fiche commune."""
        row = _ligne()
        attendu = oklch_to_hex(OKLCH(L=0.72, C=0.10, H=28.8))
        assert feature_proprietes(row)["hex"] == attendu

    def test_famille_dominante_en_tete_de_repartition(self):
        assert feature_proprietes(_ligne())["famille"] == "gauche"

    def test_insee_et_nom_transmis(self):
        props = feature_proprietes(_ligne())
        assert props["insee"] == "93066"
        assert props["nom"] == "Saint-Denis"

    def test_participation_arrondie_trois_decimales(self):
        assert feature_proprietes(_ligne())["participation"] == 0.512

    def test_repartition_vide_retombe_sur_divers(self):
        props = feature_proprietes(_ligne(repartition=[]))
        assert props["famille"] == "divers"

    def test_repartition_nulle_retombe_sur_divers(self):
        props = feature_proprietes(_ligne(repartition=None))
        assert props["famille"] == "divers"

    def test_participation_nulle_donne_none(self):
        props = feature_proprietes(_ligne(participation_mediane=None))
        assert props["participation"] is None


class TestFeature:
    def test_feature_geojson_bien_formee(self):
        geom = {"type": "MultiPolygon", "coordinates": [[[[2.35, 48.93]]]]}
        feat = feature(_ligne(), geom)
        assert feat["type"] == "Feature"
        assert feat["geometry"] == geom
        assert feat["properties"]["insee"] == "93066"
