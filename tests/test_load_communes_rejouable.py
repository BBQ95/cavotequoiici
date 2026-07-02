"""Rejouabilité du chargement des communes sur une base déjà peuplée.

Régression du bug « pipeline non idempotent » : `upsert_communes` vidait la
table `communes`, ce qui viole les clés étrangères de `resultats_scrutin`,
`couleurs_scrutin` et `couleurs_ville` dès qu'un scrutin a été ingéré. Relancer
`make data` (réflexe naturel après un échec) plantait donc à l'étape 1.

Test d'intégration : nécessite DATABASE_URL (base migrée et peuplée) et les
contours `data/communes-100m.geojson`. Lancer avec : pytest -m integration
"""

import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

DB = os.environ.get("DATABASE_URL")
GEOJSON = Path(os.environ.get("COMMUNES_GEOJSON", "data/communes-100m.geojson"))

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not DB, reason="DATABASE_URL non définie (test d'intégration BDD)"),
    pytest.mark.skipif(not GEOJSON.exists(), reason="contours absents (make fresh non lancé)"),
]


def _compte(conn, table: str) -> int:
    return conn.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()


def test_upsert_communes_rejouable_sans_violer_les_fk():
    """Recharger les contours sur une base peuplée ne doit ni planter ni perdre de données."""
    import geopandas as gpd

    from pipeline.load_communes import prepare_communes, upsert_communes

    engine = create_engine(DB)
    with engine.connect() as conn:
        communes_avant = _compte(conn, "communes")
        resultats_avant = _compte(conn, "resultats_scrutin")
        couleurs_avant = _compte(conn, "couleurs_ville")
    if resultats_avant == 0:
        pytest.skip("aucun résultat ingéré : le scénario FK n'est pas reproductible")

    gdf = prepare_communes(gpd.read_file(GEOJSON))
    n = upsert_communes(gdf, engine)  # ne doit pas lever de ForeignKeyViolation

    assert n == len(gdf)
    with engine.connect() as conn:
        assert _compte(conn, "communes") == communes_avant
        assert _compte(conn, "resultats_scrutin") == resultats_avant
        assert _compte(conn, "couleurs_ville") == couleurs_avant
