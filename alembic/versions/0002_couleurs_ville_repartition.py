"""Ajoute couleurs_ville.repartition : répartition synthétique par famille.

Revision ID: 0002_repartition
Revises: 0001_initial
Create Date: 2026-06-27

La synthèse (`pipeline.couleur.couleur_ville`) calcule déjà le classement complet
des familles pondérées (`repartition`). On le persiste pour l'exposer dans
CouleurSynthese (barre des familles de la fiche commune), sans recalcul à la volée.
Colonne nullable : les lignes existantes restent valides jusqu'au prochain
`compute_couleurs`, qui réécrit toutes les lignes avec la répartition.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002_repartition"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "couleurs_ville",
        sa.Column("repartition", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("couleurs_ville", "repartition")
