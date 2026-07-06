"""Synchronisation API ↔ pipeline des algos de dominance (sans BDD)."""


def test_algo_api_synchronise_avec_pipeline():
    """Le Literal `Algo` de l'API doit servir tous les algos du pipeline
    (remarque de revue #48) — un 4ᵉ algo pipeline sans mise à jour de l'API
    casserait ici plutôt qu'en production silencieusement."""
    from typing import get_args

    from api.routers.communes import Algo
    from pipeline.couleur import ALGOS

    assert set(get_args(Algo)) == set(ALGOS)
