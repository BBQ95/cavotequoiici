"""Modèles Pydantic pour les réponses des routes scrutins."""

from __future__ import annotations

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# GET /communes/{insee}/scrutins
# ---------------------------------------------------------------------------

class ScrutinInclus(BaseModel):
    """Un scrutin inclus dans la synthèse de la commune."""
    scrutin_id: str
    type: str
    date: str
    poids_relatif: float


class ListeScrutinsResponse(BaseModel):
    """Réponse de GET /communes/{insee}/scrutins."""
    insee: str
    scrutins: list[ScrutinInclus]


# ---------------------------------------------------------------------------
# GET /communes/{insee}/scrutins/{scrutin_id}
# ---------------------------------------------------------------------------

class FamilleVoix(BaseModel):
    """Voix d'une famille politique pour un scrutin."""
    famille: str
    voix: int
    pourcentage: float


class CouleurScrutin(BaseModel):
    """Couleur OKLCH d'un scrutin pour une commune."""
    l: float
    c: float
    h: float


class DetailScrutinResponse(BaseModel):
    """Réponse de GET /communes/{insee}/scrutins/{scrutin_id}."""
    insee: str
    scrutin_id: str
    familles: list[FamilleVoix]
    participation: float
    couleur: CouleurScrutin