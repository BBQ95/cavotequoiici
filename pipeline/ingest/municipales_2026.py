"""Ingestion des résultats des élections municipales du 15 mars 2026 (1er tour) par commune.

Source : data.gouv.fr — Ministère de l'Intérieur
  https://www.data.gouv.fr/fr/datasets/elections-municipales-2026-resultats-du-premier-tour/

Le fichier par commune est au format wide : jusqu'à 13 listes en colonnes,
chaque liste occupe 13 colonnes (numéro de panneau, nom/prénom/sexe candidat,
nuance, libellé abrégé, libellé, voix, %, %, élu, sièges CM, sièges CC).
On pivote en format long (une ligne par commune × nuance) puis on insère
via pipeline.ingest.common.

Format mixte :
  - Communes < 1000 hab. : candidats nominatifs SANS nuance officielle
    (les colonnes « Nuance liste N » sont vides) → voix attribuées à la nuance LUD
    (sans étiquette → famille divers). Ces communes DOIVENT être incluses.
  - Communes ≥ 1000 hab. : listes AVEC nuance officielle → mapper via le CSV.
"""

from __future__ import annotations

import os
import re
import sys
import urllib.request
from pathlib import Path
from typing import Literal, overload

import polars as pl
from sqlalchemy import create_engine

from pipeline.ingest.common import (
    charger_nuances,
    codes_communes,
    compter_orphelins,
    filtrer_communes_connues,
    inserer_resultats,
    upsert_scrutin,
)

SCRUTIN_ID = "municipales_2026_t1"
SCRUTIN_TYPE = "municipales_t1"
TOUR = 1
DATE_SCRUTIN = "2026-03-15"
POIDS = 0.5

# Les communes < 1000 hab. ont des candidats nominatifs SANS nuance officielle :
# les colonnes « Nuance liste N » sont vides dans le fichier source. On attribue
# donc la nuance LUD (sans étiquette → famille divers) à leurs voix dans
# parse_resultats_commune, ce qui les inclut dans l'analyse.
# Voir « Remarques de classification » dans pipeline/config/nuances/README.md.

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
COMMUNE_CSV = DATA_DIR / "municipales_2026_t1_communes.csv"

# Timestamp de version du fichier sur data.gouv.fr (segment dans l'URL).
TIMESTAMP_DATA_GOUV = "20260320-164339"

# URL de téléchargement du fichier résultats par commune (data.gouv.fr, MI).
URL_DATA_GOUV = (
    "https://static.data.gouv.fr/resources/"
    "elections-municipales-2026-resultats-du-premier-tour/"
    f"{TIMESTAMP_DATA_GOUV}/municipales-2026-resultats-communes-2026-03-20.csv"
)

NUANCES_DIR = (
    Path(__file__).resolve().parents[1] / "config" / "nuances"
)


# ──────────────────────────────────────────────────────────────────────────────
# Fonctions pures
# ──────────────────────────────────────────────────────────────────────────────

@overload
def normaliser_code_insee(
    code: str | int | None, *, strict: Literal[True] = True
) -> str: ...


@overload
def normaliser_code_insee(
    code: str | int | None, *, strict: Literal[False]
) -> str | None: ...


def normaliser_code_insee(
    code: str | int | None, *, strict: bool = True
) -> str | None:
    """Normalise un code INSEE en string de 5 caractères (zéro-pad à gauche pour les numériques).

    Gère :
    - Les codes numériques (zero-pad à 5 chiffres)
    - Les codes corses (2Axxx, 2Bxxx) — conservés tels quels
    - Les codes des Français de l'étranger (ZZxxx) et territoires (ZXxxx) — conservés tels quels

    Paramètre ``strict`` :
    - ``strict=True`` (défaut) : lève ``ValueError`` sur code invalide (fail-loud)
    - ``strict=False`` : retourne ``None`` pour les codes invalides (rejet silencieux pour batch)

    >>> normaliser_code_insee("1234")
    '01234'
    >>> normaliser_code_insee(75001)
    '75001'
    >>> normaliser_code_insee("2A001")
    '2A001'
    >>> normaliser_code_insee("ZZ001")
    'ZZ001'
    """
    if code is None or str(code).strip() == "":
        if strict:
            raise ValueError("Code INSEE vide ou None")
        return None
    s = str(code).strip().upper()

    # Codes alphanumériques de 5 caractères (2A, 2B, ZX, ZZ, etc.)
    if len(s) == 5 and not s.isdigit():
        # Vérifier que c'est bien un code INSEE valide (lettres + chiffres)
        if all(c.isalnum() for c in s):
            return s

    # Cas normal : numérique → zero-pad à 5
    try:
        n = int(s)
    except ValueError:
        if strict:
            raise ValueError(f"Code INSEE non valide : {code!r}")
        return None
    if n < 0 or n > 99999:
        if strict:
            raise ValueError(f"Code INSEE hors plage : {code!r}")
        return None
    return f"{n:05d}"


def parse_resultats_commune(df: pl.DataFrame) -> pl.DataFrame:
    """Transforme le DataFrame wide (13 listes en colonnes) en format long.

    Colonnes du fichier source :
      - "Code commune", "Libellé commune", "Inscrits", "Exprimés"
      - Pour chaque liste N (1..13) :
        "Nuance liste N", "Voix N"

    Retourne un DataFrame avec colonnes :
      code_insee, nuance, voix, exprimes, inscrits
    (une ligne par commune × nuance, sans les panneaux vides)

    Note : les communes < 1000 hab. ont des candidats nominatifs sans nuance
    officielle. Pour ne pas les exclure, on attribue la nuance LUD (sans étiquette,
    famille divers) aux voix qui n'ont pas de nuance. Ces voix sont ensuite
    agrégées par commune sous la nuance LUD.
    """
    # Identifier les colonnes de nuances et de voix, en extrayant le numéro N
    nuance_cols = {}
    for c in df.columns:
        if c.startswith("Nuance liste "):
            m = re.search(r"Nuance liste (\d+)", c)
            if m:
                nuance_cols[int(m.group(1))] = c

    voix_cols = {}
    for c in df.columns:
        if c.startswith("Voix "):
            m = re.search(r"Voix (\d+)", c)
            if m:
                voix_cols[int(m.group(1))] = c

    # Apparier explicitement nuance↔voix par le numéro N
    rows: list[pl.DataFrame] = []
    for n in sorted(nuance_cols.keys()):
        nc = nuance_cols[n]
        vc = voix_cols.get(n)
        if vc is None:
            continue  # pas de colonne Voix N correspondante
        sub = df.select(
            pl.col("Code commune").alias("code_insee_raw"),
            pl.col(nc).alias("nuance"),
            pl.col(vc).alias("voix_raw"),
            pl.col("Exprimés").alias("exprimes_raw"),
            pl.col("Inscrits").alias("inscrits_raw"),
        )
        # Filtrer les panneaux vides :
        # - Panneau vide = nuance vide ET voix vide/nulle
        # - Si nuance vide MAIS voix > 0 → candidat nominatif sans nuance officielle
        #   (commune < 1000 hab.) → attribuer la nuance LUD (sans étiquette → divers)
        has_nuance = pl.col("nuance").is_not_null() & (pl.col("nuance") != "")
        voix_val = pl.col("voix_raw").cast(pl.Int64, strict=False).fill_null(0) > 0

        # Panneaux réellement vides : ni nuance, ni voix
        sub = sub.filter(has_nuance | voix_val)

        # Pour les lignes sans nuance mais avec voix → LUD
        sub = sub.with_columns(
            pl.when(~has_nuance)
            .then(pl.lit("LUD"))
            .otherwise(pl.col("nuance"))
            .alias("nuance")
        )
        rows.append(sub)

    if not rows:
        # Aucune colonne de nuance trouvée → DataFrame vide avec bonnes colonnes
        return pl.DataFrame(
            schema={
                "code_insee": pl.Utf8,
                "nuance": pl.Utf8,
                "voix": pl.Int64,
                "exprimes": pl.Int64,
                "inscrits": pl.Int64,
            }
        )

    long_df = pl.concat(rows, how="vertical")

    # Normaliser code INSEE
    long_df = long_df.with_columns(
        long_df["code_insee_raw"].map_elements(
            lambda x: normaliser_code_insee(x, strict=False),
            return_dtype=pl.Utf8,
        ).alias("code_insee")
    )

    # Convertir voix, exprimes, inscrits en entiers
    long_df = long_df.with_columns(
        pl.col("voix_raw").cast(pl.Int64, strict=False).fill_null(0).alias("voix"),
        pl.col("exprimes_raw").cast(pl.Int64, strict=False).fill_null(0).alias("exprimes"),
        pl.col("inscrits_raw").cast(pl.Int64, strict=False).fill_null(0).alias("inscrits"),
    )

    # Sélectionner les colonnes finales
    result = long_df.select(
        ["code_insee", "nuance", "voix", "exprimes", "inscrits"]
    )

    return result


def aggregate_voix(df: pl.DataFrame) -> pl.DataFrame:
    """Agrège les voix par (code_insee, nuance) en sommant.

    Utile si plusieurs panneaux ont la même nuance (possible dans les municipales
    si deux listes de même nuance se présentent dans la même commune, bien que
    théoriquement rare).

    Garde exprimes et inscrits au niveau commune (max, car constant par commune).
    """
    agg = df.group_by(["code_insee", "nuance"]).agg(
        pl.col("voix").sum().alias("voix"),
        pl.col("exprimes").max().alias("exprimes"),
        pl.col("inscrits").max().alias("inscrits"),
    )
    return agg


# ──────────────────────────────────────────────────────────────────────────────
# Pipeline principal
# ──────────────────────────────────────────────────────────────────────────────

def telecharger_fichier(url: str, dest: Path) -> Path:
    """Télécharge le fichier si absent localement."""
    if dest.exists():
        print(f"Fichier déjà présent : {dest}")
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"Téléchargement : {url}")
    urllib.request.urlretrieve(url, dest)
    print(f"  → {dest} ({dest.stat().st_size / 1e6:.1f} MB)")
    return dest


# Colonnes obligatoires du fichier source (hors colonnes de listes « Nuance liste N » / « Voix N »
# qui sont détectées dynamiquement par parse_resultats_commune).
COLONNES_OBLIGATOIRES = ["Code commune", "Exprimés", "Inscrits"]


def verifier_colonnes(df: pl.DataFrame) -> None:
    """Vérifie que les colonnes attendues sont présentes dans le DataFrame.

    Lève ``ValueError`` avec un message clair si une colonne obligatoire manque.
    Les colonnes « Nuance liste N » et « Voix N » ne sont pas vérifiées ici :
    elles sont détectées dynamiquement par ``parse_resultats_commune`` (le nombre
    de listes varie selon le scrutin).

    >>> verifier_colonnes(pl.DataFrame({"Code commune": [], "Exprimés": [], "Inscrits": []}))
    """
    colonnes_presentes = set(df.columns)
    manquantes = [c for c in COLONNES_OBLIGATOIRES if c not in colonnes_presentes]
    if manquantes:
        raise ValueError(
            f"Colonnes manquantes: {manquantes}. "
            f"Colonnes trouvées: {list(df.columns)}"
        )


def lire_csv_robuste(csv_path: Path, separator: str = ";") -> pl.DataFrame:
    """Lit un CSV en essayant utf-8, puis latin-1 (ISO-8859-1) en fallback.

    Les fichiers du Ministère de l'Intérieur sont parfois en ISO-8859-1/Windows-1252.
    On tente d'abord UTF-8 (encodage le plus courant) ; si la lecture échoue
    (UnicodeDecodeError ou caractères corrompus), on retente en latin-1.

    Retourne un DataFrame Polars avec toutes les colonnes en chaînes de caractères
    (infer_schema_length=0) pour éviter les problèmes de typage des pourcentages
    (ex. « 55,08% »).

    >>> lire_csv_robuste(Path("data/municipales_2026_t1_communes.csv"))  # doctest: +SKIP
    """
    common_kwargs = dict(
        separator=separator,
        infer_schema_length=0,
        quote_char='"',
    )
    try:
        return pl.read_csv(str(csv_path), encoding="utf-8", **common_kwargs)
    except (pl.exceptions.ComputeError, UnicodeDecodeError):
        print(f"  ⚠️ Lecture UTF-8 échouée, retry en latin-1 (ISO-8859-1)…")
        return pl.read_csv(str(csv_path), encoding="latin1", **common_kwargs)


def build_lignes_insertion(
    df_long: pl.DataFrame, mapping: dict[str, str]
) -> list[dict]:
    """Filtre les nuances non mappées et prépare les lignes pour inserer_resultats.

    Retourne une liste de dicts avec les colonnes :
    code_insee, nuance, voix, exprimes, inscrits

    Les lignes dont ``code_insee`` est ``None`` (issu d'une normalisation
    non-strict sur un code INSEE invalide) sont également exclues.

    Garde-fou (fail-loud) : si les données contiennent des nuances absentes
    du mapping, on lève une ``SystemExit`` avec le volume de voix concerné
    plutôt que d'écarter silencieusement ces voix (cf. legislatives_2024.py).
    """
    # Détecter les nuances non mappées avant filtrage (fail-loud)
    nuances_valides = set(mapping.keys())
    nuances_presentes = set(df_long["nuance"].unique().to_list())
    nuances_manquantes = nuances_presentes - nuances_valides
    if nuances_manquantes:
        voix_perdues = df_long.filter(
            df_long["nuance"].is_in(nuances_manquantes)
        )["voix"].sum()
        sys.exit(
            f"⛔ nuances sans famille dans {SCRUTIN_ID}.csv : "
            f"{sorted(nuances_manquantes)} "
            f"({voix_perdues} voix écartées)"
        )

    # Filtrer les nuances non mappées (toutes mappées à ce stade)
    df_filtre = df_long.filter(df_long["nuance"].is_in(nuances_valides))

    # Exclure les lignes dont le code INSEE est None (mode non-strict)
    df_filtre = df_filtre.filter(pl.col("code_insee").is_not_null())

    # Convertir en liste de dicts
    lignes = df_filtre.to_dicts()
    return lignes


def main() -> None:
    """Point d'entrée : télécharge, parse, insère."""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL non définie. Exportez-la avant de lancer l'ingestion.")
    engine = create_engine(database_url)

    # ──────────────────────────────────────────────────────────────────────
    # Inclusion des communes < 1000 hab.
    # ──────────────────────────────────────────────────────────────────────
    # Les communes de moins de 1000 habitants ont des candidats nominatifs SANS
    # nuance officielle (les colonnes « Nuance liste N » sont vides dans le
    # fichier source). La spec exige qu'elles soient INCLUSES, pas exclues.
    # On attribue donc la nuance LUD (sans étiquette → famille divers) à leurs
    # voix dans parse_resultats_commune. Ces communes apparaissent dans les
    # résultats avec famille = divers.
    # ──────────────────────────────────────────────────────────────────────

    # 1. Télécharger
    csv_path = telecharger_fichier(URL_DATA_GOUV, COMMUNE_CSV)

    # 2. Charger le mapping nuances
    mapping = charger_nuances(SCRUTIN_ID, nuances_dir=NUANCES_DIR)
    print(f"Mapping nuances : {len(mapping)} nuances chargées")

    # 3. Parser le fichier (Polars, séparateur ;)
    #    L'encodage est détecté automatiquement : utf-8 d'abord, latin-1 en fallback
    #    (les fichiers du MI sont parfois en ISO-8859-1/Windows-1252).
    print(f"Parsing : {csv_path}")
    df = lire_csv_robuste(csv_path)
    print(f"  → {df.shape[0]} lignes, {df.shape[1]} colonnes")

    # 3b. Vérifier que les colonnes attendues sont présentes (fail-loud)
    verifier_colonnes(df)

    # 4. Pivoter en format long
    #    Les communes < 1000 hab. sont INCLUSES : les candidats nominatifs
    #    sans nuance officielle se voient attribuer la nuance LUD
    #    (sans étiquette → famille divers) dans parse_resultats_commune.
    #    Impact : la famille « divers » est gonflée dans tout le rural
    #    (≈ 25 000 communes < 1000 hab. sur ~35 000 au total), mais les
    #    résultats ne sont pas perdus — voir « Remarques de classification »
    #    dans pipeline/config/nuances/README.md.
    df_long = parse_resultats_commune(df)
    print(f"  → {df_long.shape[0]} lignes (commune × nuance)")

    # 5. Agréger (sécurité : somme si doublons)
    df_agg = aggregate_voix(df_long)
    print(f"  → {df_agg.shape[0]} lignes après agrégation")

    # 6. Préparer les lignes pour l'insertion
    lignes = build_lignes_insertion(df_agg, mapping)
    print(f"  → {len(lignes)} lignes à insérer (après filtrage nuances mappées)")

    # 7. Écarter les communes hors contours (étranger ZZ/ZX, fusions) — sinon la
    #    contrainte de clé étrangère sur resultats_scrutin fait échouer l'insertion.
    connus = codes_communes(engine)
    lignes, orphelins = filtrer_communes_connues(lignes, connus)
    if orphelins:
        ex = ", ".join(sorted(orphelins)[:10])
        print(f"⚠️ {len(orphelins)} communes ignorées (hors contours) : {ex}…")

    # 8. Upsert scrutin
    upsert_scrutin(SCRUTIN_ID, SCRUTIN_TYPE, TOUR, DATE_SCRUTIN, POIDS, engine)
    print(f"Scrutin upserté : {SCRUTIN_ID}")

    # 9. Insérer les résultats
    nb = inserer_resultats(lignes, SCRUTIN_ID, engine)
    print(f"{nb} résultats insérés")

    # 10. Vérifier qu'il ne reste aucun orphelin
    orphelins = compter_orphelins(SCRUTIN_ID, engine)
    print(f"Orphelins : {orphelins}")
    if orphelins > 0:
        print(f"ATTENTION : {orphelins} codes INSEE non trouvés dans la table communes")
    else:
        print("✓ Aucun orphelin")


if __name__ == "__main__":
    main()
