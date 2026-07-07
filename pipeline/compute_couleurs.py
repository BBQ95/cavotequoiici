"""Calcul des couleurs précalculées (Étape 3).

Lit `resultats_scrutin` + `scrutins`, agrège les voix par famille politique (via
les mappings datés `config/nuances/<scrutin_id>.csv`), puis :
  - couleurs_scrutin : couleur OKLCH d'une commune pour chaque scrutin ;
  - couleurs_ville   : couleur SYNTHÉTIQUE (pondérée récence + désaturée par
                       l'abstention), servie directement à l'app.

Réutilise le modèle `pipeline.couleur` (spec Concept §5).

Usage :
    DATABASE_URL=postgresql+psycopg2://postgres:cavote@localhost:5432/postgres \\
    python -m pipeline.compute_couleurs
"""

from __future__ import annotations

import json
import os
import statistics
from collections import defaultdict
from datetime import date

import polars as pl
from sqlalchemy import create_engine, text

from pipeline.couleur import ALGOS, ResultatScrutin, couleur_ville, hex_to_oklch
from pipeline.ingest.common import charger_nuances
from pipeline.synthese import TYPE_VERS_POIDS, age_annees, participation, parts_familles

DEFAUT_DB_URL = "postgresql+psycopg2://postgres:cavote@localhost:5432/postgres"


def _charger_voix_par_famille(engine, scrutin_id: str, mapping: dict[str, str]):
    """Retourne (familles, meta) pour un scrutin.

    familles : DataFrame (code_insee, famille, voix) agrégé.
    meta     : DataFrame (code_insee, exprimes, inscrits).
    """
    with engine.connect() as conn:
        df = pl.read_database(
            "SELECT code_insee, nuance, voix, exprimes, inscrits "
            "FROM resultats_scrutin WHERE scrutin_id = :s",
            conn,
            execute_options={"parameters": {"s": scrutin_id}},
        )
    map_df = pl.DataFrame(
        {"nuance": list(mapping), "famille": list(mapping.values())}
    )
    df = df.join(map_df, on="nuance", how="left").drop_nulls("famille")
    familles = df.group_by(["code_insee", "famille"]).agg(
        pl.col("voix").cast(pl.Int64).sum().alias("voix")
    )
    meta = df.group_by("code_insee").agg(
        [
            pl.col("exprimes").cast(pl.Int64).first().alias("exprimes"),
            pl.col("inscrits").cast(pl.Int64).first().alias("inscrits"),
        ]
    )
    return familles, meta


def _construire(engine, reference: date):
    """Construit la structure {code_insee: {scrutin_id: bloc}} depuis la BDD."""
    with engine.connect() as conn:
        scrutins = conn.execute(
            text("SELECT id, type, date FROM scrutins")
        ).fetchall()

    communes: dict[str, dict[str, dict]] = defaultdict(dict)
    ignores: list[tuple[str, str]] = []
    for sid, type_long, d in scrutins:
        if type_long not in TYPE_VERS_POIDS:
            ignores.append((sid, type_long))
            continue  # type non pris en charge (ex. second tour, hors panier)
        mapping = charger_nuances(sid)
        familles, meta = _charger_voix_par_famille(engine, sid, mapping)
        bloc_base = {
            r["code_insee"]: {
                "type": TYPE_VERS_POIDS[type_long],
                "age": age_annees(d, reference),
                "exprimes": r["exprimes"],
                "inscrits": r["inscrits"],
                "voix": {},
            }
            for r in meta.iter_rows(named=True)
        }
        for r in familles.iter_rows(named=True):
            b = bloc_base.get(r["code_insee"])
            if b is not None:
                b["voix"][r["famille"]] = r["voix"]
        for code, bloc in bloc_base.items():
            communes[code][sid] = bloc
    if ignores:
        details = ", ".join(f"{sid} ({t})" for sid, t in ignores)
        print(
            f"  ⚠ {len(ignores)} scrutin(s) ignoré(s) — type absent de "
            f"TYPE_VERS_POIDS/poids.toml : {details}"
        )
    return communes


def _resultats_scrutin(bloc: dict) -> ResultatScrutin:
    return ResultatScrutin(
        type_scrutin=bloc["type"],
        age_annees=bloc["age"],
        parts_familles=parts_familles(bloc["voix"], bloc["exprimes"]),
        participation=participation(bloc["exprimes"], bloc["inscrits"]),
    )


def main() -> None:
    url = os.environ.get("DATABASE_URL", DEFAUT_DB_URL)
    ref_env = os.environ.get("REFERENCE_DATE")
    reference = date.fromisoformat(ref_env) if ref_env else date.today()
    engine = create_engine(url)

    print("Lecture des résultats et agrégation par famille…")
    communes = _construire(engine, reference)
    print(f"  → {len(communes)} communes")

    # --- couleurs_scrutin : médianes de participation par scrutin ---
    part_par_scrutin: dict[str, list[float]] = defaultdict(list)
    for blocs in communes.values():
        for sid, bloc in blocs.items():
            if bloc["exprimes"] > 0:
                part_par_scrutin[sid].append(
                    participation(bloc["exprimes"], bloc["inscrits"])
                )
    med_scrutin = {
        sid: statistics.median(ps) for sid, ps in part_par_scrutin.items() if ps
    }

    # --- synthèse : médiane nationale de la participation synthétique ---
    parts_synth = []
    rs_cache: dict[str, list] = {}
    for code, blocs in communes.items():
        rs = [
            _resultats_scrutin(b)
            for b in blocs.values()
            if b["exprimes"] > 0
        ]
        if not rs:
            continue
        rs_cache[code] = rs
        parts_synth.append(couleur_ville(rs, 1.0)["participation"])
    med_nationale = statistics.median(parts_synth) if parts_synth else 0.0
    print(f"  participation médiane nationale = {med_nationale:.3f}")

    lignes_scrutin = []
    for code, blocs in communes.items():
        for sid, bloc in blocs.items():
            if bloc["exprimes"] <= 0:
                continue
            res = couleur_ville([_resultats_scrutin(bloc)], med_scrutin.get(sid, 1.0))
            ok = hex_to_oklch(res["hex"])
            lignes_scrutin.append(
                {
                    "code_insee": code,
                    "scrutin_id": sid,
                    "l": ok.L,
                    "c": ok.C,
                    "h": ok.H,
                    "participation": res["participation"],
                }
            )

    lignes_ville = []
    lignes_algo = []
    for code, rs in rs_cache.items():
        # Une couleur par algo de dominance ; « complet » alimente aussi
        # couleurs_ville (synthèse historique servie par défaut à l'app).
        for algo in ALGOS:
            res = couleur_ville(rs, med_nationale, algo=algo)
            ok = hex_to_oklch(res["hex"])
            lignes_algo.append(
                {
                    "code_insee": code,
                    "algo": algo,
                    "l": ok.L,
                    "c": ok.C,
                    "h": ok.H,
                    "famille_dominante": res["famille_dominante"],
                    "part_synthetique": res["part_synthetique"],
                    "marge": res["marge"],
                }
            )
            if algo == "complet":
                lignes_ville.append(
                    {
                        "code_insee": code,
                        "l": ok.L,
                        "c": ok.C,
                        "h": ok.H,
                        "participation_mediane": res["participation"],
                        "scrutins_inclus": json.dumps(res["scrutins_inclus"]),
                        "repartition": json.dumps(
                            [{"famille": f, "part": p} for f, p in res["repartition"]]
                        ),
                    }
                )

    # Impact de la pondération : communes « grises » (dominante divers) en
    # algo complet — attendu en forte baisse avec la couverture S4.
    grises_complet = sum(
        1
        for ligne in lignes_algo
        if ligne["algo"] == "complet" and ligne["famille_dominante"] == "divers"
    )
    total_communes = len(rs_cache)
    pct = 100 * grises_complet / total_communes if total_communes else 0.0
    print(
        f"  communes grises (dominante divers, algo complet) = "
        f"{grises_complet}/{total_communes} ({pct:.1f} %)"
    )

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM couleurs_scrutin"))
        if lignes_scrutin:
            conn.execute(
                text(
                    "INSERT INTO couleurs_scrutin "
                    "(code_insee, scrutin_id, l, c, h, participation) "
                    "VALUES (:code_insee, :scrutin_id, :l, :c, :h, :participation)"
                ),
                lignes_scrutin,
            )
        conn.execute(text("DELETE FROM couleurs_ville"))
        if lignes_ville:
            conn.execute(
                text(
                    "INSERT INTO couleurs_ville "
                    "(code_insee, l, c, h, participation_mediane, scrutins_inclus, "
                    "repartition) "
                    "VALUES (:code_insee, :l, :c, :h, :participation_mediane, "
                    ":scrutins_inclus, :repartition)"
                ),
                lignes_ville,
            )
        conn.execute(text("DELETE FROM couleurs_ville_algo"))
        if lignes_algo:
            conn.execute(
                text(
                    "INSERT INTO couleurs_ville_algo "
                    "(code_insee, algo, l, c, h, famille_dominante, "
                    "part_synthetique, marge) "
                    "VALUES (:code_insee, :algo, :l, :c, :h, :famille_dominante, "
                    ":part_synthetique, :marge)"
                ),
                lignes_algo,
            )
    print(
        f"{len(lignes_scrutin)} couleurs_scrutin, {len(lignes_ville)} couleurs_ville, "
        f"{len(lignes_algo)} couleurs_ville_algo écrites."
    )


if __name__ == "__main__":
    main()
