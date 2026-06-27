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
