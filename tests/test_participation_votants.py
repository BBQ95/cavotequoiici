"""Régression : les blancs/nuls participent, sans entrer dans les parts politiques."""

import importlib.util
from pathlib import Path

import polars as pl
import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, text

from pipeline.compute_couleurs import _charger_voix_par_famille, _resultats_scrutin
from pipeline.couleur import couleur_ville
from pipeline.ingest.common import inserer_resultats
from pipeline.ingest import (
    europeennes_2024,
    legislatives_2024,
    municipales_2026,
    presidentielle_2022,
)


def source_large(prefixe):
    return pl.DataFrame({
        "Code commune": ["01001"], "Inscrits": ["100"],
        "Votants": ["80"], "Exprimés": ["70"],
        f"Nuance {prefixe} 1": ["RN"], "Voix 1": ["40"],
        f"Nuance {prefixe} 2": ["UG"], "Voix 2": ["30"],
    })


def source_presidentielle():
    return pl.DataFrame({
        "dep_code": ["01", "01"], "commune_code": ["001", "001"],
        "cand_num_panneau": [5, 7], "cand_nb_voix": [40, 30],
        "inscrits_nb": [100, 100], "votants_nb": [80, 80],
        "exprimes_nb": [70, 70],
    })


@pytest.mark.parametrize(
    "scrutin", ["presidentielle", "legislatives", "europeennes", "municipales"]
)
def test_votants_de_la_source_a_la_couleur(scrutin):
    if scrutin == "presidentielle":
        resultat = presidentielle_2022.agreger_resultats(source_presidentielle())
    elif scrutin == "legislatives":
        resultat = legislatives_2024.agreger_resultats(source_large("candidat"))
    else:
        module = europeennes_2024 if scrutin == "europeennes" else municipales_2026
        resultat = module.aggregate_voix(module.parse_resultats_commune(source_large("liste")))
    assert resultat["votants"].to_list() == [80, 80]

    # Aller-retour SQL réel : vérifie aussi le contrat partagé d'insertion et
    # la lecture de compute_couleurs, sans nécessiter de serveur PostGIS.
    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE resultats_scrutin (code_insee TEXT, scrutin_id TEXT, "
            "nuance TEXT, voix INTEGER, exprimes INTEGER, votants INTEGER, inscrits INTEGER)"
        ))
    inserer_resultats(resultat.to_dicts(), "test", engine)
    familles, meta = _charger_voix_par_famille(
        engine, "test", {"RN": "droite", "UG": "gauche", "FI": "gauche"}
    )
    bloc = meta.to_dicts()[0] | {
        "type": "pres_t1", "age": 0,
        "voix": {r["famille"]: r["voix"] for r in familles.to_dicts()},
    }
    rs = _resultats_scrutin(bloc)
    assert rs.participation == 0.8
    assert rs.parts_familles == {"droite": 40 / 70, "gauche": 30 / 70}
    synthese = couleur_ville([rs], 0.8)
    assert synthese["participation"] == 0.8
    assert sum(p for _, p in synthese["repartition"]) == pytest.approx(1)


def test_votants_presidentielle_sommes_une_fois_par_arrondissement():
    premier = source_presidentielle().with_columns(
        pl.lit("75").alias("dep_code"), pl.lit("056AR01").alias("commune_code")
    )
    second = premier.with_columns(
        pl.lit("056AR02").alias("commune_code"),
        pl.lit(40).alias("votants_nb"), pl.lit(35).alias("exprimes_nb"),
        pl.lit(50).alias("inscrits_nb"),
        (pl.col("cand_nb_voix") / 2).alias("cand_nb_voix"),
    )
    resultat = presidentielle_2022.agreger_resultats(
        pl.concat([premier, second], how="vertical_relaxed")
    )
    assert set(resultat["code_insee"]) == {"75056"}
    assert set(resultat["votants"]) == {120}
    assert set(resultat["exprimes"]) == {105}
    assert set(resultat["inscrits"]) == {150}


def test_migration_preserve_les_resultats_et_exige_une_reingestion(monkeypatch):
    path = (
        Path(__file__).resolve().parents[1]
        / "alembic/versions/0005_resultats_votants.py"
    )
    spec = importlib.util.spec_from_file_location("migration_votants", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE resultats_scrutin (code_insee TEXT, scrutin_id TEXT, "
            "nuance TEXT, voix INTEGER, exprimes INTEGER, inscrits INTEGER)"
        ))
        conn.execute(text(
            "INSERT INTO resultats_scrutin VALUES ('01001', 'test', 'RN', 70, 70, 100)"
        ))
        monkeypatch.setattr(migration, "op", Operations(MigrationContext.configure(conn)))
        migration.upgrade()
        assert conn.execute(text("SELECT votants FROM resultats_scrutin")).scalar_one() is None
    with pytest.raises(ValueError, match="réingérer"):
        _charger_voix_par_famille(engine, "test", {"RN": "droite"})
    # Une source incomplète ne doit pas effacer les anciens résultats.
    with pytest.raises(ValueError, match="votants manquants"):
        inserer_resultats([{
            "code_insee": "01001", "nuance": "RN", "voix": 60,
            "exprimes": 60, "votants": None, "inscrits": 100,
        }], "test", engine)
    with engine.begin() as conn:
        monkeypatch.setattr(migration, "op", Operations(MigrationContext.configure(conn)))
        migration.downgrade()
        assert conn.execute(text("SELECT voix FROM resultats_scrutin")).scalar_one() == 70
