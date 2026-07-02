"""Chargement des contours géographiques des communes dans PostGIS (Étape 1).

Source : Etalab « Contours administratifs » 2024, fichier `communes-100m.geojson`
(déjà simplifié ≈100 m, déjà en EPSG:4326, avec code INSEE / nom / département / région).
Lu via GeoPandas/pyogrio — aucun GDAL système requis.

Usage :
    DATABASE_URL=postgresql+psycopg2://postgres:cavote@localhost:5432/postgres \\
    COMMUNES_GEOJSON=data/communes-100m.geojson \\
    python -m pipeline.load_communes
"""

from __future__ import annotations

import os

import geopandas as gpd
from shapely.geometry import MultiPolygon, Polygon
from sqlalchemy import create_engine, text

# Colonnes du GeoDataFrame préparé, alignées sur la table `communes`
# (la géométrie reste nommée "geometry" ici ; renommée en "geom" au moment de l'écriture).
COLONNES_CIBLE = ["code_insee", "nom", "departement", "region", "geometry"]

DEFAUT_GEOJSON = "data/communes-100m.geojson"
DEFAUT_DB_URL = "postgresql+psycopg2://postgres:cavote@localhost:5432/postgres"


def normalize_insee(value) -> str:
    """Normalise un code INSEE : 5 caractères, zéro-paddé, lettres en majuscule.

    Gère les entiers, les espaces parasites et la Corse (2A/2B). Lève ValueError
    pour une valeur vide / nulle / NaN.
    """
    if value is None:
        raise ValueError("code INSEE nul")
    s = str(value).strip().upper()
    if not s or s == "NAN":
        raise ValueError(f"code INSEE invalide: {value!r}")
    return s.zfill(5)


def to_multipolygon(geom) -> MultiPolygon:
    """Garantit une géométrie MultiPolygon (la colonne PostGIS l'exige)."""
    if geom is None:
        raise ValueError("géométrie nulle")
    if isinstance(geom, MultiPolygon):
        return geom
    if isinstance(geom, Polygon):
        return MultiPolygon([geom])
    raise ValueError(f"géométrie non polygonale: {geom.geom_type}")


def prepare_communes(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Projette le GeoDataFrame source sur le schéma cible `communes`.

    - normalise le code INSEE (colonne source `code` -> `code_insee`) ;
    - convertit les géométries en MultiPolygon ;
    - ne conserve que les colonnes cible et déduplique par code INSEE.
    """
    gdf = gdf.copy()
    gdf["code_insee"] = gdf["code"].map(normalize_insee)
    gdf["geometry"] = gdf["geometry"].map(to_multipolygon)

    out = gpd.GeoDataFrame(
        gdf[["code_insee", "nom", "departement", "region"]].copy(),
        geometry=gdf["geometry"],
        crs=gdf.crs,
    )
    out = out[COLONNES_CIBLE]
    out = out.drop_duplicates(subset="code_insee", keep="first").reset_index(drop=True)
    return gpd.GeoDataFrame(out, geometry="geometry", crs=gdf.crs)


def upsert_communes(gdf: gpd.GeoDataFrame, engine) -> int:
    """Remplace le contenu de la table `communes` par `gdf`, rejouable.

    Un `DELETE FROM communes` global violerait les clés étrangères de
    `resultats_scrutin` / `couleurs_scrutin` / `couleurs_ville` dès qu'un
    scrutin a été ingéré : on passe par une table de transit puis un upsert
    par code INSEE. Les communes absentes de `gdf` (contours retirés d'un
    millésime) sont purgées avec leurs données liées. La géométrie est écrite
    dans la colonne `geom`. Retourne le nombre de lignes chargées.
    """
    gdf.rename_geometry("geom").to_postgis(
        "communes_transit", engine, if_exists="replace", index=False
    )
    with engine.begin() as conn:
        # Index + stats indispensables : les purges anti-jointure ci-dessous
        # balaient resultats_scrutin (~1 M de lignes).
        conn.execute(
            text("CREATE INDEX ix_communes_transit ON communes_transit (code_insee)")
        )
        conn.execute(text("ANALYZE communes_transit"))
        conn.execute(
            text(
                "INSERT INTO communes (code_insee, nom, departement, region, geom) "
                "SELECT code_insee, nom, departement, region, geom "
                "FROM communes_transit "
                "ON CONFLICT (code_insee) DO UPDATE SET "
                "nom = EXCLUDED.nom, departement = EXCLUDED.departement, "
                "region = EXCLUDED.region, geom = EXCLUDED.geom"
            )
        )
        # Purge des communes disparues du référentiel, tables filles d'abord.
        for table in (
            "resultats_scrutin",
            "couleurs_scrutin",
            "couleurs_ville",
            "communes",
        ):
            conn.execute(
                text(
                    f"DELETE FROM {table} x WHERE NOT EXISTS "
                    "(SELECT 1 FROM communes_transit t "
                    "WHERE t.code_insee = x.code_insee)"
                )
            )
        conn.execute(text("DROP TABLE communes_transit"))
        # Répare les géométries invalides (auto-intersections introduites par la
        # simplification) en conservant le type MultiPolygon attendu par la colonne.
        conn.execute(
            text(
                "UPDATE communes "
                "SET geom = ST_Multi(ST_CollectionExtract(ST_MakeValid(geom), 3)) "
                "WHERE NOT ST_IsValid(geom)"
            )
        )
    return len(gdf)


def main() -> None:
    path = os.environ.get("COMMUNES_GEOJSON", DEFAUT_GEOJSON)
    url = os.environ.get("DATABASE_URL", DEFAUT_DB_URL)
    print(f"Lecture {path} …")
    gdf = gpd.read_file(path)
    out = prepare_communes(gdf)
    engine = create_engine(url)
    n = upsert_communes(out, engine)
    print(f"{n} communes chargées dans PostGIS.")


if __name__ == "__main__":
    main()
