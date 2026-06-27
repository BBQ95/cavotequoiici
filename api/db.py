"""Connexion à la base (couche partagée de l'API).

L'API est en lecture seule : elle sert des données précalculées. L'URL provient de
DATABASE_URL (jamais de secret en dur).
"""

from __future__ import annotations

import os

from sqlalchemy import Engine, create_engine

DEFAUT_DB_URL = "postgresql+psycopg2://postgres:cavote@localhost:5432/postgres"

_engine: Engine | None = None


def get_engine() -> Engine:
    """Engine SQLAlchemy paresseux (créé au premier appel)."""
    global _engine
    if _engine is None:
        _engine = create_engine(os.environ.get("DATABASE_URL", DEFAUT_DB_URL))
    return _engine


def get_conn():
    """Dépendance FastAPI : fournit une connexion par requête."""
    with get_engine().connect() as conn:
        yield conn
