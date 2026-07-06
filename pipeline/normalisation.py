"""Normalisation des noms de communes pour la recherche insensible aux accents.

Source unique de vérité : la colonne `communes.nom_recherche` (remplie au
chargement et par la migration 0003) ET la requête utilisateur (routeur
`/communes/search`) passent par `normaliser_nom` — toute évolution ici doit
s'accompagner d'un rechargement des communes (`make data` ou backfill).
"""

from __future__ import annotations

import unicodedata

# Ligatures que la décomposition Unicode NFD ne sépare pas.
_LIGATURES = {"œ": "oe", "æ": "ae"}

# Séparateurs ramenés à l'espace : « saint denis » doit matcher « Saint-Denis »,
# « l ile » matcher « L'Île- ». Les deux apostrophes (droite et typographique).
_SEPARATEURS = "-'’"


def normaliser_nom(nom: str) -> str:
    """Minuscules, sans accents ni ligatures, séparateurs unifiés en espaces."""
    s = nom.lower()
    for lig, remplacement in _LIGATURES.items():
        s = s.replace(lig, remplacement)
    for sep in _SEPARATEURS:
        s = s.replace(sep, " ")
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.split())
