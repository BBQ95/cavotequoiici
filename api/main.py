"""Application FastAPI CaVoteQuoiIci (API de lecture).

Sert les données précalculées (couleurs, résultats par commune). Les routes sont
réparties en deux routeurs disjoints : `communes` (recherche, fiche, couleur,
proximité) et `scrutins` (détail par scrutin).
"""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.routers import communes, scrutins

app = FastAPI(
    title="CaVoteQuoiIci API",
    version="0.1.0",
    description="API de lecture : couleur politique synthétique des communes.",
)

# API publique en lecture seule (données figées, aucun secret) : CORS ouvert par
# défaut, restreignable via CORS_ORIGINS (liste séparée par des virgules).
_origins = os.environ.get("CORS_ORIGINS", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _origins == "*" else [o.strip() for o in _origins.split(",")],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(communes.router)
app.include_router(scrutins.router)

# Glyphes MapLibre ({fontstack}/{range}.pbf) pour les étiquettes de la carte
# (cf. api/fonts/README.md). Servis par l'API : ils passent par la même
# exposition (/api) que le reste, aucun service supplémentaire. Le dossier est
# versionné — son absence doit faire échouer le démarrage, pas rendre une carte
# muette.
app.mount("/fonts", StaticFiles(directory=Path(__file__).parent / "fonts"), name="fonts")


@app.get("/healthz", tags=["meta"])
def healthz() -> dict:
    """Sonde de vivacité."""
    return {"status": "ok"}
