"""pipeline/export_communes.py — Export statique des fiches communes.

Produit l'arborescence servie par `data.cavotequoiici.fr` (bucket R2 derrière
le CDN Cloudflare), pour que l'app n'ait plus besoin de l'API en production :

    export/
    ├── communes/{insee}.json   fiche par commune, les 3 algos embarqués
    ├── nuances.json            réponse de GET /nuances, figée
    ├── meta/version.json       version des données (cache-busting côté app)
    └── fonts/…                 glyphes MapLibre ({fontstack}/{range}.pbf)

Chaque fiche embarque une `CouleurSynthese` par algo de dominance (l'endpoint
`/communes/{insee}` la sert via `?algo=` ; en statique, le client choisit la
clé dans `couleurs`). Les schémas Pydantic de l'API sont réutilisés tels quels
(`api.schemas.communes`) : la fiche statique reste structurellement identique
à la fiche servie — même source unique de conversion `oklch_to_hex`.

L'import pipeline → api est assumé (et sans cycle : les routeurs importent
pipeline.ingest/synthese, pas ce module) : c'est ce qui garantit la parité
octet pour octet de `nuances.json` avec l'endpoint.

Usage :
    DATABASE_URL=postgresql+psycopg2://postgres:cavote@localhost:5432/postgres \\
        python -m pipeline.export_communes
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping

from sqlalchemy import create_engine, text

from api.routers.nuances import _charger_tout as _charger_nuances
from api.schemas.communes import CouleurSynthese, FamilleSynthese
from pipeline.couleur import ALGOS, OKLCH, oklch_to_hex
from pipeline.jsoncol import decode_json_col

DEFAUT_DB_URL = "postgresql+psycopg2://postgres:cavote@localhost:5432/postgres"

RACINE = Path(__file__).resolve().parent.parent
EXPORT_DIR = RACINE / "export"
FONTS_SRC = RACINE / "api" / "fonts"

# Version du schéma des artefacts statiques (fiches + version.json). À
# incrémenter à chaque changement de forme incompatible côté app.
SCHEMA_VERSION = 1

# Fiche complète par commune : mêmes colonnes que l'endpoint /communes/{insee}
# (métadonnées + synthèse + point représentatif lat/lon), sans le WHERE.
_SQL_FICHES = text(
    """
    SELECT c.code_insee, c.nom, c.departement, c.region, c.population,
           cv.participation_mediane, cv.scrutins_inclus, cv.repartition,
           ST_Y(ST_Transform(ST_PointOnSurface(c.geom), 4326)) AS lat,
           ST_X(ST_Transform(ST_PointOnSurface(c.geom), 4326)) AS lon
    FROM communes c
    JOIN couleurs_ville cv ON cv.code_insee = c.code_insee
    """
)

# Couleur de synthèse par algo (« complet » inclus : contrairement aux tuiles,
# la fiche statique porte les trois, comme l'endpoint avec ?algo=).
_SQL_COULEURS_ALGO = text(
    "SELECT code_insee, algo, l, c, h, famille_dominante FROM couleurs_ville_algo"
)

_SQL_SCRUTINS = text(
    "SELECT DISTINCT scrutin_id FROM couleurs_scrutin ORDER BY scrutin_id"
)


def couleur_synthese(
    row: Mapping[str, Any], algo: str, ligne_algo: Mapping[str, Any]
) -> CouleurSynthese:
    """CouleurSynthese d'une commune pour un algo, comme la servirait l'API.

    `row` : ligne de `_SQL_FICHES` (participation, scrutins_inclus,
    repartition — identiques pour tous les algos). `ligne_algo` : ligne de
    couleurs_ville_algo (l/c/h/famille_dominante propres à l'algo).
    """
    scrutins = decode_json_col(row["scrutins_inclus"]) or []
    repartition = decode_json_col(row["repartition"]) or []
    return CouleurSynthese(
        code_insee=row["code_insee"],
        l=ligne_algo["l"],
        c=ligne_algo["c"],
        h=ligne_algo["h"],
        hex=oklch_to_hex(OKLCH(L=ligne_algo["l"], C=ligne_algo["c"], H=ligne_algo["h"])),
        algo=algo,
        famille_dominante=ligne_algo["famille_dominante"],
        participation_mediane=row["participation_mediane"],
        scrutins_inclus=[(t, p) for t, p in scrutins],
        repartition=[
            FamilleSynthese(famille=e["famille"], part=e["part"]) for e in repartition
        ],
    )


def fiche_statique(
    row: Mapping[str, Any], lignes_algo: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    """Fiche statique d'une commune : métadonnées + une couleur par algo.

    Contrairement à l'API (repli legacy pour « complet »), une base dont
    couleurs_ville_algo n'est pas peuplée pour TOUS les algos fait échouer
    l'export : publier des fiches partielles casserait l'app en silence.
    """
    manquants = [a for a in ALGOS if a not in lignes_algo]
    if manquants:
        raise RuntimeError(
            f"commune {row['code_insee']} sans couleur pour {', '.join(manquants)} "
            "— relancer compute_couleurs avant l'export"
        )
    return {
        "code_insee": row["code_insee"],
        "nom": row["nom"],
        "departement": row["departement"],
        "region": row["region"],
        "population": row["population"],
        "lat": row["lat"],
        "lon": row["lon"],
        "couleurs": {
            algo: couleur_synthese(row, algo, lignes_algo[algo]).model_dump(mode="json")
            for algo in ALGOS
        },
    }


def charger_couleurs_algo(conn) -> dict[str, dict[str, Mapping[str, Any]]]:
    """couleurs_ville_algo en mémoire : code_insee → {algo: ligne}.

    3 algos × 35 000 communes : même stratégie que dans export_tiles.
    """
    couleurs: dict[str, dict[str, Mapping[str, Any]]] = {}
    for row in conn.execute(_SQL_COULEURS_ALGO).mappings():
        couleurs.setdefault(row["code_insee"], {})[row["algo"]] = dict(row)
    return couleurs


def iter_fiches(conn) -> Iterator[dict[str, Any]]:
    """Itère les fiches statiques des communes ayant une couleur de synthèse."""
    couleurs_algo = charger_couleurs_algo(conn)
    for row in conn.execute(_SQL_FICHES).mappings():
        yield fiche_statique(row, couleurs_algo.get(row["code_insee"], {}))


def _ecrire_json(donnees: Any, chemin: Path) -> None:
    """Écrit un JSON compact UTF-8 (même sérialisation pour tous les artefacts)."""
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(
        json.dumps(donnees, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )


def ecrire_fiches(fiches: Iterable[dict[str, Any]], dossier: Path) -> int:
    """Écrit un `{code_insee}.json` par fiche. Retourne le nombre écrit.

    Le dossier est vidé d'abord : une commune disparue entre deux exports ne
    doit pas laisser un JSON périmé (rclone sync le republierait).
    """
    if dossier.exists():
        shutil.rmtree(dossier)
    dossier.mkdir(parents=True)
    n = 0
    for fiche in fiches:
        _ecrire_json(fiche, dossier / f"{fiche['code_insee']}.json")
        n += 1
    return n


def exporter_nuances() -> dict[str, Any]:
    """Contenu de nuances.json : exactement la réponse de GET /nuances
    (même code de chargement des CSV, cf. api.routers.nuances)."""
    return _charger_nuances().model_dump(mode="json")


def meta_version(nb_communes: int, scrutins: list[str], genere_le: str) -> dict[str, Any]:
    """Contenu de meta/version.json : identité du jeu de données publié."""
    return {
        "schema": SCHEMA_VERSION,
        "genere_le": genere_le,
        "nb_communes": nb_communes,
        "algos": list(ALGOS),
        "scrutins": scrutins,
    }


def copier_glyphes(src: Path, dest: Path) -> int:
    """Copie les glyphes MapLibre (*.pbf) et la licence OFL vers l'export.

    Préserve l'arborescence `{fontstack}/{range}.pbf` attendue par MapLibre.
    Le README du dossier source est de la doc dépôt, pas un artefact à servir.
    Retourne le nombre de .pbf copiés.
    """
    if dest.exists():
        shutil.rmtree(dest)
    n = 0
    for pbf in sorted(src.rglob("*.pbf")):
        cible = dest / pbf.relative_to(src)
        cible.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pbf, cible)
        n += 1
    licence = src / "OFL.txt"
    if licence.exists():
        shutil.copy2(licence, dest / "OFL.txt")
    return n


def main() -> None:
    url = os.environ.get("DATABASE_URL", DEFAUT_DB_URL)
    engine = create_engine(url)
    with engine.connect() as conn:
        n = ecrire_fiches(iter_fiches(conn), EXPORT_DIR / "communes")
        scrutins = [r[0] for r in conn.execute(_SQL_SCRUTINS)]
    if n == 0:
        print("✗ aucune commune — la table couleurs_ville est-elle peuplée ?", file=sys.stderr)
        sys.exit(1)
    print(f"✓ {n} fiches écrites dans {EXPORT_DIR / 'communes'}")

    nuances = exporter_nuances()
    _ecrire_json(nuances, EXPORT_DIR / "nuances.json")
    print(f"✓ nuances.json ({len(nuances['scrutins'])} scrutins classés)")

    genere_le = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _ecrire_json(meta_version(n, scrutins, genere_le), EXPORT_DIR / "meta" / "version.json")
    print(f"✓ meta/version.json (genere_le={genere_le}, scrutins={scrutins})")

    n_pbf = copier_glyphes(FONTS_SRC, EXPORT_DIR / "fonts")
    print(f"✓ {n_pbf} glyphes pbf copiés vers {EXPORT_DIR / 'fonts'}")


if __name__ == "__main__":
    main()
