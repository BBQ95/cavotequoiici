"""Ingestion de l'élection présidentielle 2022, 1er tour (Étape 2).

Source : data.gouv.fr, résultats par commune (format long : une ligne par commune
× candidat, UTF-8, séparateur virgule). Couvre métropole + Corse (les DOM, absents
de ce fichier, restent à compléter ultérieurement).

Construction du code INSEE : `dep_code` + 3 premiers caractères de `commune_code`,
ce qui agrège automatiquement les arrondissements PLM (Paris/Lyon/Marseille) vers
leur commune parente (75056 / 69123 / 13055), cohérent avec la table `communes`.

Usage :
    DATABASE_URL=postgresql+psycopg2://postgres:cavote@localhost:5432/postgres \\
    python -m pipeline.ingest.presidentielle_2022
"""

from __future__ import annotations

import os
from pathlib import Path

import polars as pl
from sqlalchemy import create_engine

from pipeline.ingest.common import (
    codes_communes,
    compter_orphelins,
    filtrer_communes_connues,
    inserer_resultats,
    upsert_scrutin,
)

SCRUTIN_ID = "presidentielle_2022_t1"
TYPE_SCRUTIN = "presidentielle_t1"
TOUR = 1
DATE = "2022-04-10"
POIDS_BRUT = 1.0

URL_SOURCE = "https://www.data.gouv.fr/api/1/datasets/r/54782507-e795-4f9d-aa70-ed06feba22e3"
DEFAUT_CSV = "data/presidentielle_2022_t1_communes.csv"
DEFAUT_DB_URL = "postgresql+psycopg2://postgres:cavote@localhost:5432/postgres"

# Numéro de panneau officiel -> code nuance (cf. config/nuances/presidentielle_2022_t1.csv).
# Clé stable, insensible aux accents/casse du nom de candidat.
PANNEAU_NUANCE = {
    1: "LO",    # Arthaud
    2: "PCF",   # Roussel
    3: "ENS",   # Macron
    4: "RES",   # Lassalle (Résistons)
    5: "RN",    # Le Pen
    6: "REC",   # Zemmour (Reconquête)
    7: "FI",    # Mélenchon
    8: "PS",    # Hidalgo
    9: "EELV",  # Jadot
    10: "LR",   # Pécresse
    11: "NPA",  # Poutou
    12: "DLF",  # Dupont-Aignan
}


def construire_insee(dep_code: str, commune_code: str) -> str:
    """Code INSEE 5 caractères = département + base communale (3 premiers car.).

    Les arrondissements PLM (`056AR18`) sont ramenés à leur commune parente (`056`).
    """
    return f"{str(dep_code).strip().upper()}{str(commune_code).strip()[:3]}"


def agreger_resultats(df: pl.DataFrame) -> pl.DataFrame:
    """Agrège le fichier long en lignes (code_insee, nuance, voix, exprimes, inscrits).

    - voix : somme par (commune, nuance) — fusionne les arrondissements PLM ;
    - exprimes/inscrits : somme des sous-communes (comptées une seule fois).
    """
    df = df.with_columns(
        [
            pl.col("cand_num_panneau").cast(pl.Int64),
            pl.col("cand_nb_voix").cast(pl.Int64),
            pl.col("exprimes_nb").cast(pl.Int64),
            pl.col("inscrits_nb").cast(pl.Int64),
        ]
    ).with_columns(
        [
            (
                pl.col("dep_code").str.strip_chars().str.to_uppercase()
                + pl.col("commune_code").str.strip_chars().str.slice(0, 3)
            ).alias("code_insee"),
            pl.col("cand_num_panneau")
            .replace_strict(PANNEAU_NUANCE)
            .alias("nuance"),
        ]
    )

    voix = df.group_by(["code_insee", "nuance"]).agg(
        pl.col("cand_nb_voix").sum().alias("voix")
    )
    meta = (
        df.unique(subset=["dep_code", "commune_code"])
        .group_by("code_insee")
        .agg(
            [
                pl.col("exprimes_nb").sum().alias("exprimes"),
                pl.col("inscrits_nb").sum().alias("inscrits"),
            ]
        )
    )
    return voix.join(meta, on="code_insee", how="left").select(
        "code_insee", "nuance", "voix", "exprimes", "inscrits"
    )


def telecharger(path: str) -> None:
    """Télécharge le CSV source s'il est absent (réseau requis)."""
    import urllib.request

    if Path(path).exists():
        return
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    print(f"Téléchargement {URL_SOURCE} -> {path} …")
    urllib.request.urlretrieve(URL_SOURCE, path)


def main() -> None:
    path = os.environ.get("PRESIDENTIELLE_CSV", DEFAUT_CSV)
    url = os.environ.get("DATABASE_URL", DEFAUT_DB_URL)
    telecharger(path)
    print(f"Lecture {path} …")
    df = pl.read_csv(path, infer_schema=False)  # tout en str : codes communes alphanum.
    out = agreger_resultats(df)
    lignes = out.to_dicts()

    engine = create_engine(url)
    # Écarte les communes 2022 disparues des contours 2024 (fusions / communes nouvelles).
    connus = codes_communes(engine)
    gardees, orphelins = filtrer_communes_connues(lignes, connus)
    if orphelins:
        ex = ", ".join(sorted(orphelins)[:10])
        print(
            f"⚠️ {len(orphelins)} communes ignorées (absentes des contours 2024, "
            f"fusionnées/disparues depuis 2022) : {ex}…"
        )
        print("   → à réintégrer via une table historique des codes INSEE (suivi Étape 2).")

    upsert_scrutin(SCRUTIN_ID, TYPE_SCRUTIN, TOUR, DATE, POIDS_BRUT, engine)
    n = inserer_resultats(gardees, SCRUTIN_ID, engine)
    restant = compter_orphelins(SCRUTIN_ID, engine)
    print(f"{n} lignes (commune × nuance) insérées pour {SCRUTIN_ID}.")
    print(f"Codes INSEE orphelins après filtrage : {restant}")
    if restant:
        raise SystemExit(f"⛔ {restant} codes INSEE orphelins (attendu 0)")


if __name__ == "__main__":
    main()
