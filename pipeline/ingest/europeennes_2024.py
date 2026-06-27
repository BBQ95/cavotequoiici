"""Ingestion des résultats des élections européennes du 9 juin 2024 par commune.

Source : data.gouv.fr — Ministère de l'Intérieur
  https://www.data.gouv.fr/fr/datasets/resultats-des-elections-europeennes-du-9-juin-2024/

Le fichier par commune est au format wide : 38 listes en colonnes (panneau 1..38),
chaque panneau occupe 8 colonnes (numéro, nuance, libellé abrégé, libellé, voix,
% inscrits, % exprimés, sièges). On pivote en format long (une ligne par
commune × nuance) puis on insère via pipeline.ingest.common.
"""

from __future__ import annotations

import os
import re
import urllib.request
from pathlib import Path
from typing import Literal, overload

import polars as pl
from sqlalchemy import create_engine

from pipeline.ingest.common import (
    charger_nuances,
    compter_orphelins,
    inserer_resultats,
    upsert_scrutin,
)

SCRUTIN_ID = "europeennes_2024"
SCRUTIN_TYPE = "europeennes"
TOUR = 1
DATE_SCRUTIN = "2024-06-09"
POIDS = 0.7

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
COMMUNE_CSV = DATA_DIR / "europeennes_2024_commune.csv"

# Timestamp de version du fichier sur data.gouv.fr (segment dans l'URL).
# Si data.gouv.fr met à jour le fichier, ce timestamp change et l'URL aussi.
TIMESTAMP_DATA_GOUV = "20240613-154634"

# URL de téléchargement du fichier résultats par commune (data.gouv.fr).
URL_DATA_GOUV = (
    "https://static.data.gouv.fr/resources/"
    "resultats-des-elections-europeennes-du-9-juin-2024/"
    f"{TIMESTAMP_DATA_GOUV}/resultats-definitifs-par-commune.csv"
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
    """Transforme le DataFrame wide (38 listes en colonnes) en format long.

    Colonnes du fichier source :
      - "Code commune", "Libellé commune", "Inscrits", "Exprimés"
      - Pour chaque liste N (1..38) :
        "Nuance liste N", "Voix N"

    Retourne un DataFrame avec colonnes :
      code_insee, nuance, voix, exprimes, inscrits
    (une ligne par commune × nuance, sans les panneaux vides)
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
    rows: list[dict] = []
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
        # Filtrer les panneaux vides (nuance None ou vide)
        sub = sub.filter(pl.col("nuance").is_not_null() & (pl.col("nuance") != ""))
        rows.append(sub)

    if not rows:
        raise ValueError("Aucune colonne de nuance trouvée")

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

    Utile si plusieurs panneau ont la même nuance (théoriquement impossible
    pour les européennes, mais le test le vérifie pour robustesse).

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


def build_lignes_insertion(
    df_long: pl.DataFrame, mapping: dict[str, str]
) -> list[dict]:
    """Filtre les nuances non mappées et prépare les lignes pour inserer_resultats.

    Retourne une liste de dicts avec les colonnes :
    code_insee, nuance, voix, exprimes, inscrits

    Les lignes dont ``code_insee`` est ``None`` (issu d'une normalisation
    non-strict sur un code INSEE invalide) sont également exclues.
    """
    # Filtrer les nuances non mappées
    nuances_valides = set(mapping.keys())
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

    # 1. Télécharger
    csv_path = telecharger_fichier(URL_DATA_GOUV, COMMUNE_CSV)

    # 2. Charger le mapping nuances
    mapping = charger_nuances(SCRUTIN_ID, nuances_dir=NUANCES_DIR)
    print(f"Mapping nuances : {len(mapping)} nuances chargées")

    # 3. Parser le fichier (Polars, UTF-8, séparateur ;)
    print(f"Parsing : {csv_path}")
    df = pl.read_csv(
        str(csv_path),
        separator=";",
        encoding="utf-8",
        infer_schema_length=0,
        quote_char='"',
    )
    print(f"  → {df.shape[0]} lignes, {df.shape[1]} colonnes")

    # 4. Pivoter en format long
    df_long = parse_resultats_commune(df)
    print(f"  → {df_long.shape[0]} lignes (commune × nuance)")

    # 5. Agréger (sécurité : somme si doublons)
    df_agg = aggregate_voix(df_long)
    print(f"  → {df_agg.shape[0]} lignes après agrégation")

    # 6. Préparer les lignes pour l'insertion
    lignes = build_lignes_insertion(df_agg, mapping)
    print(f"  → {len(lignes)} lignes à insérer (après filtrage nuances mappées)")

    # 7. Upsert scrutin
    upsert_scrutin(SCRUTIN_ID, SCRUTIN_TYPE, TOUR, DATE_SCRUTIN, POIDS, engine)
    print(f"Scrutin upserté : {SCRUTIN_ID}")

    # 8. Insérer les résultats
    nb = inserer_resultats(lignes, SCRUTIN_ID, engine)
    print(f"{nb} résultats insérés")

    # 9. Vérifier les orphelins
    orphelins = compter_orphelins(SCRUTIN_ID, engine)
    print(f"Orphelins : {orphelins}")
    if orphelins > 0:
        print(f"ATTENTION : {orphelins} codes INSEE non trouvés dans la table communes")
    else:
        print("✓ Aucun orphelin")


if __name__ == "__main__":
    main()
