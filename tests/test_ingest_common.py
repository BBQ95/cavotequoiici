"""Tests des fonctions pures de pipeline.ingest.common (sans BDD).

Les helpers BDD (upsert_scrutin, inserer_resultats, compter_orphelins) sont
couverts en intégration par les parseurs de chaque scrutin (Étape 2).
"""

import pytest

from pipeline.ingest.common import (
    charger_nuances,
    charger_nuances_completes,
    familles_valides,
    filtrer_communes_connues,
)


@pytest.fixture
def config(tmp_path):
    """Reconstruit une arborescence config/ + config/nuances/ minimale."""
    (tmp_path / "familles.csv").write_text(
        "famille,libelle,position,hex\n"
        "gauche,Gauche,Gauche,#E84E6B\n"
        "droite,Droite,Droite,#2D6FCB\n"
        "extreme_droite,Extrême droite,Droite radicale,#16243F\n",
        encoding="utf-8",
    )
    nuances = tmp_path / "nuances"
    nuances.mkdir()
    return tmp_path, nuances


def _ecrire(nuances_dir, scrutin_id, corps):
    entete = "nuance,famille,scrutin_type,annee,date_classification,date_debut,date_fin,source\n"
    (nuances_dir / f"{scrutin_id}.csv").write_text(entete + corps, encoding="utf-8")


def test_familles_valides(config):
    base, _ = config
    assert familles_valides(base) == {"gauche", "droite", "extreme_droite"}


def test_charger_nuances_ok(config):
    _, nuances = config
    _ecrire(
        nuances,
        "x_2024",
        "PS,gauche,europeennes,2024,2024-06-09,,,data.gouv.fr\n"
        "RN,extreme_droite,europeennes,2024,2024-06-09,,,data.gouv.fr\n",
    )
    mapping = charger_nuances("x_2024", nuances_dir=nuances)
    assert mapping == {"PS": "gauche", "RN": "extreme_droite"}


def test_charger_nuances_fichier_absent(config):
    _, nuances = config
    with pytest.raises(FileNotFoundError):
        charger_nuances("inexistant", nuances_dir=nuances)


def test_charger_nuances_famille_inconnue(config):
    _, nuances = config
    _ecrire(nuances, "x", "PS,centre,europeennes,2024,2024-06-09,,,src\n")  # centre absent
    with pytest.raises(ValueError, match="famille inconnue"):
        charger_nuances("x", nuances_dir=nuances)


def test_charger_nuances_doublon(config):
    _, nuances = config
    _ecrire(
        nuances,
        "x",
        "PS,gauche,europeennes,2024,2024-06-09,,,src\n"
        "PS,droite,europeennes,2024,2024-06-09,,,src\n",
    )
    with pytest.raises(ValueError, match="dupliquée"):
        charger_nuances("x", nuances_dir=nuances)


def test_charger_nuances_vide(config):
    _, nuances = config
    _ecrire(nuances, "x", "")
    with pytest.raises(ValueError, match="aucune nuance"):
        charger_nuances("x", nuances_dir=nuances)


def test_charger_nuances_completes_ok(config):
    _, nuances = config
    _ecrire(
        nuances,
        "x_2024",
        "PS,gauche,europeennes,2024,2024-06-09,,,data.gouv.fr\n"
        "RN,extreme_droite,europeennes,2024,2024-06-09,,,Légifrance id/1\n",
    )
    lignes = charger_nuances_completes("x_2024", nuances_dir=nuances)
    assert lignes == [
        {
            "nuance": "PS",
            "famille": "gauche",
            "scrutin_type": "europeennes",
            "annee": 2024,
            "date_classification": "2024-06-09",
            "source": "data.gouv.fr",
            "statut": None,
        },
        {
            "nuance": "RN",
            "famille": "extreme_droite",
            "scrutin_type": "europeennes",
            "annee": 2024,
            "date_classification": "2024-06-09",
            "source": "Légifrance id/1",
            "statut": None,
        },
    ]


def test_charger_nuances_completes_statut(config):
    # Colonne `statut` optionnelle (municipales 2026 : grille provisoire).
    _, nuances = config
    entete = (
        "nuance,famille,scrutin_type,annee,date_classification,"
        "date_debut,date_fin,source,statut\n"
    )
    (nuances / "mun.csv").write_text(
        entete + "LUD,droite,municipales_t1,2026,2026-03-15,,,data.gouv.fr,provisoire\n",
        encoding="utf-8",
    )
    lignes = charger_nuances_completes("mun", nuances_dir=nuances)
    assert lignes[0]["statut"] == "provisoire"


def test_charger_nuances_completes_memes_validations(config):
    # Même chemin de validation que charger_nuances.
    _, nuances = config
    with pytest.raises(FileNotFoundError):
        charger_nuances_completes("inexistant", nuances_dir=nuances)
    _ecrire(nuances, "fam", "PS,centre,europeennes,2024,2024-06-09,,,src\n")
    with pytest.raises(ValueError, match="famille inconnue"):
        charger_nuances_completes("fam", nuances_dir=nuances)
    _ecrire(
        nuances,
        "dup",
        "PS,gauche,europeennes,2024,2024-06-09,,,src\n"
        "PS,droite,europeennes,2024,2024-06-09,,,src\n",
    )
    with pytest.raises(ValueError, match="dupliquée"):
        charger_nuances_completes("dup", nuances_dir=nuances)
    _ecrire(nuances, "vide", "")
    with pytest.raises(ValueError, match="aucune nuance"):
        charger_nuances_completes("vide", nuances_dir=nuances)


def test_filtrer_communes_connues():
    lignes = [
        {"code_insee": "01001", "voix": 5},
        {"code_insee": "99999", "voix": 3},  # inconnue
        {"code_insee": "06088", "voix": 7},
        {"code_insee": "99999", "voix": 1},  # même inconnue, dédupliquée
    ]
    gardees, orphelins = filtrer_communes_connues(lignes, {"01001", "06088"})
    assert [g["code_insee"] for g in gardees] == ["01001", "06088"]
    assert orphelins == {"99999"}
