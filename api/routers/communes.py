"""Routeur communes : recherche, fiche, couleur synthétique, proximité.

Implémenté dans la piste CLI (Étape 4). Ce module est déjà enregistré dans
api/main.py — y ajouter les routes sans toucher à main.py.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/communes", tags=["communes"])
