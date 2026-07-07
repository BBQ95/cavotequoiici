"""Schémas Pydantic des réponses du routeur communes."""

from __future__ import annotations

from pydantic import BaseModel


class CommuneResultat(BaseModel):
    """Élément d'autocomplétion / de recherche.

    `hex` (couleur de synthèse) et `famille` (dominante) sont nuls pour une
    commune sans couleur calculée.
    """

    code_insee: str
    nom: str
    departement: str | None = None
    hex: str | None = None
    famille: str | None = None


class FamilleSynthese(BaseModel):
    """Part synthétique (pondérée) d'une famille politique dans la couleur de la ville."""

    famille: str
    part: float


class CouleurSynthese(BaseModel):
    """Couleur politique synthétique d'une commune.

    `algo` = algo de dominance servi (cf. pipeline.couleur.ALGOS) ;
    `famille_dominante` en dépend — pour « tendance »/« blocs » elle peut
    différer de la première entrée de `repartition` (qui reste le classement
    complet, divers inclus, identique pour tous les algos).
    """

    code_insee: str
    l: float
    c: float
    h: float
    hex: str
    algo: str = "complet"
    famille_dominante: str | None = None
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
    lat: float | None = None
    lon: float | None = None


class CommuneProximite(BaseModel):
    """Commune voisine d'un point géographique."""

    code_insee: str
    nom: str
    distance_m: float
    hex: str
