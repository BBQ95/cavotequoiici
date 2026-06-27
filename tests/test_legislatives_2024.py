"""Tests des fonctions pures du parseur législatives 2024 T1 (sans BDD)."""

import polars as pl
import pytest

from pipeline.ingest.common import charger_nuances
from pipeline.ingest.legislatives_2024 import (
    SCRUTIN_ID,
    agreger_resultats,
    normaliser_insee,
)


def test_normaliser_insee():
    df = pl.DataFrame({"c": ["2068", "65286", "2B007", "zz081"]})
    out = df.select(normaliser_insee(pl.col("c")).alias("i"))["i"].to_list()
    assert out == ["02068", "65286", "2B007", "ZZ081"]


def _source():
    """Mini fichier large : 2 communes, 3 blocs candidat (dont nuances dupliquées)."""
    return pl.DataFrame(
        {
            "Code commune": ["2068", "65286"],
            "Inscrits": ["100", "200"],
            "Exprimés": ["80", "150"],
            "Nuance candidat 1": ["RN", "UG"],
            "Voix 1": ["30", "70"],
            "Nuance candidat 2": ["UG", "RN"],
            "Voix 2": ["25", "50"],
            "Nuance candidat 3": ["RN", ""],   # 2e RN sur la 1re commune ; vide sur la 2e
            "Voix 3": ["10", ""],
        }
    )


def test_agreger_colonnes():
    out = agreger_resultats(_source(), max_candidats=3)
    assert set(out.columns) == {"code_insee", "nuance", "voix", "exprimes", "inscrits"}


def test_agreger_somme_par_nuance():
    out = agreger_resultats(_source(), max_candidats=3)
    com = out.filter(pl.col("code_insee") == "02068")
    voix = {r["nuance"]: r["voix"] for r in com.to_dicts()}
    assert voix == {"RN": 40, "UG": 25}   # RN = 30 + 10
    assert set(com["exprimes"].to_list()) == {80}
    assert set(com["inscrits"].to_list()) == {100}


def test_agreger_ignore_blocs_vides():
    out = agreger_resultats(_source(), max_candidats=3)
    com = out.filter(pl.col("code_insee") == "65286")
    voix = {r["nuance"]: r["voix"] for r in com.to_dicts()}
    assert voix == {"UG": 70, "RN": 50}   # bloc 3 vide ignoré


def test_toutes_nuances_du_csv_ont_une_famille():
    mapping = charger_nuances(SCRUTIN_ID)
    # nuances officielles attendues couvertes
    for n in ["EXG", "FI", "COM", "UG", "SOC", "VEC", "ENS", "LR", "RN", "REC", "UXD", "DSV"]:
        assert n in mapping
