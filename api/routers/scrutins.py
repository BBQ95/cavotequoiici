"""Routeur scrutins : liste des scrutins inclus + détail par scrutin d'une commune.

À implémenter (piste Richard). Ce module est déjà enregistré dans api/main.py —
y ajouter les routes sans toucher à main.py ni aux autres fichiers partagés.

Routes attendues :
  GET /communes/{insee}/scrutins                  -> scrutins inclus + poids relatif
  GET /communes/{insee}/scrutins/{scrutin_id}     -> détail par famille + couleur du scrutin
"""

from fastapi import APIRouter

router = APIRouter(prefix="/communes", tags=["scrutins"])
