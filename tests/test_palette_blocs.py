"""Palette par bloc : calcul, participation et parité des artefacts publiés."""
import json
from pathlib import Path

import pytest

from pipeline import couleur
from pipeline.couleur import ALGOS, OKLCH, ResultatScrutin, couleur_ville, hex_to_oklch
from pipeline.export_communes import couleur_synthese, entree_index
from pipeline.export_tiles import feature_proprietes


def calcul(parts, participation=0.8, algo="blocs"):
    return couleur_ville([ResultatScrutin("pres_t1", 0, parts, participation)], 0.8, algo)


@pytest.mark.parametrize("bloc,familles,hex_attendu", [
    ("gauche", ["extreme_gauche", "gauche", "ecologistes"], "#E84E6B"),
    ("centre", ["centre"], "#FFB300"),
    ("droite", ["droite", "extreme_droite"], "#2D6FCB"),
])
def test_palette_independante_de_la_sous_famille(bloc, familles, hex_attendu):
    for famille in familles:
        res = calcul({famille: 1.0})
        assert res["famille_dominante"] == bloc
        assert res["hex"].upper() == hex_attendu


@pytest.mark.parametrize("famille", ["extreme_gauche", "ecologistes", "extreme_droite"])
def test_autres_algos_conservent_la_teinte_de_famille(famille):
    for algo in ["complet", "tendance"]:
        res = calcul({famille: 1.0}, algo=algo)
        assert res["famille_dominante"] == famille
        assert res["hex"].upper() == couleur.COULEURS[famille]


@pytest.mark.parametrize("bloc,famille", [("gauche", "ecologistes"), ("centre", "centre"), ("droite", "extreme_droite")])
def test_participation_attenue_la_couleur_du_bloc(bloc, famille):
    forte, faible = [calcul({famille: 0.8, "divers": 0.2}, p) for p in [0.8, 0.3]]
    assert forte["famille_dominante"] == faible["famille_dominante"] == bloc
    a, b = [hex_to_oklch(r["hex"]) for r in [forte, faible]]
    assert b.C < a.C
    assert abs(a.H - b.H) < 2
    assert forte["repartition"] == faible["repartition"]


def test_egalite_de_blocs_marge_nulle_et_teinte_du_bloc_departage():
    res = calcul({"extreme_gauche": 0.5, "extreme_droite": 0.5})
    assert res["famille_dominante"] == "droite"
    assert res["marge"] == 0
    assert res["part_synthetique"] == 0.5
    base = hex_to_oklch("#2D6FCB")
    finale = hex_to_oklch(res["hex"])
    assert abs(base.H - finale.H) < 1
    assert finale.C == pytest.approx(base.C * 0.45, abs=0.002)


@pytest.mark.parametrize("parts", [{"divers": 1.0}, {"inconnue": 1.0}, {"divers": 0.7, "ecologistes": 0.0, "inconnue": 0.3}])
def test_aucun_bloc_classe_donne_un_resultat_neutre(parts):
    res = calcul(parts)
    assert res["famille_dominante"] == "divers"
    assert res["marge"] == 0
    assert hex_to_oklch(res["hex"]).C < 0.02


def test_palette_mobile_verrouillee_par_fixture():
    fixture = json.loads((Path(__file__).parent / "fixtures/blocs_parite.json").read_text())
    assert fixture["couleurs"] == couleur.COULEURS_BLOCS
    assert fixture["version_palette"] == couleur.VERSION_PALETTE_BLOCS


@pytest.mark.parametrize("famille", ["extreme_gauche", "centre", "extreme_droite"])
def test_meme_hex_dans_fiche_index_et_tuile_apres_calcul(famille):
    resultats = {algo: calcul({famille: 0.7, "divers": 0.3}, algo=algo) for algo in ALGOS}
    # Même aller-retour hex→OKLCH que compute_couleurs lors de l'écriture en base.
    lignes = {}
    for algo, res in resultats.items():
        ok = hex_to_oklch(res["hex"])
        lignes[algo] = {"l": ok.L, "c": ok.C, "h": ok.H, "famille_dominante": res["famille_dominante"]}
    row = {"code_insee": "00001", "nom": "Exemple", "departement": "00", "lat": 47.0, "lon": 2.0,
           "participation_mediane": 0.8, "scrutins_inclus": [["pres_t1", 1.0]],
           "repartition": [{"famille": f, "part": p} for f, p in resultats["complet"]["repartition"]],
           **lignes["complet"]}
    fiche = couleur_synthese(row, "blocs", lignes["blocs"])
    index = entree_index(row, lignes, {"gauche": 0, "centre": 1, "droite": 2})
    tuiles = feature_proprietes(row, couleurs_par_algo={algo: OKLCH(v["l"], v["c"], v["h"]) for algo, v in lignes.items()})
    assert fiche.hex == index[5][ALGOS.index("blocs")] == tuiles["hex_algo_blocs"] == resultats["blocs"]["hex"]
    assert fiche.famille_dominante in ["gauche", "centre", "droite"]
    assert index[6][ALGOS.index("blocs")] is not None
