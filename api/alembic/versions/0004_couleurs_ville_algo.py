"""Ajoute couleurs_ville_algo : couleur de synthèse par algo de dominance.

Revision ID: 0004_couleurs_algo
Revises: 0003_nom_recherche
Create Date: 2026-07-06

P1 Todo — trois algos sélectionnables dans l'app (cf. pipeline.couleur.ALGOS :
complet / tendance / blocs). Une ligne par (commune, algo), remplie par
`compute_couleurs` ; `couleurs_ville` reste la synthèse historique (= algo
complet) pour la compatibilité API/app. La répartition par famille n'est pas
dupliquée ici : identique pour tous les algos, elle vit dans couleurs_ville.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0004_couleurs_algo"
down_revision = "0003_nom_recherche"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "couleurs_ville_algo",
        sa.Column("code_insee", sa.String(length=5),
                  sa.ForeignKey("communes.code_insee"), nullable=False),
        sa.Column("algo", sa.String(length=16), nullable=False),
        sa.Column("l", sa.Float(), nullable=False),
        sa.Column("c", sa.Float(), nullable=False),
        sa.Column("h", sa.Float(), nullable=False),
        sa.Column("famille_dominante", sa.Text(), nullable=False),
        sa.Column("part_synthetique", sa.Float(), nullable=False),
        sa.Column("marge", sa.Float(), nullable=False),
        sa.Column("calcule_le", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("code_insee", "algo"),
    )


def downgrade() -> None:
    op.drop_table("couleurs_ville_algo")
