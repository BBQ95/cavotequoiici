"""pipeline/export_tiles.py — Export des communes colorées en tuiles vectorielles.

Étape 6.1 du guide. Lit la synthèse `couleurs_ville` jointe aux contours
`communes`, précalcule la couleur sRGB (#RRGGBB) à partir de l'OKLCH de synthèse
puis produit `tiles/communes.pmtiles` via tippecanoe.

L'archive contient DEUX couches :
  - `communes`   : polygones colorés (choroplèthe) ;
  - `etiquettes` : points de noms de villes (ST_PointOnSurface), étagés par
    rang national (proxy MAX(inscrits)) — grandes villes aux zooms bas,
    petites communes en zoomant.

L'étagement des étiquettes se fait par TRANCHES DE ZOOM fusionnées par
tile-join (une mini-archive mono-zoom par niveau, la tranche du zoom z
contenant toutes les communes déjà visibles à z). On n'utilise PAS le minzoom
par feature de tippecanoe (`"tippecanoe": {"minzoom": N}`) : avec la version
2.49.0, il réactive un dot-dropping qui ignore -r1 — une seule ville
survivait par tuile et par zoom (Marseille n'apparaissait jamais).

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
from typing import Any, Iterable, Iterator, Mapping

from sqlalchemy import create_engine, text

from pipeline.couleur import OKLCH, COULEURS, oklch_to_hex
from pipeline.jsoncol import decode_json_col

DEFAUT_DB_URL = "postgresql+psycopg2://postgres:cavote@localhost:5432/postgres"

RACINE = Path(__file__).resolve().parent.parent
GEOJSON_PATH = RACINE / "tiles" / "communes.geojson"
ETIQUETTES_GEOJSON_PATH = RACINE / "tiles" / "etiquettes.geojson"
PMTILES_PATH = RACINE / "tiles" / "communes.pmtiles"
# Artefacts intermédiaires (gitignorés comme le reste de tiles/).
POLYGONES_PMTILES_PATH = RACINE / "tiles" / "communes-polygones.pmtiles"

# Les couches dans lesquelles MapLibre trouvera les données (source-layer).
NOM_COUCHE = "communes"
NOM_COUCHE_ETIQUETTES = "etiquettes"

# Étagement des étiquettes : (rang national max inclus, minzoom). Au-delà du
# dernier seuil : ZOOM_MAX. Progression ~×3-4 par niveau (surface visible ×4
# par zoom) ; calibré sur la distribution des inscrits (top 10 ≈ métropoles,
# top 12 000 ≈ bourgs > ~700 inscrits).
SEUILS_MINZOOM: tuple[tuple[int, int], ...] = (
    (10, 4),
    (40, 5),
    (120, 6),
    (400, 7),
    (1200, 8),
    (4000, 9),
    (12000, 10),
)

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

# Couleur OKLCH de chaque commune pour CHAQUE scrutin (carte v2 : la carte
# bascule synthèse ↔ scrutin sans re-télécharger — tout vit dans la tuile).
_SQL_COULEURS_SCRUTIN = text(
    "SELECT code_insee, scrutin_id, l, c, h FROM couleurs_scrutin"
)

# Couleur de synthèse par algo de dominance (P1.2 : la carte bascule d'algo
# sans re-télécharger). « complet » est exclu : c'est déjà la clé `hex`.
_SQL_COULEURS_ALGO = text(
    "SELECT code_insee, algo, l, c, h FROM couleurs_ville_algo "
    "WHERE algo != 'complet'"
)

# Points d'étiquette : même univers que les polygones (jointure couleurs_ville).
# Priorité = rang national par MAX(inscrits) (proxy de population ; le tiebreak
# code_insee rend le rang déterministe). ST_PointOnSurface garantit un point
# DANS le polygone (un centroïde peut tomber dehors : communes en croissant,
# multipolygones).
_SQL_ETIQUETTES = text(
    """
    SELECT c.code_insee,
           c.nom,
           row_number() OVER (ORDER BY m.max_inscrits DESC NULLS LAST, c.code_insee) AS rang,
           ST_AsGeoJSON(ST_PointOnSurface(c.geom)) AS geom
    FROM communes c
    JOIN couleurs_ville cv ON cv.code_insee = c.code_insee
    LEFT JOIN (
        SELECT code_insee, MAX(inscrits) AS max_inscrits
        FROM resultats_scrutin
        GROUP BY code_insee
    ) m ON m.code_insee = c.code_insee
    """
)


def minzoom_pour_rang(rang: int) -> int:
    """Zoom d'apparition de l'étiquette d'une commune selon son rang national."""
    for borne, minzoom in SEUILS_MINZOOM:
        if rang <= borne:
            return minzoom
    return ZOOM_MAX


def feature_etiquette(row: Mapping[str, Any], geometry: Mapping[str, Any]) -> dict[str, Any]:
    """Feature de point d'étiquette.

    Propriétés minimales : `nom` (texte affiché), `insee` (tap sur un nom →
    fiche commune), `rang` (priorité de collision côté client). L'étagement
    par zoom n'est PAS porté par la feature (cf. docstring du module) : il
    vient du découpage en tranches (`tranche_etiquettes`).
    """
    return {
        "type": "Feature",
        "geometry": geometry,
        "properties": {
            "nom": row["nom"],
            "insee": row["code_insee"],
            "rang": row["rang"],
        },
    }


def tranche_etiquettes(
    features: list[dict[str, Any]], zoom: int
) -> list[dict[str, Any]]:
    """Étiquettes déjà visibles au zoom donné (minzoom_pour_rang(rang) <= zoom).

    Chaque commune figure donc dans toutes les tranches de son zoom
    d'apparition jusqu'à ZOOM_MAX — chaque tranche devient une archive
    mono-zoom autosuffisante.
    """
    return [
        f for f in features if minzoom_pour_rang(f["properties"]["rang"]) <= zoom
    ]


def iter_etiquettes(conn) -> Iterator[dict[str, Any]]:
    """Itère les Features de points d'étiquette des communes tuilées."""
    for row in conn.execute(_SQL_ETIQUETTES).mappings():
        yield feature_etiquette(row, json.loads(row["geom"]))


def charger_couleurs_scrutin(conn) -> dict[str, dict[str, OKLCH]]:
    """Charge couleurs_scrutin en mémoire : code_insee → {scrutin_id: OKLCH}.

    ~4 scrutins × 35 000 communes : tient largement en mémoire, et évite une
    jointure agrégée par ligne dans la requête principale streamée.
    """
    couleurs: dict[str, dict[str, OKLCH]] = {}
    for row in conn.execute(_SQL_COULEURS_SCRUTIN).mappings():
        couleurs.setdefault(row["code_insee"], {})[row["scrutin_id"]] = OKLCH(
            L=row["l"], C=row["c"], H=row["h"]
        )
    return couleurs


def feature_proprietes(
    row: Mapping[str, Any],
    couleurs_par_scrutin: Mapping[str, OKLCH] | None = None,
    couleurs_par_algo: Mapping[str, OKLCH] | None = None,
) -> dict[str, Any]:
    """Propriétés d'une commune pour la tuile, depuis une ligne de la jointure.

    `row` expose : code_insee, nom, l, c, h, participation_mediane, repartition
    (liste de {famille, part} triée par part décroissante, telle que produite
    par `compute_couleurs`).

    `couleurs_par_scrutin` (scrutin_id → OKLCH, depuis couleurs_scrutin) ajoute
    une clé `hex_<scrutin_id>` par scrutin disputé dans la commune. Un scrutin
    absent n'émet PAS de clé (feature plus légère ; le client retombe sur une
    teinte neutre via `coalesce`).

    `couleurs_par_algo` (algo → OKLCH, depuis couleurs_ville_algo) ajoute une
    clé `hex_algo_<algo>` par algo de dominance alternatif ; « complet » est
    ignoré (c'est la clé `hex`), même absence de clé pour une commune sans
    ligne.
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
    props = {
        "insee": row["code_insee"],
        "nom": row["nom"],
        "hex": oklch_to_hex(OKLCH(L=row["l"], C=row["c"], H=row["h"])),
        "famille": famille,
        "participation": round(participation, 3) if participation is not None else None,
    }
    for scrutin_id, oklch in (couleurs_par_scrutin or {}).items():
        props[f"hex_{scrutin_id}"] = oklch_to_hex(oklch)
    for algo, oklch in (couleurs_par_algo or {}).items():
        if algo != "complet":
            props[f"hex_algo_{algo}"] = oklch_to_hex(oklch)
    return props


def feature(
    row: Mapping[str, Any],
    geometry: Mapping[str, Any],
    couleurs_par_scrutin: Mapping[str, OKLCH] | None = None,
    couleurs_par_algo: Mapping[str, OKLCH] | None = None,
) -> dict[str, Any]:
    """Assemble une Feature GeoJSON à partir d'une ligne et de sa géométrie."""
    return {
        "type": "Feature",
        "geometry": geometry,
        "properties": feature_proprietes(row, couleurs_par_scrutin, couleurs_par_algo),
    }


def charger_couleurs_algo(conn) -> dict[str, dict[str, OKLCH]]:
    """Charge couleurs_ville_algo (hors complet) : code_insee → {algo: OKLCH}.

    2 algos × 35 000 communes : même stratégie en mémoire que
    `charger_couleurs_scrutin`.
    """
    couleurs: dict[str, dict[str, OKLCH]] = {}
    for row in conn.execute(_SQL_COULEURS_ALGO).mappings():
        couleurs.setdefault(row["code_insee"], {})[row["algo"]] = OKLCH(
            L=row["l"], C=row["c"], H=row["h"]
        )
    return couleurs


def iter_features(conn) -> Iterator[dict[str, Any]]:
    """Itère les Features GeoJSON des communes ayant une couleur de synthèse."""
    couleurs_scrutin = charger_couleurs_scrutin(conn)
    couleurs_algo = charger_couleurs_algo(conn)
    for row in conn.execute(_SQL).mappings():
        geometry = json.loads(row["geom"])
        yield feature(
            row,
            geometry,
            couleurs_scrutin.get(row["code_insee"]),
            couleurs_algo.get(row["code_insee"]),
        )


def ecrire_geojson(features: Iterable[dict[str, Any]], chemin: Path) -> int:
    """Écrit la FeatureCollection en flux (sans tout charger en mémoire).

    Retourne le nombre de features écrites.
    """
    chemin.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with chemin.open("w", encoding="utf-8") as f:
        f.write('{"type":"FeatureCollection","features":[')
        for feat in features:
            if n:
                f.write(",")
            f.write(json.dumps(feat, ensure_ascii=False, separators=(",", ":")))
            n += 1
        f.write("]}")
    return n


def commande_tippecanoe_communes(geojson_communes: Path, pmtiles_path: Path) -> list[str]:
    """Commande tippecanoe de l'archive des polygones (couche `communes`)."""
    return [
        "tippecanoe",
        "-o", str(pmtiles_path),
        "--force",  # écrase la sortie existante
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
        "-L", f"{NOM_COUCHE}:{geojson_communes}",
    ]


def commande_tippecanoe_etiquettes(
    geojson_tranche: Path, pmtiles_path: Path, zoom: int
) -> list[str]:
    """Commande tippecanoe d'UNE tranche d'étiquettes (archive mono-zoom).

    -r1 : aucun dot-dropping — l'étagement est déjà dans le contenu de la
    tranche, chaque point de la tranche doit apparaître à son zoom.
    """
    return [
        "tippecanoe",
        "-o", str(pmtiles_path),
        "--force",
        f"--minimum-zoom={zoom}",
        f"--maximum-zoom={zoom}",
        "-r1",
        "-L", f"{NOM_COUCHE_ETIQUETTES}:{geojson_tranche}",
    ]


def commande_tile_join(entrees: list[Path], pmtiles_path: Path) -> list[str]:
    """Commande tile-join fusionnant les archives en une seule.

    -pk : tile-join a sa propre limite de 500 Ko par tuile — sans lui il
    re-élaguerait les tuiles z4-z6 déjà passées au coalesce de tippecanoe.
    """
    return [
        "tile-join",
        "--force",
        "-pk",
        "-o", str(pmtiles_path),
        *[str(p) for p in entrees],
    ]


def _lancer(cmd: list[str]) -> None:
    print("→", cmd[0], " ".join(cmd[1:]))
    subprocess.run(cmd, check=True)


def generer_tuiles(
    geojson_communes: Path, etiquettes: list[dict[str, Any]], pmtiles_path: Path
) -> None:
    """Produit l'archive finale : polygones + une tranche d'étiquettes par zoom.

    Toutes les archives intermédiaires vivent dans tiles/ (gitignorées) puis
    sont fusionnées par tile-join dans `pmtiles_path`.
    """
    for binaire in ("tippecanoe", "tile-join"):
        if shutil.which(binaire) is None:
            raise RuntimeError(
                f"{binaire} introuvable. Installer tippecanoe (fournit aussi "
                "tile-join) : `apt install tippecanoe` (Debian/Ubuntu récents), "
                "`brew install tippecanoe` (macOS), paquet AUR, ou compilation "
                "depuis https://github.com/felt/tippecanoe (cf. tiles/README.md)."
            )
    _lancer(commande_tippecanoe_communes(geojson_communes, POLYGONES_PMTILES_PATH))
    archives = [POLYGONES_PMTILES_PATH]
    for zoom in range(ZOOM_MIN, ZOOM_MAX + 1):
        tranche = tranche_etiquettes(etiquettes, zoom)
        geojson = RACINE / "tiles" / f"etiquettes-z{zoom}.geojson"
        pmtiles = RACINE / "tiles" / f"etiquettes-z{zoom}.pmtiles"
        ecrire_geojson(iter(tranche), geojson)
        _lancer(commande_tippecanoe_etiquettes(geojson, pmtiles, zoom))
        archives.append(pmtiles)
        print(f"✓ tranche z{zoom} : {len(tranche)} étiquettes")
    _lancer(commande_tile_join(archives, pmtiles_path))


def main() -> None:
    url = os.environ.get("DATABASE_URL", DEFAUT_DB_URL)
    engine = create_engine(url)
    with engine.connect() as conn:
        n = ecrire_geojson(iter_features(conn), GEOJSON_PATH)
        etiquettes = list(iter_etiquettes(conn))
        ecrire_geojson(iter(etiquettes), ETIQUETTES_GEOJSON_PATH)
    taille_mo = GEOJSON_PATH.stat().st_size / 1e6
    print(f"✓ {n} communes écrites dans {GEOJSON_PATH} ({taille_mo:.1f} Mo)")
    print(f"✓ {len(etiquettes)} étiquettes écrites dans {ETIQUETTES_GEOJSON_PATH}")
    if n == 0:
        print("✗ aucune commune — la table couleurs_ville est-elle peuplée ?", file=sys.stderr)
        sys.exit(1)
    generer_tuiles(GEOJSON_PATH, etiquettes, PMTILES_PATH)
    taille_mo = PMTILES_PATH.stat().st_size / 1e6
    print(f"✓ tuiles générées : {PMTILES_PATH} ({taille_mo:.1f} Mo)")


if __name__ == "__main__":
    main()
