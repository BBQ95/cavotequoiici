"""Schémas Pydantic des réponses du routeur communes."""

from __future__ import annotations

from pydantic import BaseModel


class CommuneResultat(BaseModel):
    """Élément d'autocomplétion / de recherche."""

    code_insee: str
    nom: str
    departement: str | None = None


class FamilleSynthese(BaseModel):
    """Part synthétique (pondérée) d'une famille politique dans la couleur de la ville."""

    famille: str
    part: float


class CouleurSynthese(BaseModel):
    """Couleur politique synthétique d'une commune."""

    code_insee: str
    l: float
    c: float
    h: float
    hex: str
    participation_mediane: float
    scrutins_inclus: list[tuple[str, float]]
    repartition: list[FamilleSynthese] = []


class CommuneFiche(BaseModel):
    """Fiche complète : métadonnées + couleur synthétique."""

    code_insee: str
    nom: str
    departement: str | None = None
    region: str | None = None
    population: int | None = None
    couleur: CouleurSynthese


class CommuneProximite(BaseModel):
    """Commune voisine d'un point géographique."""

    code_insee: str
    nom: str
    distance_m: float
    hex: str
