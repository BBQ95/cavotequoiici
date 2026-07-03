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

    def test_repartition_en_chaine_json_est_decodee(self):
        """Selon le driver, la colonne JSON peut revenir en chaîne (lecture via
        text() brut) — la famille dominante doit quand même être extraite."""
        row = _ligne(repartition='[{"famille": "gauche", "part": 0.41}]')
        assert feature_proprietes(row)["famille"] == "gauche"

    def test_famille_hors_palette_retombe_sur_divers(self):
        """Une famille dominante absente de la palette COULEURS ne doit pas
        fuiter vers le client (qui la rendrait en gris) — on transmet `divers`."""
        row = _ligne(repartition=[{"famille": "inconnue", "part": 0.9}])
        assert feature_proprietes(row)["famille"] == "divers"

    def test_element_repartition_malforme_retombe_sur_divers(self):
        row = _ligne(repartition=["pas un dict"])
        assert feature_proprietes(row)["famille"] == "divers"

    def test_participation_nulle_donne_none(self):
        props = feature_proprietes(_ligne(participation_mediane=None))
        assert props["participation"] is None


class TestCouleursParScrutin:
    """Carte v2 : chaque feature porte aussi un hex par scrutin (`hex_<scrutin_id>`),
    calculé depuis couleurs_scrutin, pour que la carte puisse basculer
    synthèse ↔ scrutin sans re-télécharger de données."""

    def test_hex_par_scrutin_precalcule_depuis_oklch(self):
        couleurs = {
            "presidentielle_2022_t1": OKLCH(L=0.65, C=0.12, H=250.0),
            "europeennes_2024": OKLCH(L=0.80, C=0.05, H=100.0),
        }
        props = feature_proprietes(_ligne(), couleurs)
        assert props["hex_presidentielle_2022_t1"] == oklch_to_hex(
            OKLCH(L=0.65, C=0.12, H=250.0)
        )
        assert props["hex_europeennes_2024"] == oklch_to_hex(
            OKLCH(L=0.80, C=0.05, H=100.0)
        )

    def test_scrutin_absent_pas_de_cle(self):
        """Une commune sans couleur pour un scrutin n'émet PAS de clé (feature
        plus légère ; côté client, `coalesce` retombe sur une teinte neutre)."""
        props = feature_proprietes(_ligne(), {"europeennes_2024": OKLCH(L=0.8, C=0.05, H=100.0)})
        assert "hex_presidentielle_2022_t1" not in props

    def test_sans_couleurs_scrutin_proprietes_inchangees(self):
        """Compatibilité : sans le paramètre, seules les propriétés v1 sortent."""
        props = feature_proprietes(_ligne())
        assert set(props) == {"insee", "nom", "hex", "famille", "participation"}

    def test_hex_synthese_non_ecrase(self):
        """La clé `hex` (synthèse) reste celle de couleurs_ville même si des
        couleurs par scrutin sont fournies."""
        attendu = oklch_to_hex(OKLCH(L=0.72, C=0.10, H=28.8))
        props = feature_proprietes(_ligne(), {"europeennes_2024": OKLCH(L=0.8, C=0.05, H=100.0)})
        assert props["hex"] == attendu


class TestFeature:
    def test_feature_geojson_bien_formee(self):
        geom = {"type": "MultiPolygon", "coordinates": [[[[2.35, 48.93]]]]}
        feat = feature(_ligne(), geom)
        assert feat["type"] == "Feature"
        assert feat["geometry"] == geom
        assert feat["properties"]["insee"] == "93066"

    def test_feature_transmet_les_couleurs_par_scrutin(self):
        geom = {"type": "MultiPolygon", "coordinates": [[[[2.35, 48.93]]]]}
        feat = feature(_ligne(), geom, {"europeennes_2024": OKLCH(L=0.8, C=0.05, H=100.0)})
        assert "hex_europeennes_2024" in feat["properties"]
