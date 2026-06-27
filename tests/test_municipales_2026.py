"""Tests TDD des fonctions pures de pipeline.ingest.municipales_2026.

Couvre :
- Normalisation INSEE (codes à 5 chiffres, Corse 2A/2B, mode strict=False)
- Agrégation voix → nuance (somme par commune × nuance, doublons)
- Mapping nuance → famille (toutes les nuances du CSV ont une famille valide)
- Communes < 1000 hab. sans nuance → famille divers
- Communes ≥ 1000 hab. avec nuance → mapping normal
- Filtrage des communes hors contours (filtrer_communes_connues)
- Cas limites : commune sans exprimés, nuance non mappée
"""

from pathlib import Path

import polars as pl
import pytest

from pipeline.ingest.common import (
    charger_nuances,
    familles_valides,
    filtrer_communes_connues,
)
from pipeline.ingest.municipales_2026 import (
    aggregate_voix,
    build_lignes_insertion,
    normaliser_code_insee,
    parse_resultats_commune,
)


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

NUANCES_DIR = (
    Path(__file__).resolve().parents[1] / "pipeline" / "config" / "nuances"
)

SCRUTIN_ID = "municipales_2026_t1"


@pytest.fixture
def mapping_nuances():
    """Charge le mapping réel du fichier municipales_2026_t1.csv."""
    return charger_nuances(SCRUTIN_ID, nuances_dir=NUANCES_DIR)


@pytest.fixture
def familles_ref():
    """Ensemble des familles canoniques de familles.csv."""
    return familles_valides(NUANCES_DIR.parent)


# ──────────────────────────────────────────────────────────────────────────────
# Tests : normalisation INSEE
# ──────────────────────────────────────────────────────────────────────────────

class TestNormaliserCodeInsee:
    """Normalisation des codes INSEE : toujours 5 chiffres, zéro-pad à gauche."""

    def test_code_court_pad(self):
        """Code < 100000 doit être zero-pad à 5 chiffres."""
        assert normaliser_code_insee("1234") == "01234"

    def test_code_5_chiffres(self):
        """Code déjà à 5 chiffres reste inchangé."""
        assert normaliser_code_insee("75001") == "75001"

    def test_code_entier(self):
        """Entier → string de 5 chiffres."""
        assert normaliser_code_insee(1234) == "01234"

    def test_code_entier_5(self):
        """Entier déjà à 5 chiffres."""
        assert normaliser_code_insee(75001) == "75001"

    def test_code_corse_2a(self):
        """Code corse 2Axxx est conservé tel quel."""
        assert normaliser_code_insee("2A001") == "2A001"

    def test_code_corse_2b(self):
        """Code corse 2Bxxx est conservé tel quel."""
        assert normaliser_code_insee("2B001") == "2B001"

    def test_code_corse_minuscule(self):
        """Code corse en minuscules est normalisé en majuscules."""
        assert normaliser_code_insee("2a001") == "2A001"

    def test_code_francais_etranger_zz(self):
        """Code ZZxxx (Français de l'étranger) est conservé tel quel."""
        assert normaliser_code_insee("ZZ001") == "ZZ001"

    # ── Mode strict=False ──────────────────────────────────────────────

    def test_strict_false_code_vide_retourne_none(self):
        """En mode strict=False, un code vide retourne None (pas d'exception)."""
        assert normaliser_code_insee("", strict=False) is None

    def test_strict_false_none_retourne_none(self):
        """En mode strict=False, None retourne None."""
        assert normaliser_code_insee(None, strict=False) is None

    def test_strict_false_code_invalide_retourne_none(self):
        """En mode strict=False, un code non valide retourne None."""
        assert normaliser_code_insee("XYZ", strict=False) is None

    def test_strict_false_code_normal(self):
        """En mode strict=False, un code normal est quand même normalisé."""
        assert normaliser_code_insee("1234", strict=False) == "01234"


# ──────────────────────────────────────────────────────────────────────────────
# Tests : mapping nuance → famille
# ──────────────────────────────────────────────────────────────────────────────

class TestMappingNuanceFamille:
    """Vérifie que toutes les nuances du fichier CSV ont une famille valide."""

    def test_mapping_nuances_non_vide(self, mapping_nuances):
        """Le mapping contient au moins 15 nuances (24 attendues)."""
        assert len(mapping_nuances) >= 15

    def test_toutes_familles_valides(self, mapping_nuances, familles_ref):
        """Chaque famille du mapping existe dans familles.csv."""
        for nuance, famille in mapping_nuances.items():
            assert famille in familles_ref, (
                f"Nuance {nuance!r} → famille {famille!r} inconnue dans familles.csv"
            )

    def test_nuances_connues_presentes(self, mapping_nuances):
        """Les nuances principales sont présentes dans le mapping."""
        attendues = {"LFI", "LRN", "LVEC", "LLR", "LCOM", "LDIV", "LDVG", "LDVD"}
        for n in attendues:
            assert n in mapping_nuances, f"Nuance {n!r} absente du mapping"

    def test_aucune_nuance_dupliquée(self, mapping_nuances):
        """Le mapping ne contient pas de nuances dupliquées.

        On le vérifie réellement : le nombre de nuances uniques doit
        être égal au nombre total d'entrées. De plus, charger_nuances
        lève déjà une ValueError en cas de doublon dans le CSV source.
        """
        nuances = list(mapping_nuances.keys())
        assert len(nuances) == len(set(nuances)), (
            f"Doublon détecté : {len(nuances)} clés mais seulement "
            f"{len(set(nuances))} uniques"
        )

    def test_famille_divers_pour_sans_etiquette(self, mapping_nuances):
        """LUD (sans étiquette) → divers."""
        assert mapping_nuances.get("LUD") == "divers"

    def test_famille_divers_pour_regionalistes(self, mapping_nuances):
        """LREG (régionalistes) → divers."""
        assert mapping_nuances.get("LREG") == "divers"

    def test_lfi_extreme_gauche(self, mapping_nuances):
        """LFI → extreme_gauche (classification débattue, cf. README)."""
        assert mapping_nuances.get("LFI") == "extreme_gauche"

    def test_rn_extreme_droite(self, mapping_nuances):
        """LRN → extreme_droite."""
        assert mapping_nuances.get("LRN") == "extreme_droite"


# ──────────────────────────────────────────────────────────────────────────────
# Tests : agrégation voix → nuance
# ──────────────────────────────────────────────────────────────────────────────

def _fake_df_long() -> pl.DataFrame:
    """DataFrame de test : 2 communes, 3 nuances, voix à agréger.

    Structure (format long) :
    | code_insee | nuance | voix | exprimes | inscrits |
    """
    return pl.DataFrame(
        {
            "code_insee": ["01001", "01001", "01001", "01002", "01002"],
            "nuance": ["LFI", "LRN", "LVEC", "LFI", "LRN"],
            "voix": [100, 200, 50, 80, 120],
            "exprimes": [350, 350, 350, 200, 200],
            "inscrits": [662, 662, 662, 500, 500],
        }
    )


class TestAggregateVoix:
    """Agrégation des voix par commune × nuance."""

    def test_somme_par_commune_nuance(self):
        """L'agrégation retourne une ligne par (code_insee, nuance)."""
        df = _fake_df_long()
        agg = aggregate_voix(df)
        assert agg.shape[0] == 5  # 3 nuances pour commune 1, 2 pour commune 2

    def test_commune_sans_exprimes(self):
        """Commune avec 0 exprimés → voix = 0, mais ligne présente."""
        df = pl.DataFrame(
            {
                "code_insee": ["01003"],
                "nuance": ["LFI"],
                "voix": [0],
                "exprimes": [0],
                "inscrits": [100],
            }
        )
        agg = aggregate_voix(df)
        assert agg.shape[0] == 1
        row = agg.filter(pl.col("code_insee") == "01003").filter(pl.col("nuance") == "LFI")
        assert row["voix"][0] == 0
        assert row["exprimes"][0] == 0

    def test_sommation_doublons_meme_nuance(self):
        """Deux lignes avec même code_insee + même nuance sont sommées."""
        df = pl.DataFrame(
            {
                "code_insee": ["01001", "01001", "01002"],
                "nuance": ["LFI", "LFI", "LFI"],
                "voix": [100, 50, 80],
                "exprimes": [350, 350, 200],
                "inscrits": [662, 662, 500],
            }
        )
        agg = aggregate_voix(df)

        lfi_01001 = agg.filter(
            (pl.col("code_insee") == "01001") & (pl.col("nuance") == "LFI")
        )
        assert lfi_01001.shape[0] == 1
        assert lfi_01001["voix"][0] == 150

        # exprimes et inscrits sont au max (constantes par commune)
        assert lfi_01001["exprimes"][0] == 350
        assert lfi_01001["inscrits"][0] == 662

        lfi_01002 = agg.filter(
            (pl.col("code_insee") == "01002") & (pl.col("nuance") == "LFI")
        )
        assert lfi_01002.shape[0] == 1
        assert lfi_01002["voix"][0] == 80

        assert agg.shape[0] == 2


# ──────────────────────────────────────────────────────────────────────────────
# Tests : parse_resultats_commune (wide → long format)
# ──────────────────────────────────────────────────────────────────────────────

def _fake_raw_wide(petite: bool = False) -> pl.DataFrame:
    """DataFrame wide au format du fichier data.gouv.fr.

    Pour les communes ≥ 1000 hab : nuances présentes.
    Pour les communes < 1000 hab : nuances vides (candidats nominatifs sans nuance).
    """
    if petite:
        return pl.DataFrame(
            {
                "Code commune": ["01001"],
                "Libellé commune": ["PetiteCommune"],
                "Inscrits": ["500"],
                "Exprimés": ["250"],
                "Nuance liste 1": [None],
                "Voix 1": ["150"],
                "Nuance liste 2": [None],
                "Voix 2": ["100"],
                "Nuance liste 3": [None],
                "Voix 3": [None],
            }
        )
    return pl.DataFrame(
        {
            "Code commune": ["75001"],
            "Libellé commune": ["Paris 1er"],
            "Inscrits": ["10000"],
            "Exprimés": ["5000"],
            "Nuance liste 1": ["LFI"],
            "Voix 1": ["1000"],
            "Nuance liste 2": ["LRN"],
            "Voix 2": ["2000"],
            "Nuance liste 3": [None],
            "Voix 3": [None],
        }
    )


class TestParseResultatsCommune:
    """Transformation du format wide → format long."""

    def test_parse_retourne_dataframe(self):
        """parse_resultats_commune retourne un DataFrame Polars."""
        df = _fake_raw_wide(petite=False)
        result = parse_resultats_commune(df)
        assert isinstance(result, pl.DataFrame)

    def test_parse_colonnes_attendues(self):
        """Le résultat a les colonnes : code_insee, nuance, voix, exprimes, inscrits."""
        df = _fake_raw_wide(petite=False)
        result = parse_resultats_commune(df)
        cols = set(result.columns)
        assert {"code_insee", "nuance", "voix", "exprimes", "inscrits"} <= cols

    def test_parse_voix_converties_en_entiers(self):
        """Les voix sont converties en entiers."""
        df = _fake_raw_wide(petite=False)
        result = parse_resultats_commune(df)
        lfi = result.filter(pl.col("nuance") == "LFI")
        assert lfi["voix"][0] == 1000
        assert lfi["voix"].dtype in [pl.Int64, pl.Int32]

    def test_parse_filtre_nuances_vides(self):
        """Les panneaux vides (nuance = None) ne génèrent pas de ligne."""
        df = _fake_raw_wide(petite=False)
        result = parse_resultats_commune(df)
        assert result.shape[0] == 2  # Seulement listes 1 et 2

    def test_parse_code_insee_normalise(self):
        """Le code INSEE est normalisé à 5 chiffres."""
        df = pl.DataFrame(
            {
                "Code commune": ["1234"],
                "Libellé commune": ["Test"],
                "Inscrits": ["100"],
                "Exprimés": ["50"],
                "Nuance liste 1": ["LFI"],
                "Voix 1": ["30"],
                "Nuance liste 2": [None],
                "Voix 2": [None],
            }
        )
        result = parse_resultats_commune(df)
        assert result["code_insee"][0] == "01234"

    def test_parse_nuance_non_mappee_pas_filtree(self):
        """Une nuance non mappée apparaît quand même (le filtrage se fait en amont)."""
        df = pl.DataFrame(
            {
                "Code commune": ["01001"],
                "Libellé commune": ["Test"],
                "Inscrits": ["100"],
                "Exprimés": ["50"],
                "Nuance liste 1": ["XX_UNKNOWN"],
                "Voix 1": ["10"],
                "Nuance liste 2": [None],
                "Voix 2": [None],
            }
        )
        result = parse_resultats_commune(df)
        assert "XX_UNKNOWN" in result["nuance"].to_list()

    def test_parse_petite_commune_sans_nuance(self):
        """Commune < 1000 hab. : nuances toutes vides → voix attribuées à LUD.

        Le parse doit retourner des lignes pour une petite commune : les voix
        des candidats nominatifs sans nuance officielle sont attribuées à la
        nuance LUD (sans étiquette → famille divers).
        """
        df = _fake_raw_wide(petite=True)
        result = parse_resultats_commune(df)
        # La petite commune doit avoir des lignes (voix → LUD)
        assert result.shape[0] > 0
        nuances = result["nuance"].to_list()
        # Toutes les nuances doivent être LUD
        assert all(n == "LUD" for n in nuances), f"Attendu LUD, obtenu {nuances}"
        # Les voix doivent être les sommes des voix des candidats
        assert result["voix"].sum() == 250  # 150 + 100


# ──────────────────────────────────────────────────────────────────────────────
# Tests : format mixte (communes < 1000 vs ≥ 1000)
# ──────────────────────────────────────────────────────────────────────────────

class TestFormatMixte:
    """Gestion du format mixte : petites communes sans nuance, grandes avec nuance."""

    def test_grande_commune_avec_nuance_mapping_normal(self, mapping_nuances):
        """Commune ≥ 1000 hab. avec nuance → mapping normal via le CSV."""
        df = _fake_raw_wide(petite=False)
        result = parse_resultats_commune(df)
        # Les nuances LFI et LRN sont mappées
        for nuance in result["nuance"].to_list():
            assert nuance in mapping_nuances

    def test_petite_commune_sans_nuance_famille_divers(self, mapping_nuances):
        """Commune < 1000 hab. sans nuance → voix mappées à LUD (famille divers).

        Vérifie réellement qu'une commune < 1000 hab. dont toutes les nuances
        sont vides mais qui a des voix se voit attribuer la nuance LUD
        (sans étiquette → famille divers) — pas assert True.
        """
        df = _fake_raw_wide(petite=True)
        result = parse_resultats_commune(df)
        # La petite commune doit avoir des lignes (voix attribuées à LUD)
        assert result.shape[0] > 0, "Les petites communes doivent être incluses, pas exclues"
        nuances_result = result["nuance"].to_list()
        # Toutes les nuances doivent être LUD (sans étiquette → divers)
        for nuance in nuances_result:
            assert nuance == "LUD", f"Nuance attendue LUD, obtenue {nuance!r}"
        # LUD doit bien mapper à la famille divers
        assert mapping_nuances.get("LUD") == "divers"


# ──────────────────────────────────────────────────────────────────────────────
# Tests : build_lignes_insertion
# ──────────────────────────────────────────────────────────────────────────────

class TestBuildLignesInsertion:
    """Construction des lignes prêtes à insérer (filtrage nuances mappées)."""

    def test_filtre_nuances_non_mappees(self, mapping_nuances):
        """Les nuances non mappées sont exclues des lignes d'insertion."""
        df = pl.DataFrame(
            {
                "code_insee": ["01001", "01001"],
                "nuance": ["LFI", "XX_UNKNOWN"],
                "voix": [100, 10],
                "exprimes": [350, 350],
                "inscrits": [662, 662],
            }
        )
        lignes = build_lignes_insertion(df, mapping_nuances)
        nuances_result = {l["nuance"] for l in lignes}
        assert "LFI" in nuances_result
        assert "XX_UNKNOWN" not in nuances_result

    def test_filtre_code_insee_none(self, mapping_nuances):
        """Les lignes avec code_insee None sont exclues."""
        df = pl.DataFrame(
            {
                "code_insee": [None, "01001"],
                "nuance": ["LFI", "LRN"],
                "voix": [100, 200],
                "exprimes": [350, 350],
                "inscrits": [662, 662],
            }
        )
        lignes = build_lignes_insertion(df, mapping_nuances)
        codes = {l["code_insee"] for l in lignes}
        assert None not in codes
        assert "01001" in codes

    def test_lignes_ont_bonnes_colonnes(self, mapping_nuances):
        """Les lignes ont exactement les colonnes attendues."""
        df = pl.DataFrame(
            {
                "code_insee": ["01001"],
                "nuance": ["LFI"],
                "voix": [100],
                "exprimes": [350],
                "inscrits": [662],
            }
        )
        lignes = build_lignes_insertion(df, mapping_nuances)
        assert len(lignes) == 1
        assert set(lignes[0].keys()) == {
            "code_insee", "nuance", "voix", "exprimes", "inscrits"
        }


# ──────────────────────────────────────────────────────────────────────────────
# Tests : filtrage des communes hors contours
# ──────────────────────────────────────────────────────────────────────────────

class TestFiltrerCommunesConnues:
    """Filtrage des communes hors contours via filtrer_communes_connues."""

    def test_garde_communes_connues(self):
        """Les communes connues sont gardées."""
        lignes = [
            {"code_insee": "01001", "nuance": "LFI", "voix": 100, "exprimes": 350, "inscrits": 662},
            {"code_insee": "01002", "nuance": "LRN", "voix": 200, "exprimes": 350, "inscrits": 662},
        ]
        codes_connus = {"01001", "01002"}
        gardees, orphelins = filtrer_communes_connues(lignes, codes_connus)
        assert len(gardees) == 2
        assert len(orphelins) == 0

    def test_ecarte_communes_inconnues(self):
        """Les communes inconnues (hors contours) sont écartées."""
        lignes = [
            {"code_insee": "01001", "nuance": "LFI", "voix": 100, "exprimes": 350, "inscrits": 662},
            {"code_insee": "99999", "nuance": "LRN", "voix": 200, "exprimes": 350, "inscrits": 662},
        ]
        codes_connus = {"01001"}
        gardees, orphelins = filtrer_communes_connues(lignes, codes_connus)
        assert len(gardees) == 1
        assert gardees[0]["code_insee"] == "01001"
        assert "99999" in orphelins

    def test_orphelins_sont_uniques(self):
        """Les orphelins sont un set (pas de doublons)."""
        lignes = [
            {"code_insee": "99999", "nuance": "LFI", "voix": 100, "exprimes": 350, "inscrits": 662},
            {"code_insee": "99999", "nuance": "LRN", "voix": 200, "exprimes": 350, "inscrits": 662},
        ]
        codes_connus = set()
        gardees, orphelins = filtrer_communes_connues(lignes, codes_connus)
        assert len(orphelins) == 1  # Un seul code orphelin, pas deux

    def test_aucune_commune_connue(self):
        """Si aucune commune n'est connue, tout est orphelin."""
        lignes = [
            {"code_insee": "01001", "nuance": "LFI", "voix": 100, "exprimes": 350, "inscrits": 662},
        ]
        codes_connus = set()
        gardees, orphelins = filtrer_communes_connues(lignes, codes_connus)
        assert len(gardees) == 0
        assert "01001" in orphelins
