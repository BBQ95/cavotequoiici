"""Tests des fonctions pures du parseur présidentielle 2022 T1 (sans BDD).

L'insertion en base est testée en intégration lors du chargement réel (Étape 2).
"""

import polars as pl
import pytest

from pipeline.ingest.presidentielle_2022 import (
    PANNEAU_NUANCE,
    SCRUTIN_ID,
    agreger_resultats,
    construire_insee,
)
from pipeline.ingest.common import charger_nuances


# --- construire_insee ------------------------------------------------------

@pytest.mark.parametrize(
    "dep, com, attendu",
    [
        ("01", "001", "01001"),        # métropole
        ("2A", "004", "2A004"),         # Corse
        ("2B", "033", "2B033"),
        ("75", "056AR18", "75056"),     # Paris 18e -> commune parente Paris
        ("69", "123AR09", "69123"),     # Lyon 9e  -> Lyon
        ("13", "055AR16", "13055"),     # Marseille 16e -> Marseille
    ],
)
def test_construire_insee(dep, com, attendu):
    assert construire_insee(dep, com) == attendu


# --- mapping panneau -> nuance --------------------------------------------

def test_panneau_nuance_complet():
    # 12 candidats, panneaux 1..12, tous distincts
    assert sorted(PANNEAU_NUANCE) == list(range(1, 13))
    assert len(set(PANNEAU_NUANCE.values())) == 12


def test_chaque_nuance_a_une_famille():
    mapping = charger_nuances(SCRUTIN_ID)
    for nuance in PANNEAU_NUANCE.values():
        assert nuance in mapping, f"nuance {nuance} absente du CSV de familles"


# --- agreger_resultats -----------------------------------------------------

def _source():
    """Mini-jeu façon fichier MI : 2 communes dont Paris en 2 arrondissements."""
    base = {
        "dep_code": [],
        "commune_code": [],
        "cand_num_panneau": [],
        "cand_nb_voix": [],
        "exprimes_nb": [],
        "inscrits_nb": [],
    }

    def add(dep, com, expr, insc, voix_par_panneau):
        for p, v in voix_par_panneau.items():
            base["dep_code"].append(dep)
            base["commune_code"].append(com)
            base["cand_num_panneau"].append(p)
            base["cand_nb_voix"].append(v)
            base["exprimes_nb"].append(expr)
            base["inscrits_nb"].append(insc)

    # commune métropole simple
    add("01", "001", expr=100, insc=120, voix_par_panneau={5: 60, 7: 40})
    # Paris en 2 arrondissements -> doivent fusionner en 75056
    add("75", "056AR01", expr=50, insc=70, voix_par_panneau={5: 10, 7: 40})
    add("75", "056AR02", expr=30, insc=40, voix_par_panneau={5: 20, 7: 10})
    return pl.DataFrame(base)


def test_agreger_resultats_colonnes():
    out = agreger_resultats(_source())
    assert set(out.columns) == {"code_insee", "nuance", "voix", "exprimes", "inscrits"}


def test_agreger_resultats_fusion_arrondissements():
    out = agreger_resultats(_source())
    paris = out.filter(pl.col("code_insee") == "75056")
    # voix RN(5) = 10+20 = 30 ; FI(7) = 40+10 = 50
    voix = {r["nuance"]: r["voix"] for r in paris.to_dicts()}
    assert voix["RN"] == 30
    assert voix["FI"] == 50
    # exprimés/inscrits parent = somme des arrondissements (comptés une fois)
    expr = set(paris["exprimes"].to_list())
    insc = set(paris["inscrits"].to_list())
    assert expr == {80}      # 50 + 30
    assert insc == {110}     # 70 + 40


def test_agreger_resultats_commune_simple():
    out = agreger_resultats(_source())
    com = out.filter(pl.col("code_insee") == "01001")
    voix = {r["nuance"]: r["voix"] for r in com.to_dicts()}
    assert voix == {"RN": 60, "FI": 40}
    assert set(com["exprimes"].to_list()) == {100}
    assert set(com["inscrits"].to_list()) == {120}
