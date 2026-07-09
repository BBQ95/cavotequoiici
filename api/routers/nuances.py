"""Routeur nuances : grilles de classification nuance -> famille, par scrutin.

Sérialise les CSV versionnés de pipeline/config/nuances/ (embarqués dans
l'image API, cf. Dockerfile) : aucune dépendance BDD, l'endpoint répond sans
DATABASE_URL. Sert l'écran mobile « D'où viennent les familles ? » (audit
public : source officielle par nuance, mentions du contrôle du Conseil d'État).
"""

from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter

from api.schemas.nuances import NuanceClassee, NuancesResponse, ScrutinNuances
from pipeline.ingest.common import NUANCES_DIR, charger_nuances_completes
from pipeline.synthese import TYPE_VERS_POIDS

router = APIRouter(tags=["nuances"])


@lru_cache(maxsize=1)
def _charger_tout() -> NuancesResponse:
    """Charge toutes les grilles une fois par process (CSV immuables au runtime)."""
    scrutins = []
    for path in NUANCES_DIR.glob("*.csv"):
        scrutin_id = path.stem
        lignes = charger_nuances_completes(scrutin_id)
        scrutins.append(
            ScrutinNuances(
                scrutin_id=scrutin_id,
                # Type court (celui que le mobile sait libeller) ; fallback
                # identité purement défensif pour un futur type hors panier.
                type=TYPE_VERS_POIDS.get(lignes[0]["scrutin_type"],
                                         lignes[0]["scrutin_type"]),
                annee=lignes[0]["annee"],
                date_classification=lignes[0]["date_classification"],
                nuances=[
                    NuanceClassee(
                        nuance=l["nuance"],
                        famille=l["famille"],
                        source=l["source"],
                        statut=l["statut"],
                    )
                    for l in lignes
                ],
            )
        )
    scrutins.sort(key=lambda s: (-s.annee, s.scrutin_id))
    return NuancesResponse(scrutins=scrutins)


@router.get("/nuances", response_model=NuancesResponse)
def liste_nuances() -> NuancesResponse:
    """Grilles officielles nuance -> famille de chaque scrutin ingéré."""
    return _charger_tout()
