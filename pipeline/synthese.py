"""Helpers de synthèse pour le calcul des couleurs (Étape 3).

Fonctions pures (testables sans BDD) qui font le pont entre les données ingérées
(`resultats_scrutin` + `scrutins`) et le modèle de couleur (`pipeline.couleur`).
"""

from __future__ import annotations

from datetime import date

# Le module couleur attend des types de scrutin courts (spec Concept §5) ;
# l'ingestion stocke des types longs. Table de passage.
TYPE_VERS_POIDS = {
    "presidentielle_t1": "pres_t1",
    "legislatives_t1": "leg_t1",
    "europeennes": "euro",
    "regionales_t1": "reg_t1",
    "departementales_t1": "dep_t1",
    "municipales_t1": "mun_t1",
}


def age_annees(date_scrutin: date, reference: date) -> float:
    """Ancienneté du scrutin en années (base 365.25 j)."""
    return (reference - date_scrutin).days / 365.25


def parts_familles(voix_par_famille: dict[str, int], exprimes: int) -> dict[str, float]:
    """Part de chaque famille sur les suffrages exprimés.

    Retourne {} si exprimes <= 0 (commune sans suffrages exploitables).
    """
    if exprimes <= 0:
        return {}
    return {f: v / exprimes for f, v in voix_par_famille.items()}


def participation(exprimes: int, inscrits: int) -> float:
    """Taux de participation = exprimés / inscrits (0 si inscrits <= 0)."""
    if inscrits <= 0:
        return 0.0
    return exprimes / inscrits
