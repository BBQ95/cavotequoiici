"""Tests du routeur communes (intégration BDD ; ignoré sans DATABASE_URL)."""

import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL non définie (test d'intégration BDD)",
)

# Familles valides (cf. pipeline/config/familles.csv). Ces tests d'intégration
# vérifient le BRANCHEMENT de ?algo= sans épingler la famille d'une commune
# réelle : les couleurs réelles dérivent à chaque scrutin. La LOGIQUE des algos
# (complet vs tendance vs blocs) est testée sur données fictives dans
# tests/test_couleur.py::TestCouleurVilleAlgos.
FAMILLES_VALIDES = {
    "extreme_gauche",
    "gauche",
    "ecologistes",
    "centre",
    "droite",
    "extreme_droite",
    "divers",
}


def test_search(client):
    r = client.get("/communes/search", params={"q": "Saint-Den"})
    assert r.status_code == 200
    codes = {c["code_insee"] for c in r.json()}
    assert "93066" in codes


def test_search_insensible_aux_accents(client):
    """Cas rapporté : « nim » doit proposer Nîmes (30189)."""
    r = client.get("/communes/search", params={"q": "nim"})
    assert r.status_code == 200
    body = r.json()
    assert "30189" in {c["code_insee"] for c in body}
    # Les préfixes sortent en premier : le 1er résultat commence par « nim ».
    assert body[0]["nom"].lower().replace("î", "i").startswith("nim")


def test_search_milieu_de_nom(client):
    """« denis » (sans « saint- ») trouve Saint-Denis."""
    r = client.get("/communes/search", params={"q": "denis", "limite": 50})
    assert r.status_code == 200
    assert "93066" in {c["code_insee"] for c in r.json()}


def test_search_espace_pour_tiret(client):
    """« saint denis » (espace) matche « Saint-Denis » (tiret)."""
    r = client.get("/communes/search", params={"q": "saint denis"})
    assert r.status_code == 200
    assert "93066" in {c["code_insee"] for c in r.json()}


def test_search_renvoie_couleur_et_famille(client):
    """Chaque résultat porte hex + famille dominante (pastille de la liste)."""
    r = client.get("/communes/search", params={"q": "saint denis"})
    assert r.status_code == 200
    saint_denis = next(c for c in r.json() if c["code_insee"] == "93066")
    assert saint_denis["hex"].startswith("#")
    assert saint_denis["famille"] == "extreme_gauche"


def test_search_metacaracteres_like_neutralises(client):
    """Un « % » saisi ne doit pas matcher toutes les communes."""
    r = client.get("/communes/search", params={"q": "%"})
    assert r.status_code == 200
    assert r.json() == []


def test_couleur(client):
    r = client.get("/communes/93066/couleur")
    assert r.status_code == 200
    body = r.json()
    assert 5 <= body["h"] <= 45          # Saint-Denis → rouge
    assert body["hex"].startswith("#")
    assert body["scrutins_inclus"]


def test_couleur_404(client):
    assert client.get("/communes/00000/couleur").status_code == 404


def test_couleur_repartition(client):
    """La synthèse expose la répartition par famille (barre des familles de la fiche)."""
    r = client.get("/communes/93066/couleur")
    assert r.status_code == 200
    rep = r.json()["repartition"]
    assert isinstance(rep, list) and rep, "répartition non vide attendue"
    # Chaque entrée = {famille, part}
    for entree in rep:
        assert set(entree) == {"famille", "part"}
        assert 0.0 <= entree["part"] <= 1.0
    # Triée par part décroissante ; somme des parts ≈ 1
    parts = [e["part"] for e in rep]
    assert parts == sorted(parts, reverse=True)
    assert abs(sum(parts) - 1.0) < 0.01
    # Saint-Denis → famille dominante à gauche (extrême gauche ou gauche)
    assert rep[0]["famille"] in {"extreme_gauche", "gauche"}


def test_fiche_repartition(client):
    """La fiche complète porte aussi la répartition (sous couleur)."""
    body = client.get("/communes/06088").json()
    assert body["couleur"]["repartition"]


def test_fiche(client):
    r = client.get("/communes/06088")
    assert r.status_code == 200
    body = r.json()
    assert body["nom"] == "Nice"
    assert 240 <= body["couleur"]["h"] <= 275   # Nice → marine


def test_proximite(client):
    # autour de Nice
    r = client.get("/communes/proximite", params={"lat": 43.70, "lon": 7.27, "rayon_m": 6000})
    assert r.status_code == 200
    items = r.json()
    assert any(i["code_insee"] == "06088" for i in items)
    # triées par distance croissante
    dists = [i["distance_m"] for i in items]
    assert dists == sorted(dists)


def test_couleur_algo_branchement(client):
    """P1.2 : ?algo= est relayé de bout en bout. Invariants (indépendants des
    données réelles) : les 3 algos répondent 200, renvoient l'algo demandé et une
    famille valide ; seule la dominance/teinte peut changer — la répartition et la
    participation sont identiques d'un algo à l'autre (transparence)."""
    complet = client.get("/communes/93066/couleur").json()
    assert complet["algo"] == "complet"
    for algo in ("complet", "tendance", "blocs"):
        r = client.get("/communes/93066/couleur", params={"algo": algo})
        assert r.status_code == 200
        body = r.json()
        assert body["algo"] == algo
        assert body["famille_dominante"] in FAMILLES_VALIDES
        # Répartition et participation indépendantes de l'algo choisi.
        assert body["repartition"] == complet["repartition"]
        assert body["participation_mediane"] == complet["participation_mediane"]


def test_couleur_algo_defaut_complet(client):
    """Sans paramètre, comportement historique (compat clients existants)."""
    implicite = client.get("/communes/93066/couleur").json()
    explicite = client.get("/communes/93066/couleur", params={"algo": "complet"}).json()
    assert implicite == explicite
    assert implicite["algo"] == "complet"
    assert implicite["famille_dominante"] == implicite["repartition"][0]["famille"]


def test_couleur_algo_inconnu_422(client):
    assert client.get("/communes/93066/couleur", params={"algo": "magique"}).status_code == 422


def test_fiche_algo_branchement(client):
    """La fiche relaie ?algo= (écho + famille valide), sans pin sur une commune réelle."""
    r = client.get("/communes/93066", params={"algo": "tendance"})
    assert r.status_code == 200
    couleur = r.json()["couleur"]
    assert couleur["algo"] == "tendance"
    assert couleur["famille_dominante"] in FAMILLES_VALIDES


def test_fiche_renvoie_coordonnees_lat_lon(client):
    """La fiche d'une commune porte lat/lon (point sur surface, WGS84)."""
    body = client.get("/communes/93066").json()
    assert body["lat"] is not None
    assert body["lon"] is not None
    # Saint-Denis (93) : latitude ~48.9, longitude ~2.36
    assert 41 <= body["lat"] <= 52, "lat hors plage France métropolitaine"
    assert -5 <= body["lon"] <= 10, "lon hors plage France métropolitaine"


def test_fiche_coordonnees_nice(client):
    """Nice (06088) : lat ~43.7, lon ~7.27 — valide le sud-est."""
    body = client.get("/communes/06088").json()
    assert body["lat"] is not None
    assert body["lon"] is not None
    assert 41 <= body["lat"] <= 52
    assert -5 <= body["lon"] <= 10
    # Nice précisément
    assert abs(body["lat"] - 43.7) < 0.2
    assert abs(body["lon"] - 7.27) < 0.2


def test_search_algo_branchement(client):
    """La recherche relaie ?algo= (P1.3 : préférence de l'app) : chaque pastille
    porte une famille et un hex valides pour l'algo demandé. Sans pin sur une
    commune réelle — la logique complet/tendance est couverte sur données fictives
    (tests/test_couleur.py)."""
    for algo in ("complet", "tendance"):
        res = client.get(
            "/communes/search", params={"q": "saint", "algo": algo}
        ).json()
        assert res, f"recherche vide pour algo={algo}"
        for c in res:
            assert c["famille"] in FAMILLES_VALIDES
            assert c["hex"].startswith("#") and len(c["hex"]) == 7
