"""Tests unitaires pour pipeline/couleur.py — modèle de couleur politique.

Spécification : Outline « Concept & modèle de couleur politique » §5.
TDD strict : tests écrits avant l'implémentation.
"""

import math
import pytest

from pipeline.couleur import (
    DEMI_VIE_ANNEES,
    POIDS_TYPE,
    COULEURS,
    ResultatScrutin,
    clamp,
    poids_recence,
    poids_scrutin,
    hex_to_oklch,
    oklch_to_hex,
    couleur_ville,
)


# ---------------------------------------------------------------------------
# clamp
# ---------------------------------------------------------------------------

class TestClamp:
    def test_valeur_dans_intervalle(self):
        assert clamp(5, 0, 10) == 5

    def test_valeur_sous_minimum(self):
        assert clamp(-3, 0, 10) == 0

    def test_valeur_au_minimum(self):
        assert clamp(0, 0, 10) == 0

    def test_valeur_au_maximum(self):
        assert clamp(10, 0, 10) == 10

    def test_valeur_au_dessus_maximum(self):
        assert clamp(15, 0, 10) == 10

    def test_valeurs_flottantes(self):
        assert math.isclose(clamp(0.5, 0.45, 1.0), 0.5)


# ---------------------------------------------------------------------------
# poids_recence
# ---------------------------------------------------------------------------

class TestPoidsRecence:
    def test_age_zero(self):
        assert math.isclose(poids_recence(0), 1.0)

    def test_age_demi_vie(self):
        # à la demi-vie, le poids vaut 0.5
        assert math.isclose(poids_recence(DEMI_VIE_ANNEES), 0.5)

    def test_age_double_demi_vie(self):
        # à 2× la demi-vie, le poids vaut 0.25
        assert math.isclose(poids_recence(DEMI_VIE_ANNEES * 2), 0.25)

    def test_age_trois_demi_vie(self):
        # à 3× la demi-vie, le poids vaut 0.125
        assert math.isclose(poids_recence(DEMI_VIE_ANNEES * 3), 0.125, abs_tol=1e-9)

    def test_croissance_decroissante(self):
        """Plus c'est récent, plus le poids est élevé."""
        assert poids_recence(2) > poids_recence(4) > poids_recence(8)


# ---------------------------------------------------------------------------
# poids_scrutin
# ---------------------------------------------------------------------------

class TestPoidsScrutin:
    def test_type_connu_age_zero(self):
        # poids_brut × 1.0 (récence 0 ans)
        assert math.isclose(poids_scrutin("pres_t1", 0), POIDS_TYPE["pres_t1"])

    def test_type_connu_avec_recence(self):
        expected = POIDS_TYPE["leg_t1"] * 0.5 ** (6.0 / DEMI_VIE_ANNEES)
        assert math.isclose(poids_scrutin("leg_t1", 6.0), expected)

    def test_type_inconnu_retourne_zero(self):
        """Les seconds tours (type absent de POIDS_TYPE) doivent retourner 0."""
        assert poids_scrutin("pres_t2", 0) == 0
        assert poids_scrutin("leg_t2", 3) == 0
        assert poids_scrutin("inconnu", 5) == 0

    def test_combinaison_type_recence(self):
        """poids_scrutin = POIDS_TYPE[type] × poids_recence(age)."""
        for type_scrutin, poids_brut in POIDS_TYPE.items():
            for age in (0, 3, 6, 12):
                expected = poids_brut * 0.5 ** (age / DEMI_VIE_ANNEES)
                assert math.isclose(
                    poids_scrutin(type_scrutin, age), expected, rel_tol=1e-9
                ), f"Échec pour {type_scrutin} age={age}"


# ---------------------------------------------------------------------------
# hex_to_oklch / oklch_to_hex
# ---------------------------------------------------------------------------

class TestOKLCH:
    @pytest.mark.parametrize("famille,hex_code", sorted(COULEURS.items()))
    def test_round_trip_toutes_les_couleurs(self, famille, hex_code):
        """oklch_to_hex(hex_to_oklch(hex)) ≈ hex (aux arrondis 8-bit près)."""
        oklch = hex_to_oklch(hex_code)
        hex_retour = oklch_to_hex(oklch)
        # Comparaison au niveau RGB (chaque canal à ±1 près)
        r1, g1, b1 = int(hex_code[1:3], 16), int(hex_code[3:5], 16), int(hex_code[5:7], 16)
        r2, g2, b2 = int(hex_retour[1:3], 16), int(hex_retour[3:5], 16), int(hex_retour[5:7], 16)
        assert abs(r1 - r2) <= 1, f"{famille}: R {r1} vs {r2}"
        assert abs(g1 - g2) <= 1, f"{famille}: G {g1} vs {g2}"
        assert abs(b1 - b2) <= 1, f"{famille}: B {b1} vs {b2}"

    def test_hex_to_oklch_format(self):
        """hex_to_oklch retourne un objet avec attributs L, C, H."""
        oklch = hex_to_oklch("#FFB300")
        assert hasattr(oklch, "L")
        assert hasattr(oklch, "C")
        assert hasattr(oklch, "H")
        assert 0 <= oklch.L <= 1
        assert oklch.C >= 0

    def test_hex_noir_blanc(self):
        oklch_noir = hex_to_oklch("#000000")
        assert math.isclose(oklch_noir.L, 0.0, abs_tol=1e-4)
        oklch_blanc = hex_to_oklch("#FFFFFF")
        assert math.isclose(oklch_blanc.L, 1.0, abs_tol=1e-4)

    def test_h_degrise_pour_gris(self):
        """Un gris pur doit avoir une chroma faible (presque nulle)."""
        oklch = hex_to_oklch("#808080")
        assert oklch.C < 0.01


# ---------------------------------------------------------------------------
# couleur_ville
# ---------------------------------------------------------------------------

class TestCouleurVille:
    # -- Jeux de données réalistes -------------------------------------------

    @pytest.fixture
    def saint_denis(self):
        """Saint-Denis : ville historiquement à gauche (rouge adouci)."""
        return [
            ResultatScrutin(
                type_scrutin="pres_t1",
                age_annees=2.0,
                parts_familles={"gauche": 0.55, "centre": 0.20, "extreme_droite": 0.25},
                participation=0.65,
            ),
            ResultatScrutin(
                type_scrutin="leg_t1",
                age_annees=1.0,
                parts_familles={"gauche": 0.60, "extreme_droite": 0.25, "centre": 0.15},
                participation=0.50,
            ),
        ]

    @pytest.fixture
    def nice(self):
        """Nice : ville historiquement à droite / extrême droite (bleu foncé)."""
        return [
            ResultatScrutin(
                type_scrutin="pres_t1",
                age_annees=2.0,
                parts_familles={"extreme_droite": 0.48, "droite": 0.30, "gauche": 0.22},
                participation=0.70,
            ),
            ResultatScrutin(
                type_scrutin="euro",
                age_annees=3.0,
                parts_familles={"extreme_droite": 0.52, "droite": 0.28, "gauche": 0.20},
                participation=0.35,
            ),
        ]

    # -- Tests ----------------------------------------------------------------

    def test_saint_denis_famille_dominante_gauche(self, saint_denis):
        resultat = couleur_ville(saint_denis, participation_mediane=0.60)
        assert resultat["famille_dominante"] == "gauche"
        assert resultat["part_synthetique"] > 0.40
        assert resultat["marge"] > 0.0
        assert resultat["participation"] > 0.0
        assert resultat["hex"].startswith("#")
        assert len(resultat["hex"]) == 7

    def test_nice_famille_dominante_extreme_droite(self, nice):
        resultat = couleur_ville(nice, participation_mediane=0.55)
        assert resultat["famille_dominante"] == "extreme_droite"
        assert resultat["part_synthetique"] > 0.40
        assert resultat["marge"] > 0.0
        assert resultat["hex"].startswith("#")
        assert len(resultat["hex"]) == 7

    def test_couleur_saint_denis_rouge_adouci(self, saint_denis):
        """Saint-Denis doit produire une teinte rouge (proche de la gauche)."""
        resultat = couleur_ville(saint_denis, participation_mediane=0.60)
        # La famille dominante est « gauche » dont le hex de base est #E84E6B
        # → rouge/rosé. Vérifier que le H (hue) de la couleur produite est
        # proche de celui de la gauche.
        couleur_oklch = hex_to_oklch(resultat["hex"])
        base_gauche = hex_to_oklch(COULEURS["gauche"])
        # Tolérance de 30° sur le hue
        assert abs(couleur_oklch.H - base_gauche.H) < 30 or \
               abs(couleur_oklch.H - base_gauche.H) > 330

    def test_couleur_nice_bleu_fonce(self, nice):
        """Nice doit produire une teinte bleu foncé."""
        resultat = couleur_ville(nice, participation_mediane=0.55)
        couleur_oklch = hex_to_oklch(resultat["hex"])
        base_ed = hex_to_oklch(COULEURS["extreme_droite"])
        # Le hue de l'extrême-droite (#16243F) est un bleu foncé
        assert abs(couleur_oklch.H - base_ed.H) < 30 or \
               abs(couleur_oklch.H - base_ed.H) > 330

    def test_un_seul_scrutin(self):
        """Cas avec un seul scrutin : poids = 1 pour ce scrutin."""
        scrutins = [
            ResultatScrutin(
                type_scrutin="pres_t1",
                age_annees=0.0,
                parts_familles={"gauche": 0.50, "droite": 0.50},
                participation=0.60,
            ),
        ]
        resultat = couleur_ville(scrutins, participation_mediane=0.60)
        # Avec 50/50 et un seul scrutin, marge = 0
        assert math.isclose(resultat["marge"], 0.0, abs_tol=1e-6)
        assert resultat["famille_dominante"] in ("gauche", "droite")
        # Le scrutin inclus doit avoir un poids relatif de 1.0
        assert len(resultat["scrutins_inclus"]) == 1
        assert math.isclose(resultat["scrutins_inclus"][0][1], 1.0, abs_tol=1e-6)

    def test_scrutins_multiples_poids_relatifs(self):
        """Vérifier que les poids relatifs somment à ~1."""
        scrutins = [
            ResultatScrutin(
                type_scrutin="pres_t1",
                age_annees=0.0,
                parts_familles={"gauche": 0.60, "droite": 0.40},
                participation=0.70,
            ),
            ResultatScrutin(
                type_scrutin="leg_t1",
                age_annees=2.0,
                parts_familles={"gauche": 0.50, "droite": 0.50},
                participation=0.50,
            ),
        ]
        resultat = couleur_ville(scrutins, participation_mediane=0.60)
        poids_rels = [w for _, w in resultat["scrutins_inclus"]]
        assert math.isclose(sum(poids_rels), 1.0, abs_tol=1e-6)
        # pres_t1 (poids_brut=1.0, age=0) > leg_t1 (poids_brut=0.8, age=2)
        assert poids_rels[0] > poids_rels[1]

    def test_seconds_tours_exclus(self):
        """Un scrutin de type second tour doit être ignoré du calcul."""
        scrutins = [
            ResultatScrutin(
                type_scrutin="pres_t1",
                age_annees=1.0,
                parts_familles={"gauche": 0.55, "extreme_droite": 0.45},
                participation=0.65,
            ),
            ResultatScrutin(
                type_scrutin="pres_t2",  # non dans POIDS_TYPE
                age_annees=0.5,
                parts_familles={"gauche": 0.58, "extreme_droite": 0.42},
                participation=0.60,
            ),
        ]
        resultat = couleur_ville(scrutins, participation_mediane=0.60)
        # Seul le premier tour est inclus
        assert len(resultat["scrutins_inclus"]) == 1
        assert resultat["scrutins_inclus"][0][0] == "pres_t1"

    def test_tous_scrutins_second_tours_resultat_vide(self):
        """Si tous les scrutins sont des seconds tours, on évite une division par zéro."""
        scrutins = [
            ResultatScrutin(
                type_scrutin="pres_t2",
                age_annees=0.5,
                parts_familles={"gauche": 0.58, "extreme_droite": 0.42},
                participation=0.60,
            ),
        ]
        # Doit lever une erreur ou gérer gracieusement ; ici on teste qu'on
        # ne plante pas par division par zéro — on s'attend à une ValueError
        # (comportement documenté : au moins un scrutin t1 est requis)
        with pytest.raises(ValueError):
            couleur_ville(scrutins, participation_mediane=0.60)

    def test_participation_basse_desaturation(self):
        """Une participation très basse doit désaturer la couleur."""
        scrutin_haute_participation = ResultatScrutin(
            type_scrutin="pres_t1",
            age_annees=0.0,
            parts_familles={"gauche": 0.55, "droite": 0.45},
            participation=0.80,
        )
        scrutin_basse_participation = ResultatScrutin(
            type_scrutin="pres_t1",
            age_annees=0.0,
            parts_familles={"gauche": 0.55, "droite": 0.45},
            participation=0.20,
        )

        couleur_haute = couleur_ville([scrutin_haute_participation], participation_mediane=0.60)
        couleur_basse = couleur_ville([scrutin_basse_participation], participation_mediane=0.60)

        oklch_haute = hex_to_oklch(couleur_haute["hex"])
        oklch_basse = hex_to_oklch(couleur_basse["hex"])
        # La chroma de la couleur à basse participation doit être inférieure
        # (désaturation par le facteur de participation)
        assert oklch_basse.C < oklch_haute.C

    def test_resultat_structure_complete(self):
        """Le résultat contient toutes les clés attendues."""
        scrutins = [
            ResultatScrutin(
                type_scrutin="pres_t1",
                age_annees=0.0,
                parts_familles={"gauche": 0.55, "droite": 0.45},
                participation=0.60,
            ),
        ]
        resultat = couleur_ville(scrutins, participation_mediane=0.60)
        for key in ("hex", "famille_dominante", "part_synthetique", "marge",
                    "participation", "scrutins_inclus", "repartition"):
            assert key in resultat, f"Clé manquante : {key}"

    def test_repartition_triee_decroissante(self):
        """La repartition doit être triée par part décroissante."""
        scrutins = [
            ResultatScrutin(
                type_scrutin="pres_t1",
                age_annees=0.0,
                parts_familles={"gauche": 0.50, "droite": 0.30, "centre": 0.20},
                participation=0.60,
            ),
        ]
        resultat = couleur_ville(scrutins, participation_mediane=0.60)
        parts = [p for _, p in resultat["repartition"]]
        assert parts == sorted(parts, reverse=True)

    def test_arrondis_trois_decimales(self):
        """part_synthetique, marge et participation sont arrondis à 3 décimales."""
        scrutins = [
            ResultatScrutin(
                type_scrutin="pres_t1",
                age_annees=0.0,
                parts_familles={"gauche": 0.523456, "droite": 0.476544},
                participation=0.60789,
            ),
        ]
        resultat = couleur_ville(scrutins, participation_mediane=0.60)
        for key in ("part_synthetique", "marge", "participation"):
            val = resultat[key]
            # Vérifier qu'on a au plus 3 décimales
            assert round(val, 3) == val, f"{key} non arrondi à 3 décimales : {val}"