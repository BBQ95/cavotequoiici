"""Schéma initial : communes, scrutins, résultats et couleurs précalculées.

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-27

Tables (cf. Outline "CaVoteQuoiIci" — Guide d'implémentation §0.3 / Architecture technique §4) :
  communes, scrutins, resultats_scrutin, couleurs_scrutin, couleurs_ville.
La table couleurs_ville est l'aboutissement du pipeline : servie directement à l'API et aux tuiles.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    # --- communes : code INSEE + métadonnées + géométrie ---
    op.create_table(
        "communes",
        sa.Column("code_insee", sa.String(length=5), primary_key=True),
        sa.Column("nom", sa.Text(), nullable=False),
        sa.Column("departement", sa.String(length=3), nullable=True),
        sa.Column("region", sa.String(length=3), nullable=True),
        sa.Column("population", sa.Integer(), nullable=True),
    )
    # Géométrie (MultiPolygon WGS84) ajoutée en SQL brut (PostGIS) + index spatial.
    op.execute(
        "ALTER TABLE communes ADD COLUMN geom geometry(MultiPolygon, 4326)"
    )
    op.execute("CREATE INDEX ix_communes_geom ON communes USING GIST (geom)")
    op.create_index("ix_communes_nom", "communes", ["nom"])

    # --- scrutins : un panier d'élections, chacune avec son poids brut ---
    op.create_table(
        "scrutins",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("tour", sa.SmallInteger(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("poids_brut", sa.Float(), nullable=False),
    )

    # --- resultats_scrutin : voix par nuance, par commune et par scrutin ---
    op.create_table(
        "resultats_scrutin",
        sa.Column("code_insee", sa.String(length=5),
                  sa.ForeignKey("communes.code_insee"), nullable=False),
        sa.Column("scrutin_id", sa.String(length=64),
                  sa.ForeignKey("scrutins.id"), nullable=False),
        sa.Column("nuance", sa.String(length=16), nullable=False),
        sa.Column("voix", sa.Integer(), nullable=False),
        sa.Column("exprimes", sa.Integer(), nullable=False),
        sa.Column("inscrits", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("code_insee", "scrutin_id", "nuance"),
    )
    op.create_index(
        "ix_resultats_scrutin_commune", "resultats_scrutin", ["code_insee"]
    )

    # --- couleurs_scrutin : couleur OKLCH d'une commune pour UN scrutin ---
    op.create_table(
        "couleurs_scrutin",
        sa.Column("code_insee", sa.String(length=5),
                  sa.ForeignKey("communes.code_insee"), nullable=False),
        sa.Column("scrutin_id", sa.String(length=64),
                  sa.ForeignKey("scrutins.id"), nullable=False),
        sa.Column("l", sa.Float(), nullable=False),
        sa.Column("c", sa.Float(), nullable=False),
        sa.Column("h", sa.Float(), nullable=False),
        sa.Column("participation", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("code_insee", "scrutin_id"),
    )

    # --- couleurs_ville : SYNTHÈSE précalculée, servie directement à l'app ---
    op.create_table(
        "couleurs_ville",
        sa.Column("code_insee", sa.String(length=5),
                  sa.ForeignKey("communes.code_insee"), primary_key=True),
        sa.Column("l", sa.Float(), nullable=False),
        sa.Column("c", sa.Float(), nullable=False),
        sa.Column("h", sa.Float(), nullable=False),
        sa.Column("participation_mediane", sa.Float(), nullable=False),
        sa.Column("scrutins_inclus", sa.JSON(), nullable=False),
        sa.Column("calcule_le", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("couleurs_ville")
    op.drop_table("couleurs_scrutin")
    op.drop_index("ix_resultats_scrutin_commune", table_name="resultats_scrutin")
    op.drop_table("resultats_scrutin")
    op.drop_table("scrutins")
    op.drop_index("ix_communes_nom", table_name="communes")
    op.execute("DROP INDEX IF EXISTS ix_communes_geom")
    op.drop_table("communes")
