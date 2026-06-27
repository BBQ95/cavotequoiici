"""Décodage des colonnes JSON lues via SQLAlchemy `text()` brut.

Les colonnes `sa.JSON()` (ex. `couleurs_ville.repartition`, `scrutins_inclus`)
sont peuplées via `json.dumps(...)`. Lues par une requête `text()` brute,
SQLAlchemy ignore le type de colonne : selon le driver, la valeur revient soit
déjà désérialisée (liste/dict), soit sous forme de chaîne JSON. Ce helper
normalise les deux cas. Source unique partagée par l'API et le pipeline.
"""

from __future__ import annotations

import json
from typing import Any


def decode_json_col(valeur: Any) -> Any:
    """Renvoie la valeur désérialisée, qu'elle arrive en str JSON ou déjà décodée."""
    if isinstance(valeur, str):
        return json.loads(valeur)
    return valeur
