"""pipeline/export_tiles.py — Export des communes colorées en tuiles vectorielles.

Étape 6.1 du guide. Lit la synthèse `couleurs_ville` jointe aux contours
`communes`, précalcule la couleur sRGB (#RRGGBB) à partir de l'OKLCH de synthèse
puis produit `tiles/communes.pmtiles` via tippecanoe.

Pourquoi figer le hex dans la tuile plutôt que transporter L/C/H ?
  - MapLibre GL ne sait pas interpoler en OKLCH ; convertir côté client
    impliquerait de réimplémenter (et maintenir) la conversion.
  - Figer le hex garantit que la carte montre **exactement** la même couleur
    que la fiche commune (source unique : `pipeline.couleur.oklch_to_hex`).

Usage :
    DATABASE_URL=postgresql+psycopg2://postgres:cavote@localhost:5432/postgres \\
        python -m pipeline.export_tiles
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterator, Mapping

from sqlalchemy import create_engine, text

from pipeline.couleur import OKLCH, COULEURS, oklch_to_hex
from pipeline.jsoncol import decode_json_col

DEFAUT_DB_URL = "postgresql+psycopg2://postgres:cavote@localhost:5432/postgres"

RACINE = Path(__file__).resolve().parent.parent
GEOJSON_PATH = RACINE / "tiles" / "communes.geojson"
PMTILES_PATH = RACINE / "tiles" / "communes.pmtiles"

# La couche dans laquelle MapLibre trouvera les communes (source-layer).
NOM_COUCHE = "communes"

# Bornes de zoom : z4 ≈ France entière, z11 ≈ rue. `--extend-zooms-if-still-
# dropping` garantit qu'aucune commune n'est définitivement perdue à maxzoom.
ZOOM_MIN = 4
ZOOM_MAX = 11

# Jointure synthèse × contours. ST_AsGeoJSON sort des coordonnées lon/lat
# (EPSG:4326), ce qu'attend tippecanoe.
_SQL = text(
    """
    SELECT c.code_insee,
           c.nom,
           cv.l,
           cv.c,
           cv.h,
           cv.participation_mediane,
           cv.repartition,
           ST_AsGeoJSON(c.geom) AS geom
    FROM communes c
    JOIN couleurs_ville cv ON cv.code_insee = c.code_insee
    """
)


def feature_proprietes(row: Mapping[str, Any]) -> dict[str, Any]:
    """Propriétés d'une commune pour la tuile, depuis une ligne de la jointure.

    `row` expose : code_insee, nom, l, c, h, participation_mediane, repartition
    (liste de {famille, part} triée par part décroissante, telle que produite
    par `compute_couleurs`).
    """
    # `repartition` est une colonne sa.JSON() lue via text() brut : selon le
    # driver elle peut arriver en chaîne JSON non décodée (cf. pipeline.jsoncol).
    repartition = decode_json_col(row["repartition"]) or []
    premier = repartition[0] if repartition else {}
    famille = premier.get("famille", "divers") if isinstance(premier, dict) else "divers"
    # Garde-fou : une famille inconnue de la palette retomberait sur `divers`
    # côté client ; on n'invente pas de teinte ici, on transmet la famille.
    if famille not in COULEURS:
        famille = "divers"

    participation = row["participation_mediane"]
    return {
        "insee": row["code_insee"],
        "nom": row["nom"],
        "hex": oklch_to_hex(OKLCH(L=row["l"], C=row["c"], H=row["h"])),
        "famille": famille,
        "participation": round(participation, 3) if participation is not None else None,
    }


def feature(row: Mapping[str, Any], geometry: Mapping[str, Any]) -> dict[str, Any]:
    """Assemble une Feature GeoJSON à partir d'une ligne et de sa géométrie."""
    return {
        "type": "Feature",
        "geometry": geometry,
        "properties": feature_proprietes(row),
    }


def iter_features(conn) -> Iterator[dict[str, Any]]:
    """Itère les Features GeoJSON des communes ayant une couleur de synthèse."""
    for row in conn.execute(_SQL).mappings():
        geometry = json.loads(row["geom"])
        yield feature(row, geometry)


def ecrire_geojson(conn, chemin: Path) -> int:
    """Écrit la FeatureCollection en flux (sans tout charger en mémoire).

    Retourne le nombre de communes écrites.
    """
    chemin.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with chemin.open("w", encoding="utf-8") as f:
        f.write('{"type":"FeatureCollection","features":[')
        for feat in iter_features(conn):
            if n:
                f.write(",")
            f.write(json.dumps(feat, ensure_ascii=False, separators=(",", ":")))
            n += 1
        f.write("]}")
    return n


def generer_tuiles(geojson_path: Path, pmtiles_path: Path) -> None:
    """Lance tippecanoe pour produire le PMTiles depuis le GeoJSON."""
    if shutil.which("tippecanoe") is None:
        raise RuntimeError(
            "tippecanoe introuvable. Installer le binaire système "
            "(ex. `apt install tippecanoe`) avant de générer les tuiles."
        )
    cmd = [
        "tippecanoe",
        "-o", str(pmtiles_path),
        "--force",  # écrase la sortie existante
        "--layer", NOM_COUCHE,
        f"--minimum-zoom={ZOOM_MIN}",
        f"--maximum-zoom={ZOOM_MAX}",
        # Polygones administratifs : on préserve les frontières (faible
        # simplification). Aux zooms bas, on **fusionne** les communes les plus
        # denses (coalesce) au lieu de les **supprimer** (drop) : supprimer
        # laissait des trous dans les zones urbaines denses (Île-de-France…) à
        # l'échelle France. Coalesce garde une couverture pleine ; l'identité
        # exacte au tap se retrouve en zoomant (couverture complète à maxzoom via
        # --extend-zooms-if-still-dropping).
        "--simplification=4",
        "--coalesce-densest-as-needed",
        "--extend-zooms-if-still-dropping",
        str(geojson_path),
    ]
    print("→ tippecanoe", " ".join(cmd[1:]))
    subprocess.run(cmd, check=True)


def main() -> None:
    url = os.environ.get("DATABASE_URL", DEFAUT_DB_URL)
    engine = create_engine(url)
    with engine.connect() as conn:
        n = ecrire_geojson(conn, GEOJSON_PATH)
    taille_mo = GEOJSON_PATH.stat().st_size / 1e6
    print(f"✓ {n} communes écrites dans {GEOJSON_PATH} ({taille_mo:.1f} Mo)")
    if n == 0:
        print("✗ aucune commune — la table couleurs_ville est-elle peuplée ?", file=sys.stderr)
        sys.exit(1)
    generer_tuiles(GEOJSON_PATH, PMTILES_PATH)
    taille_mo = PMTILES_PATH.stat().st_size / 1e6
    print(f"✓ tuiles générées : {PMTILES_PATH} ({taille_mo:.1f} Mo)")


if __name__ == "__main__":
    main()
