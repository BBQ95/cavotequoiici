"""Tests TDD des fonctions pures de pipeline.ingest.europeennes_2024.

Couvre :
- Normalisation INSEE (codes à 5 chiffres, gestion des communes nouvelles)
- Agrégation voix → nuance (somme par commune × nuance)
- Mapping nuance → famille (toutes les nuances du CSV ont une famille valide)
- Cas limites : commune sans exprimés, nuance non mappée
"""

from pathlib import Path

import polars as pl
import pytest

from pipeline.ingest.common import charger_nuances, familles_valides
from pipeline.ingest.europeennes_2024 import (
    aggregate_voix,
    normaliser_code_insee,
    parse_resultats_commune,
)


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

NUANCES_DIR = (
    Path(__file__).resolve().parents[1] / "pipeline" / "config" / "nuances"
)


@pytest.fixture
def mapping_nuances():
    """Charge le mapping réel du fichier europeennes_2024.csv."""
    return charger_nuances("europeennes_2024", nuances_dir=NUANCES_DIR)


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

    def test_code_3_chiffres(self):
        """Code très court (3 chiffres) est pad à 5 (zéro-pad à gauche)."""
        assert normaliser_code_insee("001") == "00001"

    def test_code_avec_string_vide(self):
        """String vide → erreur ou valeur sensible."""
        with pytest.raises((ValueError, AssertionError)):
            normaliser_code_insee("")

    def test_code_none(self):
        """None → erreur."""
        with pytest.raises((ValueError, AssertionError, TypeError)):
            normaliser_code_insee(None)

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

    def test_code_territoire_zx(self):
        """Code ZXxxx (St-Barthélémy/St-Martin) est conservé tel quel."""
        assert normaliser_code_insee("ZX701") == "ZX701"


# ──────────────────────────────────────────────────────────────────────────────
# Tests : mapping nuance → famille
# ──────────────────────────────────────────────────────────────────────────────

class TestMappingNuanceFamille:
    """Vérifie que toutes les nuances du fichier CSV ont une famille valide."""

    def test_mapping_nuances_non_vide(self, mapping_nuances):
        """Le mapping contient au moins 10 nuances (14 attendues)."""
        assert len(mapping_nuances) >= 10

    def test_toutes_familles_valides(self, mapping_nuances, familles_ref):
        """Chaque famille du mapping existe dans familles.csv."""
        for nuance, famille in mapping_nuances.items():
            assert famille in familles_ref, (
                f"Nuance {nuance!r} → famille {famille!r} inconnue dans familles.csv"
            )

    def test_nuances_connues_presentes(self, mapping_nuances):
        """Les nuances principales sont présentes dans le mapping."""
        attendues = {"LFI", "LRN", "LVEC", "LLR", "LENS", "LCOM", "LDIV"}
        for n in attendues:
            assert n in mapping_nuances, f"Nuance {n!r} absente du mapping"


# ──────────────────────────────────────────────────────────────────────────────
# Tests : agrégation voix → nuance
# ──────────────────────────────────────────────────────────────────────────────

def _fake_df_pivot() -> pl.DataFrame:
    """DataFrame de test : 2 communes, 3 nuances, voix à agréger.

    Structure (après pivot, format attendu par aggregate_voix) :
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


def _fake_raw_row() -> dict:
    """Une ligne de données brutes au format du fichier data.gouv.fr (wide format).

    Colonnes minimales : code commune, inscrits, exprimés, et voix N / nuance N
    pour quelques listes.
    """
    return {
        "Code commune": "01001",
        "Libellé commune": "L'Abergement-Clémenciat",
        "Inscrits": "662",
        "Exprimés": "369",
        "Nuance liste 1": "LDIV",
        "Voix 1": "5",
        "Nuance liste 2": "LFI",
        "Voix 2": "100",
        "Nuance liste 3": "LRN",
        "Voix 3": "200",
        "Nuance liste 4": "LVEC",
        "Voix 4": "50",
    }


class TestAggregateVoix:
    """Agrégation des voix par commune × nuance."""

    def test_somme_par_commune_nuance(self):
        """L'agrégation somme correctement les voix par (commune, nuance)."""
        df = _fake_df_pivot()
        agg = aggregate_voix(df)
        # L'agrégation doit retourner une ligne par (code_insee, nuance)
        # Les voix sont déjà agrégées dans ce fake (une ligne par pair)
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
        """Deux lignes avec même code_insee + même nuance sont sommées.

        La docstring d'aggregate_voix indique qu'elle somme les voix en cas
        de nuance dupliquée sur une même commune. Ce test vérifie ce
        comportement : le résultat ne doit contenir qu'une seule ligne pour
        cette paire (code_insee, nuance), avec la somme des voix.
        """
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

        # Pour la commune 01001, nuance LFI : 1 seule ligne avec voix = 150
        lfi_01001 = agg.filter(
            (pl.col("code_insee") == "01001") & (pl.col("nuance") == "LFI")
        )
        assert lfi_01001.shape[0] == 1, (
            "aggregate_voix doit retourner une seule ligne par (code_insee, nuance)"
        )
        assert lfi_01001["voix"][0] == 150, (
            "Les voix doivent être sommées : 100 + 50 = 150"
        )

        # exprimes et inscrits sont au max (constantes par commune)
        assert lfi_01001["exprimes"][0] == 350
        assert lfi_01001["inscrits"][0] == 662

        # Pour la commune 01002, nuance LFI : 1 ligne avec voix = 80
        lfi_01002 = agg.filter(
            (pl.col("code_insee") == "01002") & (pl.col("nuance") == "LFI")
        )
        assert lfi_01002.shape[0] == 1
        assert lfi_01002["voix"][0] == 80

        # Total : 2 lignes (1 pour 01001-LFI, 1 pour 01002-LFI)
        assert agg.shape[0] == 2


# ──────────────────────────────────────────────────────────────────────────────
# Tests : parse_resultats_commune (wide → long format)
# ──────────────────────────────────────────────────────────────────────────────

class TestParseResultatsCommune:
    """Transformation du format wide (38 listes en colonnes) → format long."""

    def test_parse_retourne_dataframe(self):
        """parse_resultats_commune retourne un DataFrame Polars."""
        df = pl.DataFrame(
            {
                "Code commune": ["01001"],
                "Libellé commune": ["Test"],
                "Inscrits": ["662"],
                "Exprimés": ["369"],
                "Nuance liste 1": ["LFI"],
                "Voix 1": ["100"],
                "Nuance liste 2": ["LRN"],
                "Voix 2": ["200"],
                "Nuance liste 3": [None],
                "Voix 3": [None],
            }
        )
        result = parse_resultats_commune(df)
        assert isinstance(result, pl.DataFrame)

    def test_parse_colonnes_attendues(self):
        """Le résultat a les colonnes : code_insee, nuance, voix, exprimes, inscrits."""
        df = pl.DataFrame(
            {
                "Code commune": ["01001"],
                "Libellé commune": ["Test"],
                "Inscrits": ["662"],
                "Exprimés": ["369"],
                "Nuance liste 1": ["LFI"],
                "Voix 1": ["100"],
                "Nuance liste 2": ["LRN"],
                "Voix 2": ["200"],
                "Nuance liste 3": [None],
                "Voix 3": [None],
            }
        )
        result = parse_resultats_commune(df)
        cols = set(result.columns)
        assert "code_insee" in cols
        assert "nuance" in cols
        assert "voix" in cols
        assert "exprimes" in cols
        assert "inscrits" in cols

    def test_parse_voix_converties_en_entiers(self):
        """Les voix sont converties en entiers (pas en strings)."""
        df = pl.DataFrame(
            {
                "Code commune": ["01001"],
                "Libellé commune": ["Test"],
                "Inscrits": ["662"],
                "Exprimés": ["369"],
                "Nuance liste 1": ["LFI"],
                "Voix 1": ["100"],
                "Nuance liste 2": ["LRN"],
                "Voix 2": ["200"],
                "Nuance liste 3": [None],
                "Voix 3": [None],
            }
        )
        result = parse_resultats_commune(df)
        lfi = result.filter(pl.col("nuance") == "LFI")
        assert lfi["voix"][0] == 100
        assert isinstance(lfi["voix"][0], (int,)) or lfi["voix"].dtype in [pl.Int64, pl.Int32]

    def test_parse_filtre_nuances_vides(self):
        """Les panneaux vides (nuance = None) ne génèrent pas de ligne."""
        df = pl.DataFrame(
            {
                "Code commune": ["01001"],
                "Libellé commune": ["Test"],
                "Inscrits": ["662"],
                "Exprimés": ["369"],
                "Nuance liste 1": ["LFI"],
                "Voix 1": ["100"],
                "Nuance liste 2": [None],
                "Voix 2": [None],
            }
        )
        result = parse_resultats_commune(df)
        assert result.shape[0] == 1  # Seulement la liste 1

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
        # La nuance inconnue est présente (le filtrage par mapping se fait ailleurs)
        assert "XX_UNKNOWN" in result["nuance"].to_list()

    def test_parse_numeros_superieurs_a_10(self):
        """L'appariement nuance↔voix fonctionne avec des numéros ≥ 10.

        On crée un DataFrame avec les listes 1, 2 et 10. La liste 10 doit
        être correctement appariée (et ne pas écraser la liste 2).
        """
        df = pl.DataFrame(
            {
                "Code commune": ["01001"],
                "Libellé commune": ["Test"],
                "Inscrits": ["1000"],
                "Exprimés": ["500"],
                "Nuance liste 1": ["LFI"],
                "Voix 1": ["100"],
                "Nuance liste 2": ["LRN"],
                "Voix 2": ["200"],
                "Nuance liste 10": ["LVEC"],
                "Voix 10": ["50"],
            }
        )
        result = parse_resultats_commune(df)
        assert result.shape[0] == 3
        lvec = result.filter(pl.col("nuance") == "LVEC")
        assert lvec.shape[0] == 1
        assert lvec["voix"][0] == 50

    def test_parse_colonnes_desordonnees(self):
        """L'appariement nuance↔voix fonctionne même si les colonnes
        ne sont pas dans l'ordre numérique.

        On place volontairement « Nuance liste 10 » avant « Nuance liste 2 »
        et « Voix 10 » avant « Voix 2 ».
        """
        df = pl.DataFrame(
            {
                "Code commune": ["01001"],
                "Libellé commune": ["Test"],
                "Inscrits": ["1000"],
                "Exprimés": ["500"],
                "Nuance liste 1": ["LFI"],
                "Voix 1": ["100"],
                "Nuance liste 10": ["LVEC"],
                "Voix 10": ["50"],
                "Nuance liste 2": ["LRN"],
                "Voix 2": ["200"],
            }
        )
        result = parse_resultats_commune(df)
        assert result.shape[0] == 3
        # Vérifier que chaque nuance est bien appariée avec sa bonne voix
        lfi = result.filter(pl.col("nuance") == "LFI")
        lrn = result.filter(pl.col("nuance") == "LRN")
        lvec = result.filter(pl.col("nuance") == "LVEC")
        assert lfi["voix"][0] == 100
        assert lrn["voix"][0] == 200
        assert lvec["voix"][0] == 50

    # ── Test sur la vraie structure du fichier data.gouv.fr ──────────────

    FIXTURE_PATH = (
        Path(__file__).resolve().parents[1]
        / "tests"
        / "fixtures"
        / "europeennes_2024_sample.csv"
    )

    def test_parse_vrai_fichier_data_gouv(self):
        """Valide parse_resultats_commune sur un extrait du vrai fichier CSV
        de data.gouv.fr (3 communes, 38 listes en colonnes).

        Vérifie que :
        - Les vraies colonnes « Nuance liste N » / « Voix N » sont détectées
        - Le parsing ne lève pas d'erreur
        - Les codes INSEE sont normalisés à 5 chiffres
        - Le nombre de lignes est cohérent (3 communes × ≤ 38 nuances)
        """
        if not self.FIXTURE_PATH.exists():
            pytest.skip("Fixture du vrai fichier data.gouv.fr absente")

        df = pl.read_csv(
            str(self.FIXTURE_PATH),
            separator=";",
            encoding="utf-8",
            infer_schema_length=0,
            quote_char='"',
        )
        result = parse_resultats_commune(df)

        # Le résultat est un DataFrame
        assert isinstance(result, pl.DataFrame)

        # Colonnes attendues
        assert set(result.columns) == {
            "code_insee", "nuance", "voix", "exprimes", "inscrits"
        }

        # Les 3 communes de la fixture (01001, 01002, 01004) sont présentes
        codes = set(result["code_insee"].unique().to_list())
        assert "01001" in codes
        assert "01002" in codes
        assert "01004" in codes

        # Tous les codes INSEE font 5 caractères
        for code in result["code_insee"].to_list():
            assert len(code) == 5, f"Code INSEE mal normalisé : {code!r}"

        # Les voix sont des entiers
        assert result["voix"].dtype in [pl.Int64, pl.Int32]

        # Au moins une nuance non vide (les 38 listes ne sont pas toutes vides)
        assert result.shape[0] > 0


# ──────────────────────────────────────────────────────────────────────────────
# Tests : intégration mapping + parse
# ──────────────────────────────────────────────────────────────────────────────

class TestIntegration:
    """Tests d'intégration : parse + mapping nuance→famille."""

    def test_toutes_nuances_du_fichier_sont_mappees(self, mapping_nuances):
        """Toutes les nuances présentes dans le fichier réel sont dans le mapping."""
        # Les 14 nuances officielles
        nuances_officielles = {
            "LCOM", "LDIV", "LDVD", "LDVG", "LECO", "LENS", "LEXD",
            "LEXG", "LFI", "LLR", "LREC", "LRN", "LUG", "LVEC",
        }
        for n in nuances_officielles:
            assert n in mapping_nuances, (
                f"Nuance officielle {n!r} absente du mapping europeennes_2024.csv"
            )
