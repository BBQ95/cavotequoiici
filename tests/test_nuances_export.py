"""Tests de exporter_nuances() — le nuances.json des artefacts statiques.

Portage de l'ancien test de GET /nuances (retiré avec l'API) : la sortie
sérialise les CSV versionnés de pipeline/config/nuances/, sans BDD. C'est
elle que lit l'écran mobile « D'où viennent les familles ? ».
"""

import json

import pytest

from pipeline.export_communes import exporter_nuances

TYPES_COURTS = {"pres_t1", "leg_t1", "euro", "mun_t1"}


@pytest.fixture(scope="module")
def scrutins() -> list[dict]:
    nuances = exporter_nuances()
    # Sérialisable tel quel : c'est ce que l'export écrit dans nuances.json.
    json.dumps(nuances, ensure_ascii=False)
    return nuances["scrutins"]


def test_structure_et_ordre(scrutins):
    # Les 4 grilles versionnées, triées par année décroissante.
    assert [s["scrutin_id"] for s in scrutins] == [
        "municipales_2026_t1",
        "europeennes_2024",
        "legislatives_2024_t1",
        "presidentielle_2022_t1",
    ]
    annees = [s["annee"] for s in scrutins]
    assert annees == sorted(annees, reverse=True)
    for s in scrutins:
        # Type court (celui que le mobile sait libeller), jamais le type long.
        assert s["type"] in TYPES_COURTS
        assert s["date_classification"]
        assert s["nuances"], f"{s['scrutin_id']}: grille vide"


def test_source_et_statut(scrutins):
    par_id = {s["scrutin_id"]: s for s in scrutins}
    # Chaque ligne porte sa référence officielle (audit public).
    for s in scrutins:
        for n in s["nuances"]:
            assert n["source"].strip(), f"{s['scrutin_id']}/{n['nuance']}: source vide"
    # Municipales 2026 : grille provisoire (circulaire non publiée) ; les autres non.
    for n in par_id["municipales_2026_t1"]["nuances"]:
        assert n["statut"] == "provisoire"
    for sid in ("presidentielle_2022_t1", "legislatives_2024_t1", "europeennes_2024"):
        assert all(n["statut"] is None for n in par_id[sid]["nuances"])


def test_cas_conseil_detat(scrutins):
    # La classification de LFI (extrême gauche) est débattue : la mention du
    # contrôle CE doit rester visible dans la source, par grille concernée.
    par_id = {s["scrutin_id"]: s for s in scrutins}
    fi = next(
        n for n in par_id["legislatives_2024_t1"]["nuances"] if n["nuance"] == "FI"
    )
    assert fi["famille"] == "extreme_gauche"
    assert "CE" in fi["source"]
