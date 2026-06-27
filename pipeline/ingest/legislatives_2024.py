"""Ingestion des élections législatives 2024, 1er tour (Étape 2).

Source : data.gouv.fr (ministère de l'Intérieur), résultats par commune au format
**large** (séparateur `;`, UTF-8) : colonnes fixes de commune + 204 blocs candidat
de 9 colonnes (`Numéro de panneau N`, `Nuance candidat N`, …, `Voix N`, …).

La nuance officielle figure directement dans le fichier (`Nuance candidat N`) ; la
grille est fixée par l'instruction du 11 juin 2024 (Légifrance id/45565). Le code
INSEE est porté tel quel par `Code commune` (normalisé en 5 caractères) ; Paris/Lyon/
Marseille y sont déjà **consolidés** (75056/69123/13055). Les communes « étranger »
(`ZZ…`, votes des Français de l'étranger) sont écartées au chargement (orphelines).

Usage :
    DATABASE_URL=postgresql+psycopg2://postgres:cavote@localhost:5432/postgres \\
    python -m pipeline.ingest.legislatives_2024
"""

from __future__ import annotations

import os
from pathlib import Path

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

SCRUTIN_ID = "legislatives_2024_t1"
TYPE_SCRUTIN = "legislatives_t1"
TOUR = 1
DATE = "2024-06-30"
POIDS_BRUT = 0.8

URL_SOURCE = "https://www.data.gouv.fr/api/1/datasets/r/bd32fcd3-53df-47ac-bf1d-8d8003fe23a1"
DEFAUT_CSV = "data/legislatives_2024_t1_communes.csv"
DEFAUT_DB_URL = "postgresql+psycopg2://postgres:cavote@localhost:5432/postgres"

MAX_CANDIDATS = 204  # nombre de blocs candidat dans le fichier (colonnes "… N")


def normaliser_insee(expr: pl.Expr) -> pl.Expr:
    """Code commune -> INSEE 5 caractères (zéro-paddé, majuscule)."""
    return expr.str.strip_chars().str.to_uppercase().str.zfill(5)


def agreger_resultats(df: pl.DataFrame, max_candidats: int = MAX_CANDIDATS) -> pl.DataFrame:
    """Dépivote les blocs candidat et agrège en (code_insee, nuance, voix, exprimes, inscrits).

    Somme les voix par (commune, nuance) ; exprimés/inscrits sont des totaux communaux
    (répétés sur chaque bloc) repris une seule fois.
    """
    insee = normaliser_insee(pl.col("Code commune")).alias("code_insee")
    parts = []
    for n in range(1, max_candidats + 1):
        ncol, vcol = f"Nuance candidat {n}", f"Voix {n}"
        if ncol not in df.columns:
            break
        parts.append(
            df.select(
                [
                    insee,
                    pl.col("Inscrits").alias("inscrits"),
                    pl.col("Exprimés").alias("exprimes"),
                    pl.col(ncol).str.strip_chars().alias("nuance"),
                    pl.col(vcol).alias("voix"),
                ]
            )
        )
    long = pl.concat(parts).filter(
        pl.col("nuance").is_not_null() & (pl.col("nuance") != "")
    )
    long = long.with_columns(
        [
            pl.col("voix").cast(pl.Int64),
            pl.col("inscrits").cast(pl.Int64),
            pl.col("exprimes").cast(pl.Int64),
        ]
    )
    voix = long.group_by(["code_insee", "nuance"]).agg(
        pl.col("voix").sum().alias("voix")
    )
    meta = long.group_by("code_insee").agg(
        [
            pl.col("exprimes").first().alias("exprimes"),
            pl.col("inscrits").first().alias("inscrits"),
        ]
    )
    return voix.join(meta, on="code_insee", how="left").select(
        "code_insee", "nuance", "voix", "exprimes", "inscrits"
    )


def telecharger(path: str) -> None:
    import urllib.request

    if Path(path).exists():
        return
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    print(f"Téléchargement {URL_SOURCE} -> {path} …")
    urllib.request.urlretrieve(URL_SOURCE, path)


def main() -> None:
    path = os.environ.get("LEGISLATIVES_CSV", DEFAUT_CSV)
    url = os.environ.get("DATABASE_URL", DEFAUT_DB_URL)
    telecharger(path)
    print(f"Lecture {path} …")
    df = pl.read_csv(path, separator=";", infer_schema=False)
    out = agreger_resultats(df)

    # Garde-fou : toute nuance présente dans les données doit avoir un mapping famille.
    mapping = charger_nuances(SCRUTIN_ID)
    nuances_data = set(out["nuance"].unique().to_list())
    manquantes = nuances_data - set(mapping)
    if manquantes:
        raise SystemExit(
            f"⛔ nuances sans famille dans {SCRUTIN_ID}.csv : {sorted(manquantes)}"
        )

    lignes = out.to_dicts()
    engine = create_engine(url)
    connus = codes_communes(engine)
    gardees, orphelins = filtrer_communes_connues(lignes, connus)
    if orphelins:
        ex = ", ".join(sorted(orphelins)[:10])
        print(
            f"⚠️ {len(orphelins)} communes ignorées (hors contours : étranger ZZ, "
            f"fusions…) : {ex}…"
        )

    upsert_scrutin(SCRUTIN_ID, TYPE_SCRUTIN, TOUR, DATE, POIDS_BRUT, engine)
    n = inserer_resultats(gardees, SCRUTIN_ID, engine)
    restant = compter_orphelins(SCRUTIN_ID, engine)
    print(f"{n} lignes (commune × nuance) insérées pour {SCRUTIN_ID}.")
    print(f"Codes INSEE orphelins après filtrage : {restant}")
    if restant:
        raise SystemExit(f"⛔ {restant} codes INSEE orphelins (attendu 0)")


if __name__ == "__main__":
    main()
