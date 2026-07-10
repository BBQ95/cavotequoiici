"""Ajoute communes.nom_recherche : nom normalisé pour la recherche.

Revision ID: 0003_nom_recherche
Revises: 0002_repartition
Create Date: 2026-07-06

Colonne = `pipeline.normalisation.normaliser_nom(nom)` (minuscules, sans
accents/ligatures, séparateurs unifiés) : « nim » trouve Nîmes, « saint denis »
trouve Saint-Denis. Remplie par `load_communes` au chargement ; backfill ici
pour les bases existantes — la migration importe la fonction du pipeline pour
garantir que valeurs stockées et requêtes normalisées restent alignées.
Index `text_pattern_ops` : sert le LIKE 'prefixe%' de l'autocomplétion.
"""

import sys
from pathlib import Path

from alembic import op
import sqlalchemy as sa

# La racine du repo (qui porte le package pipeline) n'est pas forcément dans
# sys.path si alembic est invoqué hors racine — on l'ajoute depuis __file__.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pipeline.normalisation import normaliser_nom  # noqa: E402

# revision identifiers, used by Alembic.
revision = "0003_nom_recherche"
down_revision = "0002_repartition"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("communes", sa.Column("nom_recherche", sa.Text(), nullable=True))

    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT code_insee, nom FROM communes")).fetchall()
    if rows:
        conn.execute(
            sa.text(
                "UPDATE communes SET nom_recherche = :nr WHERE code_insee = :ci"
            ),
            [{"ci": r.code_insee, "nr": normaliser_nom(r.nom)} for r in rows],
        )

    op.alter_column("communes", "nom_recherche", nullable=False)
    op.create_index(
        "ix_communes_nom_recherche",
        "communes",
        ["nom_recherche"],
        postgresql_ops={"nom_recherche": "text_pattern_ops"},
    )


def downgrade() -> None:
    op.drop_index("ix_communes_nom_recherche", table_name="communes")
    op.drop_column("communes", "nom_recherche")
