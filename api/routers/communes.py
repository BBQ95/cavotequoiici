"""Routeur communes : recherche, fiche, couleur synthétique, proximité.

Lecture seule sur les tables précalculées (`communes`, `couleurs_ville`).
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text

from api.db import get_conn
from api.schemas.communes import (
    CommuneFiche,
    CommuneProximite,
    CommuneResultat,
    CouleurSynthese,
)
from pipeline.couleur import OKLCH, oklch_to_hex

router = APIRouter(prefix="/communes", tags=["communes"])


def _synthese(row) -> CouleurSynthese:
    """Construit une CouleurSynthese depuis une ligne couleurs_ville."""
    scrutins = row.scrutins_inclus
    if isinstance(scrutins, str):  # JSON sérialisé (selon le driver)
        scrutins = json.loads(scrutins)
    return CouleurSynthese(
        code_insee=row.code_insee,
        l=row.l,
        c=row.c,
        h=row.h,
        hex=oklch_to_hex(OKLCH(L=row.l, C=row.c, H=row.h)),
        participation_mediane=row.participation_mediane,
        scrutins_inclus=[(t, p) for t, p in scrutins],
    )


# --- /search et /proximite AVANT /{insee} (sinon capturés par la route paramétrée) ---


@router.get("/search", response_model=list[CommuneResultat])
def search(
    q: str = Query(min_length=1, description="Début du nom de commune"),
    limite: int = Query(10, ge=1, le=50),
    conn=Depends(get_conn),
):
    """Autocomplétion par nom de commune."""
    rows = conn.execute(
        text(
            "SELECT code_insee, nom, departement FROM communes "
            "WHERE nom ILIKE :q ORDER BY nom LIMIT :n"
        ),
        {"q": f"{q}%", "n": limite},
    ).fetchall()
    return [
        CommuneResultat(code_insee=r.code_insee, nom=r.nom, departement=r.departement)
        for r in rows
    ]


@router.get("/proximite", response_model=list[CommuneProximite])
def proximite(
    lat: float = Query(ge=-90, le=90),
    lon: float = Query(ge=-180, le=180),
    rayon_m: int = Query(10000, ge=1, le=200000),
    conn=Depends(get_conn),
):
    """Communes dont la géométrie est à moins de `rayon_m` mètres du point."""
    rows = conn.execute(
        text(
            "SELECT c.code_insee, c.nom, cv.l, cv.c, cv.h, "
            "ST_Distance(c.geom::geography, ST_MakePoint(:lon, :lat)::geography) AS dist "
            "FROM communes c JOIN couleurs_ville cv ON cv.code_insee = c.code_insee "
            "WHERE ST_DWithin(c.geom::geography, ST_MakePoint(:lon, :lat)::geography, :r) "
            "ORDER BY dist LIMIT 50"
        ),
        {"lat": lat, "lon": lon, "r": rayon_m},
    ).fetchall()
    return [
        CommuneProximite(
            code_insee=r.code_insee,
            nom=r.nom,
            distance_m=round(r.dist, 1),
            hex=oklch_to_hex(OKLCH(L=r.l, C=r.c, H=r.h)),
        )
        for r in rows
    ]


@router.get("/{insee}/couleur", response_model=CouleurSynthese)
def couleur(insee: str, conn=Depends(get_conn)):
    """Couleur synthétique OKLCH + participation d'une commune."""
    row = conn.execute(
        text(
            "SELECT code_insee, l, c, h, participation_mediane, scrutins_inclus "
            "FROM couleurs_ville WHERE code_insee = :x"
        ),
        {"x": insee},
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="commune sans couleur")
    return _synthese(row)


@router.get("/{insee}", response_model=CommuneFiche)
def fiche(insee: str, conn=Depends(get_conn)):
    """Fiche complète : métadonnées de la commune + couleur synthétique."""
    row = conn.execute(
        text(
            "SELECT c.code_insee, c.nom, c.departement, c.region, c.population, "
            "cv.l, cv.c, cv.h, cv.participation_mediane, cv.scrutins_inclus "
            "FROM communes c JOIN couleurs_ville cv ON cv.code_insee = c.code_insee "
            "WHERE c.code_insee = :x"
        ),
        {"x": insee},
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="commune inconnue")
    return CommuneFiche(
        code_insee=row.code_insee,
        nom=row.nom,
        departement=row.departement,
        region=row.region,
        population=row.population,
        couleur=_synthese(row),
    )
