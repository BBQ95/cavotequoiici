"""Tests de la normalisation des noms de communes pour la recherche (TDD, sans BDD)."""

import pytest

from pipeline.normalisation import normaliser_nom


@pytest.mark.parametrize(
    "brut, attendu",
    [
        ("Nîmes", "nimes"),                 # accent circonflexe (cas rapporté : « nim »)
        ("NÎMES", "nimes"),                 # casse + accent
        ("Orléans", "orleans"),             # accent aigu
        ("Besançon", "besancon"),           # cédille
        ("Sète", "sete"),                   # accent grave
        ("Haüy", "hauy"),                   # tréma
        ("Œting", "oeting"),                # ligature œ (translate simple ne suffit pas)
        ("Saint-Denis", "saint denis"),     # tiret → espace (« saint denis » doit matcher)
        ("L'Île-Rousse", "l ile rousse"),   # apostrophe droite + tiret + accent
        ("L’Haÿ-les-Roses", "l hay les roses"),  # apostrophe typographique
        ("  Le   Havre ", "le havre"),      # espaces multiples / parasites
        ("Ay", "ay"),                       # nom court sans transformation
    ],
)
def test_normaliser_nom(brut, attendu):
    assert normaliser_nom(brut) == attendu


def test_normaliser_nom_idempotent():
    """Appliquer deux fois ne change rien (stocké et requête restent alignés)."""
    for nom in ("Nîmes", "L'Île-Rousse", "saint denis"):
        assert normaliser_nom(normaliser_nom(nom)) == normaliser_nom(nom)
