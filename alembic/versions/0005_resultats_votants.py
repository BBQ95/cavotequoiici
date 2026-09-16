"""Conserve les votants (blancs et nuls compris) pour la participation.

Revision ID: 0005_resultats_votants
Revises: 0004_couleurs_algo

Les exprimés ne permettent pas de reconstituer les votants : les lignes
existantes restent NULL jusqu'à la réingestion des quatre sources. Le calcul
refuse ces lignes plutôt que de publier une participation sous-estimée.
"""

from alembic import op
import sqlalchemy as sa

revision = "0005_resultats_votants"
down_revision = "0004_couleurs_algo"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("resultats_scrutin", sa.Column("votants", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("resultats_scrutin", "votants")
