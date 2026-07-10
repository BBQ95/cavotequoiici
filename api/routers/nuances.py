"""Routeur nuances : grilles de classification nuance -> famille, par scrutin.

Sérialise les CSV versionnés de pipeline/config/nuances/ (embarqués dans
l'image API, cf. Dockerfile) : aucune dépendance BDD, l'endpoint répond sans
DATABASE_URL. Sert l'écran mobile « D'où viennent les familles ? » (audit
public : source officielle par nuance, mentions du contrôle du Conseil d'État).
"""

from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter

from pipeline.export_communes import _charger_toutes_nuances
from pipeline.schemas.nuances import NuancesResponse

router = APIRouter(tags=["nuances"])


@lru_cache(maxsize=1)
def _charger_tout() -> NuancesResponse:
    """Cache par process : la logique vit dans pipeline.export_communes
    (source unique avec nuances.json de l'export statique)."""
    return _charger_toutes_nuances()


@router.get("/nuances", response_model=NuancesResponse)
def liste_nuances() -> NuancesResponse:
    """Grilles officielles nuance -> famille de chaque scrutin ingéré."""
    return _charger_tout()
