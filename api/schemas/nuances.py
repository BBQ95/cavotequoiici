"""Modèles Pydantic pour GET /nuances (grilles de classification par scrutin)."""

from __future__ import annotations

from pydantic import BaseModel


class NuanceClassee(BaseModel):
    """Classement officiel d'une nuance (code parti/liste) dans une famille."""
    nuance: str
    famille: str
    source: str
    statut: str | None = None  # "provisoire" tant que la circulaire n'est pas publiée


class ScrutinNuances(BaseModel):
    """Grille de nuances d'un scrutin (une ligne par nuance, ordre du CSV)."""
    scrutin_id: str
    type: str  # type court (pres_t1, leg_t1, euro, mun_t1), cf. TYPE_VERS_POIDS
    annee: int
    date_classification: str
    nuances: list[NuanceClassee]


class NuancesResponse(BaseModel):
    """Réponse de GET /nuances : grilles triées par année décroissante."""
    scrutins: list[ScrutinNuances]
