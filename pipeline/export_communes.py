"""pipeline/export_communes.py — Export statique des fiches communes.

Produit l'arborescence servie par `data.cavotequoiici.fr` (bucket R2 derrière
le CDN Cloudflare), pour que l'app n'ait plus besoin de l'API en production :

    export/
    ├── communes/{insee}.json   fiche par commune : 3 algos + scrutins embarqués
    ├── index/communes.json     index compact de recherche/géoloc côté client
    ├── nuances.json            réponse de GET /nuances, figée
    ├── meta/version.json       version des données (cache-busting côté app)
    └── fonts/…                 glyphes MapLibre ({fontstack}/{range}.pbf)

Chaque fiche embarque une `CouleurSynthese` par algo de dominance (l'endpoint
`/communes/{insee}` la sert via `?algo=` ; en statique, le client choisit la
clé dans `couleurs`) et la clé `scrutins` (liste + détail par scrutin — les
deux endpoints du routeur scrutins fusionnés, pour l'encart Transparence).
Les formes des artefacts sont décrites par les schémas Pydantic de
`pipeline.schemas.*` (source unique, miroir des types TS du mobile) — même
source unique de conversion `oklch_to_hex` que les tuiles.

L'index de recherche remplace `GET /communes/search` et `/communes/proximite`
côté app : entrées compactes (nom, dpt, lat/lon, pastilles par algo), nom
normalisé recalculé côté client (parité : tests/fixtures/normalisation_parite.json).

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

from pipeline.schemas.communes import CouleurSynthese, FamilleSynthese
from pipeline.schemas.nuances import NuanceClassee, NuancesResponse, ScrutinNuances
from pipeline.schemas.scrutins import (
    CouleurScrutin,
    DetailScrutinResponse,
    FamilleVoix,
    ScrutinInclus,
)
from pipeline.couleur import ALGOS, OKLCH, oklch_to_hex
from pipeline.ingest.common import NUANCES_DIR, charger_nuances, charger_nuances_completes
from pipeline.jsoncol import decode_json_col
from pipeline.synthese import TYPE_LONG_VERS_COURT

DEFAUT_DB_URL = "postgresql+psycopg2://postgres:cavote@localhost:5432/postgres"

RACINE = Path(__file__).resolve().parent.parent
EXPORT_DIR = RACINE / "export"
FONTS_SRC = RACINE / "pipeline" / "fonts"

# Version du schéma des artefacts statiques (fiches + version.json). À
# incrémenter à chaque changement de forme incompatible côté app.
SCHEMA_VERSION = 1

# Fiche complète par commune : métadonnées + synthèse + point représentatif
# lat/lon. ORDER BY : sans lui l'ordre des lignes suit le plan Postgres (scan
# parallèle) et change d'un run à l'autre — l'index serait réordonné à chaque
# export et la synchro R2 re-téléverserait un fichier fonctionnellement
# identique. Le contenu des fiches ne dépend pas de cet ordre.
_SQL_FICHES = text(
    """
    SELECT c.code_insee, c.nom, c.departement, c.region, c.population,
           cv.participation_mediane, cv.scrutins_inclus, cv.repartition,
           ST_Y(ST_Transform(ST_PointOnSurface(c.geom), 4326)) AS lat,
           ST_X(ST_Transform(ST_PointOnSurface(c.geom), 4326)) AS lon
    FROM communes c
    JOIN couleurs_ville cv ON cv.code_insee = c.code_insee
    ORDER BY c.code_insee
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

# Métadonnées des scrutins (jointure type long → type court comme le routeur
# scrutins : seul le type court apparaît dans couleurs_ville.scrutins_inclus).
_SQL_SCRUTINS_META = text("SELECT id, type, date FROM scrutins")

# Couleur + participation par (commune, scrutin) — source du détail embarqué.
_SQL_COULEURS_SCRUTIN = text(
    "SELECT code_insee, scrutin_id, l, c, h, participation FROM couleurs_scrutin"
)

# Résultats bruts par nuance, agrégés en familles côté Python (le mapping
# nuance → famille vit dans les CSV, pas en base). ~1,4 M lignes, streamées.
_SQL_RESULTATS = text(
    "SELECT code_insee, scrutin_id, nuance, voix, exprimes FROM resultats_scrutin"
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


def _verifier_algos(
    row: Mapping[str, Any], lignes_algo: Mapping[str, Mapping[str, Any]]
) -> None:
    """Échec explicite si un algo manque : contrairement à l'API (repli legacy
    pour « complet »), publier des artefacts partiels casserait l'app en
    silence — une base pas recalculée doit faire échouer l'export."""
    manquants = [a for a in ALGOS if a not in lignes_algo]
    if manquants:
        raise RuntimeError(
            f"commune {row['code_insee']} sans couleur pour {', '.join(manquants)} "
            "— relancer compute_couleurs avant l'export"
        )


def fiche_statique(
    row: Mapping[str, Any],
    lignes_algo: Mapping[str, Mapping[str, Any]],
    scrutins: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Fiche statique d'une commune : métadonnées + une couleur par algo
    + scrutins embarqués (cf. scrutins_fiche). La clé `scrutins` existe
    toujours, même vide (contrat du client statique)."""
    _verifier_algos(row, lignes_algo)
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
        "scrutins": scrutins or [],
    }


def _finaliser_familles(
    voix_par_famille: Mapping[str, int], exprimes: int
) -> list[dict[str, Any]]:
    """Liste FamilleVoix triée. Tri (-voix, famille) : le routeur scrutins ne
    trie que par voix décroissantes (ordre SQL stable pour les égalités) —
    le tiebreak alphabétique rend l'export déterministe, divergence possible
    uniquement sur une égalité parfaite de voix."""
    return [
        {
            "famille": famille,
            "voix": voix,
            "pourcentage": round(voix / exprimes, 6) if exprimes > 0 else 0.0,
        }
        for famille, voix in sorted(voix_par_famille.items(), key=lambda kv: (-kv[1], kv[0]))
    ]


def familles_depuis_resultats(
    lignes: Iterable[tuple[str, int, int]], mapping: Mapping[str, str]
) -> list[dict[str, Any]]:
    """Agrège des lignes (nuance, voix, exprimes) en familles — même logique
    que GET /communes/{insee}/scrutins/{id} : nuance non mappée ignorée,
    exprimés constants par scrutin, pourcentage arrondi à 6 décimales."""
    voix_par_famille: dict[str, int] = {}
    exprimes = 0
    for nuance, voix, expr in lignes:
        exprimes = expr
        famille = mapping.get(nuance)
        if famille is None:
            continue
        voix_par_famille[famille] = voix_par_famille.get(famille, 0) + voix
    return _finaliser_familles(voix_par_famille, exprimes)


def scrutins_fiche(
    row: Mapping[str, Any],
    scrutins_meta: Mapping[str, tuple[str, str]],
    couleurs_scrutin_commune: Mapping[str, Mapping[str, Any]],
    familles_commune: Mapping[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Scrutins embarqués d'une fiche : parité avec les deux endpoints du
    routeur scrutins, fusionnés.

    Chaque entrée = ScrutinInclus (GET /communes/{insee}/scrutins) + une clé
    `detail` = DetailScrutinResponse (GET …/scrutins/{id}), ou `None` si le
    scrutin n'a pas de couleur pour la commune (participation nulle — le
    404 maîtrisé du routeur). Un type absent de la table scrutins n'émet
    pas d'entrée, comme au routeur.
    """
    entrees = []
    for type_court, poids in decode_json_col(row["scrutins_inclus"]) or []:
        info = scrutins_meta.get(type_court)
        if info is None:
            continue
        scrutin_id, date = info
        cs = couleurs_scrutin_commune.get(scrutin_id)
        detail = None
        if cs is not None:
            detail = DetailScrutinResponse(
                insee=row["code_insee"],
                scrutin_id=scrutin_id,
                familles=[FamilleVoix(**f) for f in familles_commune.get(scrutin_id, [])],
                participation=cs["participation"],
                couleur=CouleurScrutin(l=cs["l"], c=cs["c"], h=cs["h"]),
            ).model_dump(mode="json")
        entree = ScrutinInclus(
            scrutin_id=scrutin_id, type=type_court, date=date, poids_relatif=poids
        ).model_dump(mode="json")
        entree["detail"] = detail
        entrees.append(entree)
    return entrees


def entree_index(
    row: Mapping[str, Any],
    lignes_algo: Mapping[str, Mapping[str, Any]],
    legende: dict[str, int],
) -> list[Any]:
    """Entrée compacte de l'index de recherche :
    [insee, nom, departement, lat, lon, [hex par algo], [famille indexée par algo]].

    `legende` (famille → indice) est enrichie au passage (setdefault) — les
    familles y sont indexées à leur première apparition. lat/lon arrondis à
    5 décimales (~1 m) : suffisant pour la géoloc, économise l'index.
    Le nom normalisé n'est PAS embarqué : le client le recalcule (port TS de
    normaliser_nom, parité testée via tests/fixtures/normalisation_parite.json).
    """
    _verifier_algos(row, lignes_algo)
    hexes: list[str] = []
    familles: list[int | None] = []
    for algo in ALGOS:
        ligne = lignes_algo[algo]
        hexes.append(oklch_to_hex(OKLCH(L=ligne["l"], C=ligne["c"], H=ligne["h"])))
        famille = ligne["famille_dominante"]
        familles.append(None if famille is None else legende.setdefault(famille, len(legende)))
    lat, lon = row["lat"], row["lon"]
    return [
        row["code_insee"],
        row["nom"],
        row["departement"],
        round(lat, 5) if lat is not None else None,
        round(lon, 5) if lon is not None else None,
        hexes,
        familles,
    ]


def construire_index(
    paires: Iterable[tuple[Mapping[str, Any], Mapping[str, Mapping[str, Any]]]],
) -> dict[str, Any]:
    """Index de recherche complet : {"algos", "familles" (légende), "communes"}.

    L'ordre de `algos` fixe celui des listes hex/famille de chaque entrée.
    """
    legende: dict[str, int] = {}
    communes = [entree_index(row, lignes_algo, legende) for row, lignes_algo in paires]
    familles = [f for f, _ in sorted(legende.items(), key=lambda kv: kv[1])]
    return {"algos": list(ALGOS), "familles": familles, "communes": communes}


def charger_couleurs_algo(conn) -> dict[str, dict[str, Mapping[str, Any]]]:
    """couleurs_ville_algo en mémoire : code_insee → {algo: ligne}.

    3 algos × 35 000 communes : même stratégie que dans export_tiles.
    """
    couleurs: dict[str, dict[str, Mapping[str, Any]]] = {}
    for row in conn.execute(_SQL_COULEURS_ALGO).mappings():
        couleurs.setdefault(row["code_insee"], {})[row["algo"]] = dict(row)
    return couleurs


def charger_scrutins_meta(conn) -> dict[str, tuple[str, str]]:
    """Table scrutins indexée par type court : {type_court: (scrutin_id, date)}.

    Même jointure TYPE_LONG_VERS_COURT que le routeur scrutins (un type long hors
    panier est ignoré).
    """
    meta: dict[str, tuple[str, str]] = {}
    for scrutin_id, type_long, date in conn.execute(_SQL_SCRUTINS_META):
        type_court = TYPE_LONG_VERS_COURT.get(type_long)
        if type_court:
            meta[type_court] = (scrutin_id, str(date) if date else None)
    return meta


def charger_couleurs_scrutin(conn) -> dict[str, dict[str, Mapping[str, Any]]]:
    """couleurs_scrutin en mémoire : code_insee → {scrutin_id: ligne l/c/h/participation}."""
    couleurs: dict[str, dict[str, Mapping[str, Any]]] = {}
    for row in conn.execute(_SQL_COULEURS_SCRUTIN).mappings():
        couleurs.setdefault(row["code_insee"], {})[row["scrutin_id"]] = dict(row)
    return couleurs


def charger_familles_scrutin(conn) -> dict[str, dict[str, list[dict[str, Any]]]]:
    """Familles agrégées : code_insee → {scrutin_id: liste FamilleVoix}.

    Streame resultats_scrutin (~1,4 M lignes) en accumulant les voix par
    famille (mapping nuance → famille chargé une fois par scrutin depuis les
    CSV — un CSV absent lève FileNotFoundError : config cassée, échec voulu).
    """
    mappings: dict[str, Mapping[str, str]] = {}
    # (insee, scrutin_id) → ({famille: voix}, exprimes)
    acc: dict[tuple[str, str], tuple[dict[str, int], int]] = {}
    for insee, scrutin_id, nuance, voix, exprimes in conn.execute(_SQL_RESULTATS):
        if scrutin_id not in mappings:
            mappings[scrutin_id] = charger_nuances(scrutin_id)
        voix_par_famille, _ = acc.setdefault((insee, scrutin_id), ({}, 0))
        acc[(insee, scrutin_id)] = (voix_par_famille, exprimes)
        famille = mappings[scrutin_id].get(nuance)
        if famille is not None:
            voix_par_famille[famille] = voix_par_famille.get(famille, 0) + voix
    familles: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for (insee, scrutin_id), (voix_par_famille, exprimes) in acc.items():
        familles.setdefault(insee, {})[scrutin_id] = _finaliser_familles(
            voix_par_famille, exprimes
        )
    return familles


def _ecrire_json(donnees: Any, chemin: Path) -> None:
    """Écrit un JSON compact UTF-8 (même sérialisation pour tous les artefacts).

    Écriture atomique (temporaire dans le même dossier puis os.replace) : un
    crash ne laisse jamais un artefact tronqué sous son nom final.
    """
    chemin.parent.mkdir(parents=True, exist_ok=True)
    tmp = chemin.with_name(chemin.name + ".tmp")
    tmp.write_text(
        json.dumps(donnees, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    os.replace(tmp, chemin)


def _remplacer_dossier(tampon: Path, dossier: Path) -> None:
    """Substitue `dossier` par `tampon` (construit à côté, même filesystem).

    os.replace ne remplace pas un dossier non vide : la fenêtre rmtree→rename
    n'est pas strictement atomique, mais elle est réduite à quelques
    millisecondes — contre des minutes d'écriture pour ~35 000 fiches. Suffisant
    ici : export/ n'est pas servi directement, c'est rclone qui publie.
    """
    if dossier.exists():
        shutil.rmtree(dossier)
    os.replace(tampon, dossier)


def _dossier_tampon(dossier: Path) -> Path:
    """Dossier frère `<nom>.tmp`, reconstruit de zéro (reliquat de crash purgé)."""
    tampon = dossier.with_name(dossier.name + ".tmp")
    if tampon.exists():
        shutil.rmtree(tampon)
    tampon.mkdir(parents=True)
    return tampon


def ecrire_fiches(fiches: Iterable[dict[str, Any]], dossier: Path) -> int:
    """Écrit un `{code_insee}.json` par fiche. Retourne le nombre écrit.

    Le dossier final est intégralement remplacé : une commune disparue entre
    deux exports ne doit pas laisser un JSON périmé (rclone sync le
    republierait). Toute la partie risquée (itération BDD) écrit dans un
    tampon : un échec en cours laisse l'export précédent intact.
    """
    tampon = _dossier_tampon(dossier)
    n = 0
    for fiche in fiches:
        _ecrire_json(fiche, tampon / f"{fiche['code_insee']}.json")
        n += 1
    _remplacer_dossier(tampon, dossier)
    return n


def _verifier_homogeneite(lignes: list[dict[str, Any]], nom_fichier: str) -> None:
    """Un CSV de nuances décrit UN scrutin : ses champs scrutin-level doivent
    être identiques sur toutes les lignes. `_charger_toutes_nuances` ne lit que
    la première — sans ce garde-fou, une divergence passerait silencieusement.
    """
    for champ in ("scrutin_type", "annee", "date_classification"):
        valeurs = {l[champ] for l in lignes}
        if len(valeurs) > 1:
            raise ValueError(
                f"{nom_fichier}: champ '{champ}' hétérogène "
                f"({sorted(map(str, valeurs))}) — un CSV de nuances décrit UN scrutin"
            )


def _charger_toutes_nuances() -> NuancesResponse:
    """Toutes les grilles nuance → famille, une entrée par CSV versionné de
    pipeline/config/nuances/ (source unique — l'écran mobile « D'où viennent
    les familles ? » lit le nuances.json qui en découle)."""
    scrutins = []
    for path in NUANCES_DIR.glob("*.csv"):
        scrutin_id = path.stem
        lignes = charger_nuances_completes(scrutin_id)
        _verifier_homogeneite(lignes, path.name)
        scrutins.append(
            ScrutinNuances(
                scrutin_id=scrutin_id,
                # Type court (celui que le mobile sait libeller) ; fallback
                # identité purement défensif pour un futur type hors panier.
                type=TYPE_LONG_VERS_COURT.get(lignes[0]["scrutin_type"],
                                         lignes[0]["scrutin_type"]),
                annee=lignes[0]["annee"],
                date_classification=lignes[0]["date_classification"],
                nuances=[
                    NuanceClassee(
                        nuance=l["nuance"],
                        famille=l["famille"],
                        source=l["source"],
                        statut=l["statut"],
                    )
                    for l in lignes
                ],
            )
        )
    scrutins.sort(key=lambda s: (-s.annee, s.scrutin_id))
    return NuancesResponse(scrutins=scrutins)


def exporter_nuances() -> dict[str, Any]:
    """Contenu de nuances.json : les grilles officielles, figées à l'export."""
    return _charger_toutes_nuances().model_dump(mode="json")


def meta_version(
    nb_communes: int, scrutins: list[str], genere_le: str, nb_index: int
) -> dict[str, Any]:
    """Contenu de meta/version.json : identité du jeu de données publié.

    `nb_index` (entrées de index/communes.json) est un ajout rétro-compatible :
    le schéma reste 1 (clé additive, aucun champ existant ne change).
    """
    return {
        "schema": SCHEMA_VERSION,
        "genere_le": genere_le,
        "nb_communes": nb_communes,
        "algos": list(ALGOS),
        "scrutins": scrutins,
        "nb_index": nb_index,
    }


def copier_glyphes(src: Path, dest: Path) -> int:
    """Copie les glyphes MapLibre (*.pbf) et la licence OFL vers l'export.

    Préserve l'arborescence `{fontstack}/{range}.pbf` attendue par MapLibre.
    Le README du dossier source est de la doc dépôt, pas un artefact à servir.
    Retourne le nombre de .pbf copiés. Même remplacement par tampon que
    `ecrire_fiches` : un échec en cours laisse les glyphes précédents intacts.
    """
    tampon = _dossier_tampon(dest)
    n = 0
    for pbf in sorted(src.rglob("*.pbf")):
        cible = tampon / pbf.relative_to(src)
        cible.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pbf, cible)
        n += 1
    licence = src / "OFL.txt"
    if licence.exists():
        shutil.copy2(licence, tampon / "OFL.txt")
    _remplacer_dossier(tampon, dest)
    return n


def main() -> None:
    url = os.environ.get("DATABASE_URL", DEFAUT_DB_URL)
    engine = create_engine(url)
    with engine.connect() as conn:
        couleurs_algo = charger_couleurs_algo(conn)
        scrutins_meta = charger_scrutins_meta(conn)
        couleurs_scrutin = charger_couleurs_scrutin(conn)
        familles = charger_familles_scrutin(conn)
        # Les lignes sont petites (pas de géométrie) : on les garde pour
        # construire l'index de recherche dans la même passe que les fiches.
        paires: list[tuple[Mapping[str, Any], Mapping[str, Mapping[str, Any]]]] = []

        def _fiches() -> Iterator[dict[str, Any]]:
            for row in conn.execute(_SQL_FICHES).mappings():
                insee = row["code_insee"]
                lignes_algo = couleurs_algo.get(insee, {})
                paires.append((row, lignes_algo))
                yield fiche_statique(
                    row,
                    lignes_algo,
                    scrutins=scrutins_fiche(
                        row,
                        scrutins_meta,
                        couleurs_scrutin.get(insee, {}),
                        familles.get(insee, {}),
                    ),
                )

        n = ecrire_fiches(_fiches(), EXPORT_DIR / "communes")
        scrutins = [r[0] for r in conn.execute(_SQL_SCRUTINS)]
    if n == 0:
        print("✗ aucune commune — la table couleurs_ville est-elle peuplée ?", file=sys.stderr)
        sys.exit(1)
    print(f"✓ {n} fiches écrites dans {EXPORT_DIR / 'communes'}")

    index = construire_index(paires)
    _ecrire_json(index, EXPORT_DIR / "index" / "communes.json")
    print(
        f"✓ index/communes.json ({len(index['communes'])} entrées, "
        f"{len(index['familles'])} familles)"
    )

    nuances = exporter_nuances()
    _ecrire_json(nuances, EXPORT_DIR / "nuances.json")
    print(f"✓ nuances.json ({len(nuances['scrutins'])} scrutins classés)")

    genere_le = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _ecrire_json(
        meta_version(n, scrutins, genere_le, nb_index=len(index["communes"])),
        EXPORT_DIR / "meta" / "version.json",
    )
    print(f"✓ meta/version.json (genere_le={genere_le}, scrutins={scrutins})")

    n_pbf = copier_glyphes(FONTS_SRC, EXPORT_DIR / "fonts")
    print(f"✓ {n_pbf} glyphes pbf copiés vers {EXPORT_DIR / 'fonts'}")


if __name__ == "__main__":
    main()
