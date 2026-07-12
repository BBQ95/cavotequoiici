"""Tests unitaires pour pipeline/couleur.py — modèle de couleur politique.

Spécification : Outline « Concept & modèle de couleur politique » §5.
TDD strict : tests écrits avant l'implémentation.
"""

import json
import math
from pathlib import Path

import pytest

from pipeline.couleur import (
    ALGOS,
    BLOCS,
    DEMI_VIE_ANNEES,
    PLANCHER_DESATURATION,
    POIDS_TYPE,
    SCRUTINS_MODULES,
    COULEURS,
    ResultatScrutin,
    clamp,
    couverture,
    poids_recence,
    poids_scrutin,
    hex_to_oklch,
    oklch_to_hex,
    couleur_ville,
    _charger_config_poids,
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

    # -- Tests de durcissement (revue Fred) ------------------------------------

    def test_famille_inconnue_dominante_fallback_divers(self):
        """Point 1 : une famille absente de COULEURS ne doit pas lever KeyError.

        La couleur de fallback doit être celle de « divers » (#9AA0A6).
        """
        scrutins = [
            ResultatScrutin(
                type_scrutin="pres_t1",
                age_annees=0.0,
                parts_familles={"inconnue_famille": 0.70, "gauche": 0.30},
                participation=0.60,
            ),
        ]
        # Ne doit pas lever KeyError
        resultat = couleur_ville(scrutins, participation_mediane=0.60)
        assert resultat["famille_dominante"] == "inconnue_famille"
        assert resultat["hex"].startswith("#")
        assert len(resultat["hex"]) == 7
        # La couleur produite doit correspondre au fallback « divers »
        couleur_oklch = hex_to_oklch(resultat["hex"])
        base_divers = hex_to_oklch(COULEURS["divers"])
        # Le hue doit être identique à celui de divers
        assert abs(couleur_oklch.H - base_divers.H) < 1.0

    def test_participation_mediane_zero_pas_zero_division(self):
        """Point 2 : participation_mediane == 0 ne doit pas lever ZeroDivisionError.

        Le facteur_participation doit tomber au plancher 0.55.
        """
        scrutins = [
            ResultatScrutin(
                type_scrutin="pres_t1",
                age_annees=0.0,
                parts_familles={"gauche": 0.55, "droite": 0.45},
                participation=0.65,
            ),
        ]
        # Ne doit pas lever ZeroDivisionError
        resultat = couleur_ville(scrutins, participation_mediane=0.0)
        assert resultat["hex"].startswith("#")
        assert len(resultat["hex"]) == 7
        assert resultat["famille_dominante"] == "gauche"
        # Vérifier que la chroma correspond au plancher 0.55
        couleur_oklch = hex_to_oklch(resultat["hex"])
        base_gauche = hex_to_oklch(COULEURS["gauche"])
        # Avec facteur_participation = 0.55 et saturation_marge = 0.45 + marge*1.6
        # marge = 0.55 - 0.45 = 0.10 → saturation_marge = 0.45 + 0.16 = 0.61
        expected_C = base_gauche.C * 0.61 * 0.55
        assert math.isclose(couleur_oklch.C, expected_C, rel_tol=0.01)

    def test_t2_famille_absente_non_dans_repartition(self):
        """Point 3 : une famille n'apparaissant qu'en second tour ne doit
        pas figurer dans la repartition (qui ne somme que sur les scrutins
        retenus, i.e. t1).
        """
        scrutins = [
            ResultatScrutin(
                type_scrutin="pres_t1",
                age_annees=1.0,
                parts_familles={"gauche": 0.55, "droite": 0.45},
                participation=0.65,
            ),
            ResultatScrutin(
                type_scrutin="pres_t2",
                age_annees=0.5,
                parts_familles={"gauche": 0.50, "ecologistes": 0.50},
                participation=0.60,
            ),
        ]
        resultat = couleur_ville(scrutins, participation_mediane=0.60)
        familles_repartition = {f for f, _ in resultat["repartition"]}
        # « ecologistes » n'apparaît qu'en t2 → ne doit pas figurer
        assert "ecologistes" not in familles_repartition
        # Les familles de t1 doivent figurer
        assert "gauche" in familles_repartition
        assert "droite" in familles_repartition

    def test_repartition_arrondie_trois_decimales(self):
        """Point 3 (suite) : les valeurs de repartition sont arrondies à 3 décimales."""
        scrutins = [
            ResultatScrutin(
                type_scrutin="pres_t1",
                age_annees=0.0,
                parts_familles={"gauche": 0.523456, "droite": 0.476544},
                participation=0.60,
            ),
        ]
        resultat = couleur_ville(scrutins, participation_mediane=0.60)
        for famille, part in resultat["repartition"]:
            assert round(part, 3) == part, (
                f"repartition[{famille}] non arrondi à 3 décimales : {part}"
            )


# ---------------------------------------------------------------------------
# couleur_ville — algos alternatifs de dominance (P1 Todo)
# ---------------------------------------------------------------------------


class TestCouleurVilleAlgos:
    """Trois algos sélectionnables : « complet » (statu quo, pluralité 7 familles),
    « tendance » (divers exclu de la dominance, renormalisation sur les familles
    politiques) et « blocs » (gauche/centre/droite agrégés avant dominance).
    La répartition retournée reste TOUJOURS le classement complet (transparence).
    """

    @pytest.fixture
    def commune_lud_rurale(self):
        """Profil FICTIF (ne PAS synchroniser avec une commune réelle : les
        résultats réels dérivent à chaque scrutin et casseraient le test).

        Commune rurale < 1000 hab. : municipales 100 % sans étiquette (LUD →
        divers), scrutins nationaux penchant à droite. La couverture S4 annule le
        poids de ses municipales non classables → l'extrême droite l'emporte dans
        les trois algos (cf. `test_reperes.py` pour l'équivalent sur données réelles).
        """
        return [
            ResultatScrutin(
                type_scrutin="pres_t1",
                age_annees=4.2,
                parts_familles={
                    "centre": 0.33,
                    "extreme_droite": 0.26,
                    "divers": 0.15,
                    "gauche": 0.11,
                    "droite": 0.08,
                    "extreme_gauche": 0.04,
                    "ecologistes": 0.03,
                },
                participation=0.79,
            ),
            ResultatScrutin(
                type_scrutin="leg_t1",
                age_annees=2.0,
                parts_familles={
                    "droite": 0.37,
                    "extreme_droite": 0.33,
                    "centre": 0.15,
                    "gauche": 0.15,
                },
                participation=0.75,
            ),
            ResultatScrutin(
                type_scrutin="mun_t1",
                age_annees=0.3,
                parts_familles={"divers": 1.0},
                participation=0.85,
            ),
        ]

    # -- algo « complet » (défaut) : comportement inchangé ---------------------

    def test_defaut_est_complet(self, commune_lud_rurale):
        implicite = couleur_ville(commune_lud_rurale, participation_mediane=0.74)
        explicite = couleur_ville(commune_lud_rurale, participation_mediane=0.74, algo="complet")
        assert implicite == explicite

    def test_complet_commune_lud_couverture_s4_marine(self, commune_lud_rurale):
        """P1/S4 : les municipales 100 % « sans étiquette » ont un taux de
        couverture nul → leur poids tombe à 0 et l'extrême droite l'emporte
        dès l'algo complet (fini le quasi-gris rapporté avant P1)."""
        resultat = couleur_ville(commune_lud_rurale, participation_mediane=0.74)
        assert resultat["famille_dominante"] == "extreme_droite"
        # Teinte marine (extrême droite), pas le gris « divers »
        attendu = hex_to_oklch(COULEURS["extreme_droite"])
        ok = hex_to_oklch(resultat["hex"])
        assert abs(ok.H - attendu.H) < 15
        # Le poids relatif des municipales est ramené à 0 par la couverture
        poids = dict(resultat["scrutins_inclus"])
        assert poids["mun_t1"] == 0.0

    # -- algo « tendance » : divers exclu de la dominance ----------------------

    def test_tendance_commune_lud_coloree(self, commune_lud_rurale):
        resultat = couleur_ville(commune_lud_rurale, participation_mediane=0.74, algo="tendance")
        assert resultat["famille_dominante"] == "extreme_droite"
        # Teinte de l'extrême droite (bleu marine), pas du gris
        attendu = hex_to_oklch(COULEURS["extreme_droite"])
        ok = hex_to_oklch(resultat["hex"])
        assert abs(ok.H - attendu.H) < 15
        # Distincte du gris « divers » (teinte et non simple désaturation)
        gris = hex_to_oklch(COULEURS["divers"])
        assert abs(ok.H - gris.H) > 10

    def test_tendance_part_et_marge_renormalisees(self, commune_lud_rurale):
        """part/marge sont renormalisées sur les familles politiques (hors divers)."""
        complet = couleur_ville(commune_lud_rurale, participation_mediane=0.74)
        tendance = couleur_ville(commune_lud_rurale, participation_mediane=0.74, algo="tendance")
        # La part renormalisée de l'ED dépasse sa part brute du classement complet
        part_brute_ed = dict(complet["repartition"])["extreme_droite"]
        assert tendance["part_synthetique"] > part_brute_ed
        assert 0.0 < tendance["marge"] <= 1.0

    def test_tendance_repartition_reste_complete(self, commune_lud_rurale):
        """Transparence : divers reste visible dans la répartition retournée."""
        resultat = couleur_ville(commune_lud_rurale, participation_mediane=0.74, algo="tendance")
        assert "divers" in dict(resultat["repartition"])

    def test_complet_vs_tendance_different_quand_divers_domine(self):
        """Cœur du besoin « tendance » : quand les sans-étiquette (divers)
        arrivent EN TÊTE du classement complet, l'algo « tendance » bascule sur
        la première famille politique → teinte (et hex) réellement différentes.

        Profil FICTIF (indépendant de toute commune réelle, donc insensible à la
        dérive des résultats au fil des scrutins) : divers domine via un scrutin
        NATIONAL — non annulé par la couverture S4, contrairement aux municipales.
        C'est la version robuste des anciens tests d'intégration sur Saint-Urcize.
        """
        commune = [
            ResultatScrutin(
                type_scrutin="pres_t1",
                age_annees=2.0,
                parts_familles={
                    "divers": 0.40,
                    "extreme_droite": 0.34,
                    "gauche": 0.16,
                    "centre": 0.10,
                },
                participation=0.70,
            ),
        ]
        complet = couleur_ville(commune, participation_mediane=0.70)
        tendance = couleur_ville(commune, participation_mediane=0.70, algo="tendance")
        # complet : divers remporte la pluralité (quasi-gris)
        assert complet["famille_dominante"] == "divers"
        # tendance : divers écarté de la dominance → l'extrême droite l'emporte
        assert tendance["famille_dominante"] == "extreme_droite"
        # la teinte change donc réellement (ce que vérifiait l'ancien test réel)
        assert tendance["hex"] != complet["hex"]
        # transparence : la répartition renvoyée reste identique (divers visible)
        assert tendance["repartition"] == complet["repartition"]

    def test_tendance_sans_famille_politique_reste_divers(self):
        """Une commune 100 % divers reste grise (rien à renormaliser)."""
        scrutins = [
            ResultatScrutin(
                type_scrutin="mun_t1",
                age_annees=0.3,
                parts_familles={"divers": 1.0},
                participation=0.85,
            ),
        ]
        resultat = couleur_ville(scrutins, participation_mediane=0.74, algo="tendance")
        assert resultat["famille_dominante"] == "divers"

    def test_tendance_identique_sans_divers(self):
        """Sans voix divers, tendance == complet (même hex)."""
        scrutins = [
            ResultatScrutin(
                type_scrutin="pres_t1",
                age_annees=2.0,
                parts_familles={"gauche": 0.55, "droite": 0.45},
                participation=0.65,
            ),
        ]
        complet = couleur_ville(scrutins, participation_mediane=0.60)
        tendance = couleur_ville(scrutins, participation_mediane=0.60, algo="tendance")
        assert complet["hex"] == tendance["hex"]
        assert complet["famille_dominante"] == tendance["famille_dominante"]

    # -- algo « blocs » : gauche/centre/droite agrégés --------------------------

    def test_blocs_commune_lud_bloc_droite(self, commune_lud_rurale):
        resultat = couleur_ville(commune_lud_rurale, participation_mediane=0.74, algo="blocs")
        # Bloc droite (droite + extrême droite) gagne ; la teinte vient de la
        # sous-famille dominante du bloc (ici l'extrême droite).
        assert resultat["famille_dominante"] == "extreme_droite"
        tendance = couleur_ville(commune_lud_rurale, participation_mediane=0.74, algo="tendance")
        assert resultat["marge"] >= tendance["marge"]

    def test_blocs_camp_divise_gagne_uni(self):
        """Un camp divisé en deux familles ne perd plus face à un camp uni
        (limite « blocs divisés » de la méthodologie)."""
        scrutins = [
            ResultatScrutin(
                type_scrutin="pres_t1",
                age_annees=1.0,
                parts_familles={
                    "extreme_gauche": 0.28,
                    "gauche": 0.27,
                    "droite": 0.40,
                    "centre": 0.05,
                },
                participation=0.65,
            ),
        ]
        complet = couleur_ville(scrutins, participation_mediane=0.60)
        blocs = couleur_ville(scrutins, participation_mediane=0.60, algo="blocs")
        assert complet["famille_dominante"] == "droite"
        # Bloc gauche = 0.55 > bloc droite = 0.40 ; sous-famille max = EG
        assert blocs["famille_dominante"] == "extreme_gauche"

    def test_blocs_sans_famille_politique_reste_divers(self):
        scrutins = [
            ResultatScrutin(
                type_scrutin="mun_t1",
                age_annees=0.3,
                parts_familles={"divers": 1.0},
                participation=0.85,
            ),
        ]
        resultat = couleur_ville(scrutins, participation_mediane=0.74, algo="blocs")
        assert resultat["famille_dominante"] == "divers"

    # -- garde-fous -------------------------------------------------------------

    def test_algo_inconnu_leve_valueerror(self, commune_lud_rurale):
        with pytest.raises(ValueError):
            couleur_ville(commune_lud_rurale, participation_mediane=0.74, algo="magique")

    def test_resultat_porte_l_algo(self, commune_lud_rurale):
        for algo in ("complet", "tendance", "blocs"):
            resultat = couleur_ville(commune_lud_rurale, participation_mediane=0.74, algo=algo)
            assert resultat["algo"] == algo


# ---------------------------------------------------------------------------
# couverture + modulation S4 (P1 — pondération « S1+S4 »)
# ---------------------------------------------------------------------------


class TestCouverture:
    """Taux de couverture = part des exprimés portant une nuance classable."""

    def test_tout_divers_couverture_nulle(self):
        rs = ResultatScrutin("mun_t1", 0.3, {"divers": 1.0}, 0.85)
        assert couverture(rs) == 0.0

    def test_tout_classe_couverture_pleine(self):
        rs = ResultatScrutin("mun_t1", 0.3, {"gauche": 0.6, "droite": 0.4}, 0.85)
        assert math.isclose(couverture(rs), 1.0)

    def test_partiellement_sans_etiquette(self):
        # 40 % des exprimés sont « sans étiquette » (LUD → divers)
        rs = ResultatScrutin("mun_t1", 0.3, {"gauche": 0.6, "divers": 0.4}, 0.85)
        assert math.isclose(couverture(rs), 0.6)

    def test_denominateur_exprimes_non_normalise(self):
        # parts_familles est normalisé sur les exprimés : elles peuvent ne pas
        # sommer à 1 (nuances non mappées écartées). La couverture reste la
        # somme des parts classables telle quelle.
        rs = ResultatScrutin("mun_t1", 0.3, {"droite": 0.5, "divers": 0.3}, 0.85)
        assert math.isclose(couverture(rs), 0.5)

    def test_mun_est_module(self):
        assert "mun_t1" in SCRUTINS_MODULES


class TestModulationCouverture:
    """Le poids des scrutins de SCRUTINS_MODULES est × leur taux de couverture."""

    def test_mun_couverture_nulle_exclue_de_la_synthese(self):
        """Une municipale 100 % divers ne pèse plus rien : sa couleur ne
        vient que des scrutins nationaux."""
        scrutins = [
            ResultatScrutin("pres_t1", 2.0, {"extreme_droite": 0.6, "gauche": 0.4}, 0.70),
            ResultatScrutin("mun_t1", 0.3, {"divers": 1.0}, 0.85),
        ]
        resultat = couleur_ville(scrutins, participation_mediane=0.60)
        poids = dict(resultat["scrutins_inclus"])
        assert poids["mun_t1"] == 0.0
        assert math.isclose(poids["pres_t1"], 1.0, abs_tol=1e-6)
        assert resultat["famille_dominante"] == "extreme_droite"

    def test_mun_couverture_partielle_reduit_le_poids(self):
        """Une municipale à couverture 0,6 (40 % sans étiquette) pèse moins,
        relativement, qu'une municipale à couverture pleine."""
        pres = ResultatScrutin("pres_t1", 0.0, {"gauche": 0.6, "droite": 0.4}, 0.70)
        mun_pleine = ResultatScrutin("mun_t1", 0.0, {"gauche": 0.6, "droite": 0.4}, 0.70)
        mun_partielle = ResultatScrutin("mun_t1", 0.0, {"gauche": 0.3, "droite": 0.3, "divers": 0.4}, 0.70)
        assert math.isclose(couverture(mun_partielle), 0.6)
        poids_pleine = dict(couleur_ville([pres, mun_pleine], 0.60)["scrutins_inclus"])
        poids_partielle = dict(couleur_ville([pres, mun_partielle], 0.60)["scrutins_inclus"])
        assert poids_partielle["mun_t1"] < poids_pleine["mun_t1"]

    def test_repli_commune_uniquement_mun_non_classable(self):
        """Commune n'ayant que des municipales 100 % divers : la modulation
        annulerait tous les poids → repli sans modulation (couleur grise),
        pas de ValueError."""
        scrutins = [ResultatScrutin("mun_t1", 0.3, {"divers": 1.0}, 0.85)]
        resultat = couleur_ville(scrutins, participation_mediane=0.60)
        assert resultat["famille_dominante"] == "divers"
        # Le scrutin reste présent (repli), poids relatif 1.0
        assert math.isclose(dict(resultat["scrutins_inclus"])["mun_t1"], 1.0, abs_tol=1e-6)

    def test_mono_scrutin_mun_non_module_reste_calculable(self):
        """Appel mono-scrutin (comme couleurs_scrutin) sur une municipale non
        classable : le repli évite le crash et donne la couleur du scrutin."""
        scrutins = [ResultatScrutin("mun_t1", 0.3, {"gauche": 0.5, "divers": 0.5}, 0.85)]
        resultat = couleur_ville(scrutins, participation_mediane=0.60)
        # Un seul scrutin → poids relatif 1.0 quelle que soit la couverture
        assert math.isclose(dict(resultat["scrutins_inclus"])["mun_t1"], 1.0, abs_tol=1e-6)


class TestInvarianceDateCalcul:
    """La décroissance exponentielle est « sans mémoire » : décaler toutes les
    dates de calcul d'une constante ne change pas la couleur (seuls comptent
    les écarts d'âge entre scrutins). Cf. note méthodo « Demi-vie vs poids fixes »."""

    def _commune(self, decalage: float):
        return [
            ResultatScrutin("pres_t1", 2.0 + decalage, {"gauche": 0.55, "droite": 0.30, "extreme_droite": 0.15}, 0.65),
            ResultatScrutin("leg_t1", 1.0 + decalage, {"gauche": 0.60, "droite": 0.25, "extreme_droite": 0.15}, 0.50),
            ResultatScrutin("mun_t1", 0.3 + decalage, {"gauche": 0.45, "droite": 0.25, "divers": 0.30}, 0.70),
        ]

    def test_hex_invariant_au_decalage(self):
        for algo in ("complet", "tendance", "blocs"):
            ref = couleur_ville(self._commune(0.0), 0.60, algo=algo)
            plus_tard = couleur_ville(self._commune(5.0), 0.60, algo=algo)
            assert ref["hex"] == plus_tard["hex"], f"algo={algo}"
            assert ref["famille_dominante"] == plus_tard["famille_dominante"]


# ---------------------------------------------------------------------------
# Config poids.toml — tous les paramètres viennent du fichier (source unique)
# ---------------------------------------------------------------------------


class TestFixturesBlocs:
    def test_fixtures_a_jour(self):
        """Le fichier de parité consommé par le test TS du mobile doit refléter
        BLOCS : s'il casse ici, mettre à jour la fixture ET le port TS
        (mobile/src/lib/blocs.ts)."""
        fixture = Path(__file__).parent / "fixtures" / "blocs_parite.json"
        blocs = json.loads(fixture.read_text("utf-8"))["blocs"]
        assert blocs == BLOCS


class TestFixturesAlgos:
    def test_fixtures_a_jour(self):
        """Le fichier de parité consommé par le test TS du mobile doit refléter
        ALGOS : s'il casse ici, mettre à jour la fixture ET la const TS
        (mobile/src/api/types.ts)."""
        fixture = Path(__file__).parent / "fixtures" / "algos_parite.json"
        algos = json.loads(fixture.read_text("utf-8"))["algos"]
        assert algos == list(ALGOS)


class TestConfigPoids:
    """poids.toml est la seule source de vérité : poids, scrutins modulés,
    demi-vie de récence ET plancher de désaturation."""

    def test_valeurs_courantes_chargees_du_fichier(self):
        assert DEMI_VIE_ANNEES == 6.0
        assert PLANCHER_DESATURATION == 0.55
        assert "mun_t1" in SCRUTINS_MODULES

    def test_loader_lit_toutes_les_sections(self, tmp_path):
        toml = tmp_path / "poids.toml"
        toml.write_text(
            "[defaut]\n"
            "pres_t1 = 1.0\n"
            "mun_t1 = 0.4\n"
            "[s4]\n"
            "scrutins_moduls = [\"mun_t1\"]\n"
            "[recence]\n"
            "demi_vie_ans = 8.0\n"
            "[desaturation]\n"
            "plancher = 0.6\n"
        )
        poids, modules, demi_vie, plancher = _charger_config_poids(toml)
        assert poids == {"pres_t1": 1.0, "mun_t1": 0.4}
        assert modules == frozenset({"mun_t1"})
        assert demi_vie == 8.0
        assert plancher == 0.6

    def test_loader_valeurs_par_defaut_si_sections_absentes(self, tmp_path):
        toml = tmp_path / "poids.toml"
        toml.write_text("[defaut]\npres_t1 = 1.0\n")
        _poids, modules, demi_vie, plancher = _charger_config_poids(toml)
        assert modules == frozenset()
        assert demi_vie == 6.0
        assert plancher == 0.55
