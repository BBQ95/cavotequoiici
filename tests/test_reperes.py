"""Test des communes repères — critère BLOQUANT de l'Étape 3 (guide §3.3).

Intégration : vérifie, dans la table couleurs_ville peuplée, que la teinte (H OKLCH)
des communes repères tombe dans la plage attendue. Ignoré si DATABASE_URL absente.
"""

import os

import pytest

DB = os.environ.get("DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DB, reason="DATABASE_URL non définie (test d'intégration BDD)"
)

# code_insee -> (nom, H_min, H_max) en OKLCH
# rouge/rose (gauches) ≈ [5, 45] ; bleu marine (extrême droite) ≈ [240, 275]
REPERES = {
    "93066": ("Saint-Denis", 5, 45),       # gauche/extrême gauche → rouge
    "06088": ("Nice", 240, 275),            # extrême droite → marine
    "62427": ("Hénin-Beaumont", 240, 275),  # extrême droite → marine
    "38185": ("Grenoble", 5, 160),          # pôle gauche/écolo → rose à vert
}


def test_reperes_teinte():
    from sqlalchemy import create_engine, text

    engine = create_engine(DB)
    with engine.connect() as conn:
        for code, (nom, hmin, hmax) in REPERES.items():
            row = conn.execute(
                text("SELECT h FROM couleurs_ville WHERE code_insee = :x"),
                {"x": code},
            ).fetchone()
            assert row is not None, f"{nom} ({code}) absent de couleurs_ville"
            h = row[0]
            assert hmin <= h <= hmax, f"{nom} : H={h:.1f} hors de [{hmin}, {hmax}]"


def test_reperes_algos():
    """P1 / pondération « S1+S4 » : les communes « sans étiquette » sont colorées.

    Saint-Urcize (15216, rurale < 1000 hab., municipales 100 % LUD) était grise
    avec l'algo complet. Avec la couverture S4, le poids de ses municipales non
    classables tombe à 0 et l'extrême droite (marine) l'emporte désormais dans
    les TROIS algos. Les repères historiques ne doivent PAS changer de famille
    entre complet et tendance.
    """
    from sqlalchemy import create_engine, text

    engine = create_engine(DB)
    with engine.connect() as conn:
        lignes = conn.execute(
            text(
                "SELECT algo, h, famille_dominante FROM couleurs_ville_algo "
                "WHERE code_insee = '15216'"
            ),
        ).fetchall()
        assert len(lignes) == 3, "3 algos attendus pour Saint-Urcize"
        par_algo = {r.algo: r for r in lignes}
        for algo in ("complet", "tendance", "blocs"):
            assert par_algo[algo].famille_dominante == "extreme_droite", algo
            assert 240 <= par_algo[algo].h <= 275, f"{algo} : H hors marine"

        # Non-régression des repères : même famille en complet et tendance.
        for code, (nom, _, _) in REPERES.items():
            familles = dict(
                conn.execute(
                    text(
                        "SELECT algo, famille_dominante FROM couleurs_ville_algo "
                        "WHERE code_insee = :x AND algo IN ('complet', 'tendance')"
                    ),
                    {"x": code},
                ).fetchall()
            )
            assert familles["complet"] == familles["tendance"], nom
