"""Application FastAPI CaVoteQuoiIci (API de lecture).

Sert les données précalculées (couleurs, résultats par commune). Les routes sont
réparties en deux routeurs disjoints : `communes` (recherche, fiche, couleur,
proximité) et `scrutins` (détail par scrutin).
"""

from fastapi import FastAPI

from api.routers import communes, scrutins

app = FastAPI(
    title="CaVoteQuoiIci API",
    version="0.1.0",
    description="API de lecture : couleur politique synthétique des communes.",
)

app.include_router(communes.router)
app.include_router(scrutins.router)


@app.get("/healthz", tags=["meta"])
def healthz() -> dict:
    """Sonde de vivacité."""
    return {"status": "ok"}
