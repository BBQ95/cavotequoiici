"""Tests des helpers purs de synthèse (Étape 3)."""

from datetime import date

import pytest

from pipeline.synthese import (
    TYPE_LONG_VERS_COURT,
    age_annees,
    participation,
    parts_familles,
)
from pipeline.couleur import POIDS_TYPE


def test_type_vers_poids_cible_existe():
    # chaque type long mappe vers une clé connue du modèle couleur
    for court in TYPE_LONG_VERS_COURT.values():
        assert court in POIDS_TYPE


def test_type_vers_poids_couvre_le_panier():
    for t in ["presidentielle_t1", "legislatives_t1", "europeennes", "municipales_t1"]:
        assert t in TYPE_LONG_VERS_COURT


def test_age_annees():
    assert age_annees(date(2022, 4, 10), date(2024, 4, 10)) == pytest.approx(2.0, abs=0.01)
    assert age_annees(date(2024, 6, 9), date(2024, 6, 9)) == 0.0


def test_parts_familles():
    parts = parts_familles({"gauche": 60, "droite": 40}, exprimes=100)
    assert parts == {"gauche": 0.6, "droite": 0.4}


def test_parts_familles_exprimes_nul():
    assert parts_familles({"gauche": 0}, exprimes=0) == {}


def test_participation():
    assert participation(80, 100) == 0.8
    assert participation(5, 0) == 0.0
