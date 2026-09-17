"""Départage reproductible des égalités, indépendant du hash Python."""

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from pipeline.couleur import ALGOS, ResultatScrutin, couleur_ville


CAS = [
    # Familles à égalité ; droite précède gauche selon les identifiants.
    ({"gauche": 0.5, "droite": 0.5}, "complet", "droite", 0.0),
    # Divers est exclu avant le départage en mode tendance.
    ({"divers": 0.5, "gauche": 0.25, "droite": 0.25}, "tendance", "droite", 0.0),
    # Blocs à égalité, malgré une sous-famille gauche plus forte que chacune
    # des sous-familles du bloc droite : le départage porte sur les BLOCS.
    ({"gauche": 0.5, "droite": 0.25, "extreme_droite": 0.25}, "blocs", "droite", 0.0),
    # Bloc gauche gagnant, quelle que soit l'égalité de ses sous-familles.
    ({"gauche": 0.375, "ecologistes": 0.375, "droite": 0.25}, "blocs", "gauche", 0.5),
]


@pytest.mark.parametrize("parts,algo,gagnante,marge", CAS)
def test_departage_par_identifiant_avant_arrondi(parts, algo, gagnante, marge):
    for entrees in (list(parts.items()), list(reversed(parts.items()))):
        resultat = couleur_ville([ResultatScrutin("pres_t1", 0, dict(entrees), 0.8)], 0.8, algo)
        assert resultat["famille_dominante"] == gagnante
        assert resultat["marge"] == marge
        assert resultat["repartition"] == sorted(parts.items(), key=lambda kv: (-kv[1], kv[0]))


@pytest.mark.parametrize("algo", ALGOS)
def test_arrondi_affichage_ne_cree_pas_une_egalite(algo):
    resultat = couleur_ville([
        ResultatScrutin("pres_t1", 0, {"gauche": 0.5001, "droite": 0.4999}, 0.8)
    ], 0.8, algo)
    assert resultat["famille_dominante"] == "gauche"
    assert resultat["repartition"] == [("gauche", 0.5), ("droite", 0.5)]


def test_resultat_complet_identique_entre_processus():
    # Un test dans un seul processus ne change pas la graine du set : lancer
    # réellement Python avec plusieurs PYTHONHASHSEED reproduit la régression.
    programme = """
import json, sys
from pipeline.couleur import ALGOS, ResultatScrutin, couleur_ville
cas = json.loads(sys.argv[1])
print(json.dumps([
    couleur_ville([ResultatScrutin('pres_t1', 0, parts, .8)], .8, algo)
    for parts in cas for algo in ALGOS
], sort_keys=True))
"""
    # Le dernier profil couvre aussi les égalités en bas de classement.
    cas = [parts for parts, *_ in CAS] + [{"gauche": 0.5, "droite": 0.25, "centre": 0.25}]
    sorties = [
        subprocess.check_output(
            [sys.executable, "-c", programme, json.dumps(cas)],
            cwd=Path(__file__).resolve().parents[1],
            env={**os.environ, "PYTHONHASHSEED": str(graine)},
            text=True,
            timeout=15,
        )
        for graine in (1, 2, 3, 4, 5, 42)
    ]
    assert all(sortie == sorties[0] for sortie in sorties[1:])
