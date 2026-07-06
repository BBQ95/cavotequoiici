"""Routeur communes : recherche, fiche, couleur synthétique, proximité.

Lecture seule sur les tables précalculées (`communes`, `couleurs_ville`).
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text

from api.db import get_conn
from api.schemas.communes import (
    CommuneFiche,
    CommuneProximite,
    CommuneResultat,
    CouleurSynthese,
    FamilleSynthese,
)
from pipeline.couleur import OKLCH, oklch_to_hex
from pipeline.jsoncol import decode_json_col
from pipeline.normalisation import normaliser_nom

router = APIRouter(prefix="/communes", tags=["communes"])

# Algo de dominance servi (cf. pipeline.couleur.ALGOS). Le défaut `complet`
# préserve le comportement historique pour les clients existants ; l'app
# mobile demande explicitement sa préférence (défaut produit : « tendance »).
Algo = Literal["complet", "tendance", "blocs"]


def _json_col(valeur):
    """Décode une colonne JSON qui peut arriver en str (selon le driver)."""
    return decode_json_col(valeur)


def _synthese(row, algo: str = "complet") -> CouleurSynthese:
    """Construit une CouleurSynthese depuis une ligne couleurs_ville
    (LEFT JOIN couleurs_ville_algo : colonnes al/ac/ah/afam optionnelles).

    Pour `complet`, retombe sur les colonnes de couleurs_ville si la table
    des algos n'est pas peuplée (base d'avant la migration 0004, non
    recalculée) ; pour les autres algos, l'absence de ligne est une 404
    explicite plutôt qu'une couleur silencieusement fausse.
    """
    al = getattr(row, "al", None)
    if al is not None:
        l, c, h = row.al, row.ac, row.ah
        famille = row.afam
    elif algo == "complet":
        l, c, h = row.l, row.c, row.h
        repartition_brute = _json_col(getattr(row, "repartition", None)) or []
        famille = repartition_brute[0]["famille"] if repartition_brute else None
    else:
        raise HTTPException(
            status_code=404,
            detail=f"couleur non calculée pour l'algo {algo} (relancer compute_couleurs)",
        )
    scrutins = _json_col(row.scrutins_inclus)
    repartition = _json_col(getattr(row, "repartition", None)) or []
    return CouleurSynthese(
        code_insee=row.code_insee,
        l=l,
        c=c,
        h=h,
        hex=oklch_to_hex(OKLCH(L=l, C=c, H=h)),
        algo=algo,
        famille_dominante=famille,
        participation_mediane=row.participation_mediane,
        scrutins_inclus=[(t, p) for t, p in scrutins],
        repartition=[
            FamilleSynthese(famille=e["famille"], part=e["part"]) for e in repartition
        ],
    )


# --- /search et /proximite AVANT /{insee} (sinon capturés par la route paramétrée) ---


def _echapper_like(s: str) -> str:
    """Neutralise les métacaractères LIKE d'une saisie utilisateur."""
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@router.get("/search", response_model=list[CommuneResultat])
def search(
    q: str = Query(min_length=1, description="Nom (ou partie du nom) de commune"),
    limite: int = Query(10, ge=1, le=50),
    algo: Algo = Query("complet"),
    conn=Depends(get_conn),
):
    """Autocomplétion par nom, insensible aux accents et à la casse.

    Matche en préfixe ou en milieu de nom sur `nom_recherche` (normalisé comme
    la saisie : « nim » → Nîmes, « denis » → Saint-Denis) ; les préfixes sortent
    en premier. Chaque résultat porte la couleur de synthèse (pastille) et la
    famille dominante quand elles existent, selon l'`algo` demandé.
    """
    qn = _echapper_like(normaliser_nom(q))
    if not qn:
        return []
    rows = conn.execute(
        text(
            "SELECT c.code_insee, c.nom, c.departement, "
            "cv.l, cv.c, cv.h, cv.repartition, "
            "cva.l AS al, cva.c AS ac, cva.h AS ah, "
            "cva.famille_dominante AS afam "
            "FROM communes c "
            "LEFT JOIN couleurs_ville cv ON cv.code_insee = c.code_insee "
            "LEFT JOIN couleurs_ville_algo cva ON cva.code_insee = c.code_insee "
            "AND cva.algo = :algo "
            "WHERE c.nom_recherche LIKE :prefixe ESCAPE '\\' "
            "OR c.nom_recherche LIKE :infixe ESCAPE '\\' "
            "ORDER BY (c.nom_recherche LIKE :prefixe ESCAPE '\\') DESC, c.nom "
            "LIMIT :n"
        ),
        {"prefixe": f"{qn}%", "infixe": f"%{qn}%", "n": limite, "algo": algo},
    ).fetchall()
    resultats = []
    for r in rows:
        hexa = famille = None
        if r.al is not None:
            hexa = oklch_to_hex(OKLCH(L=r.al, C=r.ac, H=r.ah))
            famille = r.afam
        elif r.l is not None and algo == "complet":
            # Repli : couleurs_ville_algo pas encore peuplée (base pré-0004).
            hexa = oklch_to_hex(OKLCH(L=r.l, C=r.c, H=r.h))
            repartition = _json_col(r.repartition) or []
            famille = repartition[0]["famille"] if repartition else None
        resultats.append(
            CommuneResultat(
                code_insee=r.code_insee,
                nom=r.nom,
                departement=r.departement,
                hex=hexa,
                famille=famille,
            )
        )
    return resultats


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
def couleur(insee: str, algo: Algo = Query("complet"), conn=Depends(get_conn)):
    """Couleur synthétique OKLCH + participation d'une commune."""
    row = conn.execute(
        text(
            "SELECT cv.code_insee, cv.l, cv.c, cv.h, cv.participation_mediane, "
            "cv.scrutins_inclus, cv.repartition, "
            "cva.l AS al, cva.c AS ac, cva.h AS ah, "
            "cva.famille_dominante AS afam "
            "FROM couleurs_ville cv "
            "LEFT JOIN couleurs_ville_algo cva ON cva.code_insee = cv.code_insee "
            "AND cva.algo = :algo "
            "WHERE cv.code_insee = :x"
        ),
        {"x": insee, "algo": algo},
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="commune sans couleur")
    return _synthese(row, algo)


@router.get("/{insee}", response_model=CommuneFiche)
def fiche(insee: str, algo: Algo = Query("complet"), conn=Depends(get_conn)):
    """Fiche complète : métadonnées de la commune + couleur synthétique."""
    row = conn.execute(
        text(
            "SELECT c.code_insee, c.nom, c.departement, c.region, c.population, "
            "cv.l, cv.c, cv.h, cv.participation_mediane, cv.scrutins_inclus, "
            "cv.repartition, "
            "cva.l AS al, cva.c AS ac, cva.h AS ah, "
            "cva.famille_dominante AS afam "
            "FROM communes c JOIN couleurs_ville cv ON cv.code_insee = c.code_insee "
            "LEFT JOIN couleurs_ville_algo cva ON cva.code_insee = c.code_insee "
            "AND cva.algo = :algo "
            "WHERE c.code_insee = :x"
        ),
        {"x": insee, "algo": algo},
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="commune inconnue")
    return CommuneFiche(
        code_insee=row.code_insee,
        nom=row.nom,
        departement=row.departement,
        region=row.region,
        population=row.population,
        couleur=_synthese(row, algo),
    )
