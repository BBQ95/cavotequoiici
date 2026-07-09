"""Tests de GET /nuances (grilles de classification nuance -> famille, sans BDD).

L'endpoint sérialise les CSV versionnés de pipeline/config/nuances/ : il doit
fonctionner sans DATABASE_URL (job CI python-unit), comme /healthz.
"""

TYPES_COURTS = {"pres_t1", "leg_t1", "euro", "mun_t1"}


def test_nuances_200_et_structure(client):
    r = client.get("/nuances")
    assert r.status_code == 200
    scrutins = r.json()["scrutins"]
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


def test_nuances_source_et_statut(client):
    scrutins = client.get("/nuances").json()["scrutins"]
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


def test_nuances_cas_conseil_detat(client):
    # La classification de LFI (extrême gauche) est débattue : la mention du
    # contrôle CE doit rester visible dans la source, par grille concernée.
    scrutins = client.get("/nuances").json()["scrutins"]
    par_id = {s["scrutin_id"]: s for s in scrutins}
    fi = next(
        n for n in par_id["legislatives_2024_t1"]["nuances"] if n["nuance"] == "FI"
    )
    assert fi["famille"] == "extreme_gauche"
    assert "CE" in fi["source"]


def test_nuances_dans_openapi(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert "/nuances" in paths
