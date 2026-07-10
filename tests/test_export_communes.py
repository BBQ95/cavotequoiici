"""Tests unitaires pour pipeline/export_communes.py — export statique.

TDD strict : tests écrits avant l'implémentation. On couvre la logique pure
(construction des fiches, écriture des JSON, version, nuances, glyphes) ;
la requête PostGIS et l'écriture des ~35 000 fichiers réels sont des effets
de bord vérifiés à l'exécution réelle (`make export-statique`).
"""

import json
from pathlib import Path

import pytest

from pipeline.couleur import ALGOS, OKLCH, oklch_to_hex
from pipeline.export_communes import (
    SCHEMA_VERSION,
    copier_glyphes,
    couleur_synthese,
    ecrire_fiches,
    exporter_nuances,
    fiche_statique,
    meta_version,
)

FONTS_SRC = Path(__file__).resolve().parent.parent / "api" / "fonts"


def _ligne(**overrides):
    """Une ligne type de la jointure communes × couleurs_ville (+ lat/lon)."""
    base = {
        "code_insee": "93066",
        "nom": "Saint-Denis",
        "departement": "Seine-Saint-Denis",
        "region": "Île-de-France",
        "population": 112091,
        "lat": 48.93,
        "lon": 2.35,
        "participation_mediane": 0.5123,
        "scrutins_inclus": [["presidentielle", 1.0], ["europeennes", 0.8]],
        "repartition": [
            {"famille": "gauche", "part": 0.41},
            {"famille": "extreme_gauche", "part": 0.22},
        ],
    }
    base.update(overrides)
    return base


def _lignes_algo(**overrides):
    """couleurs_ville_algo d'une commune : algo → {l, c, h, famille_dominante}."""
    base = {
        "complet": {"l": 0.72, "c": 0.10, "h": 28.8, "famille_dominante": "gauche"},
        "tendance": {"l": 0.70, "c": 0.12, "h": 30.0, "famille_dominante": "gauche"},
        "blocs": {"l": 0.68, "c": 0.14, "h": 25.0, "famille_dominante": "extreme_gauche"},
    }
    base.update(overrides)
    return base


class TestCouleurSynthese:
    def test_hex_depuis_oklch_de_l_algo(self):
        """Le hex servi est exactement l'OKLCH de l'algo converti — même
        source unique (`oklch_to_hex`) que l'endpoint fiche."""
        c = couleur_synthese(_ligne(), "tendance", _lignes_algo()["tendance"])
        assert c.hex == oklch_to_hex(OKLCH(L=0.70, C=0.12, H=30.0))
        assert (c.l, c.c, c.h) == (0.70, 0.12, 30.0)

    def test_algo_et_famille_dominante_de_l_algo(self):
        c = couleur_synthese(_ligne(), "blocs", _lignes_algo()["blocs"])
        assert c.algo == "blocs"
        assert c.famille_dominante == "extreme_gauche"

    def test_scrutins_inclus_et_participation_transmis(self):
        c = couleur_synthese(_ligne(), "complet", _lignes_algo()["complet"])
        assert c.scrutins_inclus == [("presidentielle", 1.0), ("europeennes", 0.8)]
        assert c.participation_mediane == 0.5123

    def test_repartition_en_chaine_json_est_decodee(self):
        """Selon le driver, les colonnes JSON lues via text() brut peuvent
        revenir en chaîne — même tolérance que l'API (pipeline.jsoncol)."""
        row = _ligne(
            repartition='[{"famille": "gauche", "part": 0.41}]',
            scrutins_inclus='[["presidentielle", 1.0]]',
        )
        c = couleur_synthese(row, "complet", _lignes_algo()["complet"])
        assert c.repartition[0].famille == "gauche"
        assert c.scrutins_inclus == [("presidentielle", 1.0)]


class TestFicheStatique:
    def test_metadonnees_transmises(self):
        fiche = fiche_statique(_ligne(), _lignes_algo())
        assert fiche["code_insee"] == "93066"
        assert fiche["nom"] == "Saint-Denis"
        assert fiche["departement"] == "Seine-Saint-Denis"
        assert fiche["region"] == "Île-de-France"
        assert fiche["population"] == 112091
        assert fiche["lat"] == 48.93
        assert fiche["lon"] == 2.35

    def test_une_couleur_par_algo(self):
        fiche = fiche_statique(_ligne(), _lignes_algo())
        assert set(fiche["couleurs"]) == set(ALGOS)

    def test_couleurs_differentes_selon_l_algo(self):
        fiche = fiche_statique(_ligne(), _lignes_algo())
        assert fiche["couleurs"]["tendance"]["hex"] != fiche["couleurs"]["blocs"]["hex"]
        assert fiche["couleurs"]["tendance"]["algo"] == "tendance"

    def test_algo_manquant_echoue_explicitement(self):
        """Une base pas recalculée (couleurs_ville_algo incomplète) doit faire
        échouer l'export, pas produire des fiches silencieusement partielles."""
        lignes = _lignes_algo()
        del lignes["blocs"]
        with pytest.raises(RuntimeError, match="compute_couleurs"):
            fiche_statique(_ligne(), lignes)

    def test_serialisable_en_json(self):
        fiche = fiche_statique(_ligne(), _lignes_algo())
        rechargee = json.loads(json.dumps(fiche, ensure_ascii=False))
        assert rechargee["couleurs"]["complet"]["famille_dominante"] == "gauche"


class TestEcrireFiches:
    def _fiches(self):
        return [
            fiche_statique(_ligne(), _lignes_algo()),
            fiche_statique(_ligne(code_insee="75056", nom="Paris"), _lignes_algo()),
        ]

    def test_un_fichier_json_par_commune(self, tmp_path):
        n = ecrire_fiches(iter(self._fiches()), tmp_path / "communes")
        assert n == 2
        assert (tmp_path / "communes" / "93066.json").exists()
        assert (tmp_path / "communes" / "75056.json").exists()

    def test_contenu_relisible_et_utf8(self, tmp_path):
        ecrire_fiches(iter(self._fiches()), tmp_path / "communes")
        fiche = json.loads((tmp_path / "communes" / "93066.json").read_text("utf-8"))
        assert fiche["region"] == "Île-de-France"
        assert fiche["couleurs"]["complet"]["hex"].startswith("#")

    def test_purge_les_fichiers_obsoletes(self, tmp_path):
        """Une commune disparue entre deux exports ne doit pas laisser un JSON
        périmé (rclone sync le republierait)."""
        dossier = tmp_path / "communes"
        dossier.mkdir(parents=True)
        (dossier / "99999.json").write_text("{}")
        ecrire_fiches(iter(self._fiches()), dossier)
        assert not (dossier / "99999.json").exists()


class TestMetaVersion:
    def test_champs(self):
        meta = meta_version(
            nb_communes=35012,
            scrutins=["europeennes_2024", "presidentielle_2022"],
            genere_le="2026-07-10T12:00:00+00:00",
        )
        assert meta["schema"] == SCHEMA_VERSION
        assert meta["genere_le"] == "2026-07-10T12:00:00+00:00"
        assert meta["nb_communes"] == 35012
        assert meta["algos"] == list(ALGOS)
        assert meta["scrutins"] == ["europeennes_2024", "presidentielle_2022"]


class TestExporterNuances:
    def test_parite_avec_l_endpoint(self, client):
        """nuances.json statique = octet pour octet la réponse de GET /nuances
        (même code de chargement, cf. api.routers.nuances)."""
        assert exporter_nuances() == client.get("/nuances").json()


class TestCopierGlyphes:
    def test_copie_pbf_et_licence(self, tmp_path):
        dest = tmp_path / "fonts"
        n = copier_glyphes(FONTS_SRC, dest)
        assert (dest / "Noto Sans Medium" / "0-255.pbf").exists()
        assert (dest / "Noto Sans Medium" / "256-511.pbf").exists()
        # La licence OFL doit accompagner les glyphes redistribués.
        assert (dest / "OFL.txt").exists()
        assert n == 2

    def test_n_embarque_pas_le_readme(self, tmp_path):
        """Le README du dossier est de la doc dépôt, pas un artefact à servir."""
        dest = tmp_path / "fonts"
        copier_glyphes(FONTS_SRC, dest)
        assert not (dest / "README.md").exists()
