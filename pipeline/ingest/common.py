"""Briques partagées d'ingestion des scrutins (Étape 2).

Contrat commun à tous les parseurs de scrutin (un module par scrutin importe ces
helpers). Garde les fichiers de parseur **disjoints** pour permettre le travail
parallèle ; seul ce module et la convention `config/nuances/<scrutin_id>.csv` sont
partagés.

Table cible `resultats_scrutin` : (code_insee, scrutin_id, nuance, voix, exprimes, inscrits).
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, Mapping

from sqlalchemy import text

CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"
NUANCES_DIR = CONFIG_DIR / "nuances"

# Colonnes attendues d'une ligne de résultat prête à insérer.
COLONNES_RESULTAT = ("code_insee", "nuance", "voix", "exprimes", "inscrits")


def familles_valides(config_dir: Path | str = CONFIG_DIR) -> set[str]:
    """Ensemble des familles canoniques (lues dans familles.csv)."""
    path = Path(config_dir) / "familles.csv"
    with open(path, newline="", encoding="utf-8") as f:
        return {row["famille"].strip() for row in csv.DictReader(f)}


def charger_nuances(
    scrutin_id: str, nuances_dir: Path | str = NUANCES_DIR
) -> dict[str, str]:
    """Charge le mapping nuance -> famille d'un scrutin depuis son CSV daté.

    Valide que chaque famille existe dans familles.csv et qu'aucune nuance n'est
    dupliquée. Lève FileNotFoundError si le fichier du scrutin n'existe pas.
    """
    path = Path(nuances_dir) / f"{scrutin_id}.csv"
    if not path.exists():
        raise FileNotFoundError(f"mapping de nuances absent: {path}")
    valides = familles_valides(Path(nuances_dir).parent)
    mapping: dict[str, str] = {}
    with open(path, newline="", encoding="utf-8") as f:
        for i, row in enumerate(csv.DictReader(f), start=2):  # ligne 1 = en-tête
            nuance = (row.get("nuance") or "").strip()
            famille = (row.get("famille") or "").strip()
            if not nuance:
                raise ValueError(f"{path}:{i} nuance vide")
            if famille not in valides:
                raise ValueError(f"{path}:{i} famille inconnue: {famille!r}")
            if nuance in mapping:
                raise ValueError(f"{path}:{i} nuance dupliquée: {nuance!r}")
            mapping[nuance] = famille
    if not mapping:
        raise ValueError(f"{path}: aucune nuance")
    return mapping


def upsert_scrutin(
    scrutin_id: str,
    type_scrutin: str,
    tour: int,
    date: str,
    poids_brut: float,
    engine,
) -> None:
    """Insère ou met à jour la ligne du scrutin dans `scrutins`."""
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO scrutins (id, type, tour, date, poids_brut) "
                "VALUES (:id, :type, :tour, :date, :poids) "
                "ON CONFLICT (id) DO UPDATE SET "
                "type = EXCLUDED.type, tour = EXCLUDED.tour, "
                "date = EXCLUDED.date, poids_brut = EXCLUDED.poids_brut"
            ),
            {
                "id": scrutin_id,
                "type": type_scrutin,
                "tour": tour,
                "date": date,
                "poids": poids_brut,
            },
        )


def inserer_resultats(
    lignes: Iterable[Mapping], scrutin_id: str, engine
) -> int:
    """Remplace les résultats du scrutin par `lignes` (dicts COLONNES_RESULTAT).

    Vide d'abord les lignes existantes du scrutin (idempotent), puis insère.
    Retourne le nombre de lignes insérées.
    """
    rows = [
        {c: l[c] for c in COLONNES_RESULTAT} | {"scrutin_id": scrutin_id}
        for l in lignes
    ]
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM resultats_scrutin WHERE scrutin_id = :s"),
            {"s": scrutin_id},
        )
        if rows:
            conn.execute(
                text(
                    "INSERT INTO resultats_scrutin "
                    "(code_insee, scrutin_id, nuance, voix, exprimes, inscrits) "
                    "VALUES (:code_insee, :scrutin_id, :nuance, :voix, "
                    ":exprimes, :inscrits)"
                ),
                rows,
            )
    return len(rows)


def compter_orphelins(scrutin_id: str, engine) -> int:
    """Nombre de codes INSEE de `resultats_scrutin` absents de `communes`.

    Critère de sortie de l'Étape 2 : doit valoir 0 pour chaque scrutin.
    """
    with engine.connect() as conn:
        return conn.execute(
            text(
                "SELECT count(*) FROM resultats_scrutin r "
                "LEFT JOIN communes c ON c.code_insee = r.code_insee "
                "WHERE r.scrutin_id = :s AND c.code_insee IS NULL"
            ),
            {"s": scrutin_id},
        ).scalar_one()
