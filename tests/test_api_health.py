"""Test de la fondation API (sans BDD)."""


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_openapi_expose(client):
    # L'application démarre et les deux routeurs sont enregistrés.
    r = client.get("/openapi.json")
    assert r.status_code == 200
    assert r.json()["info"]["title"] == "CaVoteQuoiIci API"
