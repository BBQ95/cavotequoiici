"""Tests unitaires pour pipeline/export_tiles.py — Étape 6.1 (tuiles PMTiles).

TDD strict : tests écrits avant l'implémentation. On ne couvre ici que la
logique pure (`feature_proprietes`, `feature`) ; l'export PostGIS et l'appel
tippecanoe sont des effets de bord vérifiés à l'exécution réelle (`make tiles`).
"""

from pathlib import Path

import pytest

from pipeline.couleur import OKLCH, oklch_to_hex
from pipeline.export_tiles import (
    ZOOM_MAX,
    commande_tile_join,
    commande_tippecanoe_communes,
    commande_tippecanoe_etiquettes,
    feature,
    feature_etiquette,
    feature_proprietes,
    minzoom_pour_rang,
    tranche_etiquettes,
)


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


class TestMinzoomPourRang:
    """Étagement des étiquettes de villes par zoom : le rang national (proxy
    MAX(inscrits)) détermine le zoom d'apparition — grandes villes d'abord."""

    @pytest.mark.parametrize(
        ("rang", "minzoom"),
        [
            (1, 4),
            (10, 4),
            (11, 5),
            (40, 5),
            (41, 6),
            (120, 6),
            (121, 7),
            (400, 7),
            (401, 8),
            (1200, 8),
            (1201, 9),
            (4000, 9),
            (4001, 10),
            (12000, 10),
            (12001, 11),
            (35012, 11),
        ],
    )
    def test_bornes_des_seuils(self, rang, minzoom):
        assert minzoom_pour_rang(rang) == minzoom

    def test_jamais_au_dela_de_maxzoom(self):
        """Toute commune, même la dernière, apparaît au plus tard à maxzoom."""
        assert minzoom_pour_rang(10**6) == ZOOM_MAX


class TestFeatureEtiquette:
    """Feature de point d'étiquette (couche `etiquettes` des tuiles).

    PAS de clé `tippecanoe` par feature : avec tippecanoe 2.49.0, un minzoom
    par feature réactive un dot-dropping qui ignore `-r1` (une seule ville
    survivait par tuile, Marseille n'apparaissait jamais). L'étagement par
    zoom se fait par TRANCHES : une archive par zoom (cf. tranche_etiquettes
    + commande_tippecanoe_etiquettes), fusionnées par tile-join.
    """

    GEOM = {"type": "Point", "coordinates": [2.3522, 48.8566]}

    def _ligne(self, **overrides):
        base = {"code_insee": "75056", "nom": "Paris", "rang": 1}
        base.update(overrides)
        return base

    def test_pas_de_cle_tippecanoe(self):
        feat = feature_etiquette(self._ligne(), self.GEOM)
        assert set(feat) == {"type", "geometry", "properties"}

    def test_proprietes_minimales(self):
        """Exactement nom + insee + rang : `insee` pour que le tap sur un nom
        ouvre la fiche, `rang` pour la priorité de collision côté client."""
        props = feature_etiquette(self._ligne(), self.GEOM)["properties"]
        assert props == {"nom": "Paris", "insee": "75056", "rang": 1}

    def test_geometrie_transmise(self):
        feat = feature_etiquette(self._ligne(), self.GEOM)
        assert feat["type"] == "Feature"
        assert feat["geometry"] == self.GEOM


class TestTrancheEtiquettes:
    """La tranche du zoom z contient toutes les étiquettes déjà visibles à z
    (minzoom_pour_rang(rang) <= z) — chaque commune apparaît donc dans toutes
    les tranches de son zoom d'apparition jusqu'à ZOOM_MAX."""

    GEOM = {"type": "Point", "coordinates": [0.0, 0.0]}

    def _feat(self, rang):
        return feature_etiquette({"code_insee": "x", "nom": "X", "rang": rang}, self.GEOM)

    def test_filtre_par_rang(self):
        feats = [self._feat(1), self._feat(11), self._feat(41), self._feat(12001)]
        assert [f["properties"]["rang"] for f in tranche_etiquettes(feats, 4)] == [1]
        assert [f["properties"]["rang"] for f in tranche_etiquettes(feats, 5)] == [1, 11]
        assert [f["properties"]["rang"] for f in tranche_etiquettes(feats, 6)] == [1, 11, 41]

    def test_tranche_maxzoom_contient_tout(self):
        feats = [self._feat(1), self._feat(35012)]
        assert tranche_etiquettes(feats, ZOOM_MAX) == feats


class TestCommandeTippecanoeCommunes:
    """Commande de l'archive des polygones (couche communes seule)."""

    CMD = commande_tippecanoe_communes(Path("/t/communes.geojson"), Path("/t/poly.pmtiles"))

    def test_couche_nommee(self):
        assert "communes:/t/communes.geojson" in self.CMD

    def test_options_existantes_conservees(self):
        for opt in (
            "--force",
            "--minimum-zoom=4",
            "--maximum-zoom=11",
            "--simplification=4",
            "--coalesce-densest-as-needed",
            "--extend-zooms-if-still-dropping",
        ):
            assert opt in self.CMD

    def test_sortie_pmtiles(self):
        i = self.CMD.index("-o")
        assert self.CMD[i + 1] == "/t/poly.pmtiles"


class TestCommandeTippecanoeEtiquettes:
    """Commande d'une tranche d'étiquettes : un seul niveau de zoom, sans
    aucun dropping (-r1) — l'étagement est déjà dans le contenu de la tranche."""

    CMD = commande_tippecanoe_etiquettes(Path("/t/etiq-z6.geojson"), Path("/t/etiq-z6.pmtiles"), 6)

    def test_un_seul_zoom(self):
        assert "--minimum-zoom=6" in self.CMD
        assert "--maximum-zoom=6" in self.CMD

    def test_sans_dropping(self):
        assert "-r1" in self.CMD

    def test_couche_et_sortie(self):
        assert "etiquettes:/t/etiq-z6.geojson" in self.CMD
        i = self.CMD.index("-o")
        assert self.CMD[i + 1] == "/t/etiq-z6.pmtiles"


class TestCommandeTileJoin:
    """Fusion des archives (polygones + une tranche d'étiquettes par zoom)."""

    CMD = commande_tile_join(
        [Path("/t/poly.pmtiles"), Path("/t/etiq-z4.pmtiles")], Path("/t/out.pmtiles")
    )

    def test_sortie_et_entrees_dans_l_ordre(self):
        i = self.CMD.index("-o")
        assert self.CMD[i + 1] == "/t/out.pmtiles"
        assert self.CMD[-2:] == ["/t/poly.pmtiles", "/t/etiq-z4.pmtiles"]

    def test_pas_de_relimitation_de_taille(self):
        """-pk : tile-join a sa propre limite de 500 Ko par tuile — sans -pk il
        re-élaguerait les tuiles z4-z6 déjà passées au coalesce par tippecanoe."""
        assert "-pk" in self.CMD

    def test_force(self):
        assert "--force" in self.CMD


class TestCouleursParAlgo:
    """P1.2 : chaque feature porte aussi un hex par algo de dominance
    (`hex_algo_<algo>`, depuis couleurs_ville_algo) pour que la carte puisse
    basculer d'algo sans re-télécharger. « complet » n'émet pas de clé : c'est
    déjà la clé `hex` (synthèse historique)."""

    def test_hex_par_algo_precalcule_depuis_oklch(self):
        algos = {
            "tendance": OKLCH(L=0.30, C=0.04, H=262.0),
            "blocs": OKLCH(L=0.28, C=0.06, H=262.0),
        }
        props = feature_proprietes(_ligne(), None, algos)
        assert props["hex_algo_tendance"] == oklch_to_hex(OKLCH(L=0.30, C=0.04, H=262.0))
        assert props["hex_algo_blocs"] == oklch_to_hex(OKLCH(L=0.28, C=0.06, H=262.0))

    def test_complet_pas_de_cle_dediee(self):
        """L'algo complet est la clé `hex` : pas de doublon hex_algo_complet,
        même si le chargeur le fournissait par erreur."""
        props = feature_proprietes(_ligne(), None, {"complet": OKLCH(L=0.7, C=0.1, H=28.8)})
        assert "hex_algo_complet" not in props

    def test_commune_sans_algo_pas_de_cle(self):
        props = feature_proprietes(_ligne(), None, None)
        assert not [k for k in props if k.startswith("hex_algo_")]

    def test_hex_synthese_non_ecrase_par_algos(self):
        attendu = oklch_to_hex(OKLCH(L=0.72, C=0.10, H=28.8))
        props = feature_proprietes(_ligne(), None, {"tendance": OKLCH(L=0.3, C=0.04, H=262.0)})
        assert props["hex"] == attendu

    def test_cumul_scrutins_et_algos(self):
        props = feature_proprietes(
            _ligne(),
            {"europeennes_2024": OKLCH(L=0.8, C=0.05, H=100.0)},
            {"tendance": OKLCH(L=0.3, C=0.04, H=262.0)},
        )
        assert "hex_europeennes_2024" in props and "hex_algo_tendance" in props
