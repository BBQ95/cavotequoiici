"""pipeline/couleur.py — Modèle de couleur politique.

Spécification canonique : Outline « Concept & modèle de couleur politique » §5.

Algorithme :
  1. Poids de chaque scrutin = poids_type × 0.5^(age / demi_vie)
  2. Parts synthétiques par famille politique (moyenne pondérée)
  3. Famille dominante + marge (écart vs 2ᵉ)
  4. Couleur = OKLCH(teinte dominante) modulée par la netteté × la participation

Les seconds tours sont exclus (absents de POIDS_TYPE).
"""

import math
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

DEMI_VIE_ANNEES = 6.0

POIDS_TYPE = {
    "pres_t1": 1.0,
    "leg_t1": 0.8,
    "euro": 0.7,
    "reg_t1": 0.6,
    "dep_t1": 0.6,
    "mun_t1": 0.5,
}

COULEURS = {
    "extreme_gauche": "#D60B0B",
    "gauche": "#E84E6B",
    "ecologistes": "#46A302",
    "centre": "#FFB300",
    "droite": "#2D6FCB",
    "extreme_droite": "#16243F",
    "divers": "#9AA0A6",
}

# Algos de dominance sélectionnables (P1 Todo — cf. étude Outline) :
#   complet  : pluralité sur les 7 familles, divers inclus (comportement historique)
#   tendance : divers exclu de la course, parts renormalisées sur les familles
#              politiques — les « sans étiquette » ne grisent plus la carte
#   blocs    : gauche/centre/droite agrégés avant dominance (un camp divisé en
#              deux familles ne perd plus face à un camp uni) ; la teinte vient
#              de la sous-famille dominante du bloc gagnant
ALGOS = ("complet", "tendance", "blocs")

BLOCS = {
    "extreme_gauche": "gauche",
    "gauche": "gauche",
    "ecologistes": "gauche",
    "centre": "centre",
    "droite": "droite",
    "extreme_droite": "droite",
}

# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------


@dataclass
class ResultatScrutin:
    type_scrutin: str
    age_annees: float
    parts_familles: dict[str, float]
    participation: float


# ---------------------------------------------------------------------------
# OKLCH (conversion manuelle sRGB → OKLab → OKLCH)
# ---------------------------------------------------------------------------


@dataclass
class OKLCH:
    L: float
    C: float
    H: float


def _srgb_to_linear(c: float) -> float:
    """canal sRGB [0,1] → RGB linéaire [0,1]."""
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def _linear_to_srgb(c: float) -> float:
    """RGB linéaire [0,1] → canal sRGB [0,1]."""
    if c <= 0.0031308:
        return 12.92 * c
    return 1.055 * (c ** (1.0 / 2.4)) - 0.055


def _linear_rgb_to_oklab(r: float, g: float, b: float) -> tuple[float, float, float]:
    """RGB linéaire → OKLab (Björn Ottosson 2020)."""
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b

    l_ = l ** (1.0 / 3.0)
    m_ = m ** (1.0 / 3.0)
    s_ = s ** (1.0 / 3.0)

    L = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    b_lab = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_

    return L, a, b_lab


def _oklab_to_linear_rgb(L: float, a: float, b: float) -> tuple[float, float, float]:
    """OKLab → RGB linéaire (inverse de ci-dessus)."""
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b

    l = l_ ** 3
    m = m_ ** 3
    s = s_ ** 3

    r = +4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    b_rgb = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s

    return r, g, b_rgb


def hex_to_oklch(hex_str: str) -> OKLCH:
    """Convertit un hex (#RRGGBB) en OKLCH (L, C, H)."""
    h = hex_str.lstrip("#")
    r = int(h[0:2], 16) / 255.0
    g = int(h[2:4], 16) / 255.0
    b = int(h[4:6], 16) / 255.0

    r_l = _srgb_to_linear(r)
    g_l = _srgb_to_linear(g)
    b_l = _srgb_to_linear(b)

    L, a, b_lab = _linear_rgb_to_oklab(r_l, g_l, b_l)

    C = (a * a + b_lab * b_lab) ** 0.5
    H = math.degrees(math.atan2(b_lab, a))
    if H < 0:
        H += 360.0

    return OKLCH(L=L, C=C, H=H)


def oklch_to_hex(oklch: OKLCH) -> str:
    """Convertit OKLCH vers hex (#RRGGBB)."""
    H_rad = math.radians(oklch.H)
    a = oklch.C * math.cos(H_rad)
    b = oklch.C * math.sin(H_rad)

    # Utiliser L, a, b pour recalculer le RGB linéaire
    r_l, g_l, b_l = _oklab_to_linear_rgb(oklch.L, a, b)

    r = _linear_to_srgb(r_l)
    g = _linear_to_srgb(g_l)
    b = _linear_to_srgb(b_l)

    r = max(0.0, min(1.0, r))
    g = max(0.0, min(1.0, g))
    b = max(0.0, min(1.0, b))

    return f"#{int(round(r * 255)):02X}{int(round(g * 255)):02X}{int(round(b * 255)):02X}"


# ---------------------------------------------------------------------------
# Fonctions utilitaires
# ---------------------------------------------------------------------------


def clamp(valeur: float, minimum: float, maximum: float) -> float:
    """Clamp linéaire : ramène *valeur* dans [minimum, maximum]."""
    if valeur < minimum:
        return minimum
    if valeur > maximum:
        return maximum
    return valeur


def poids_recence(age_annees: float) -> float:
    """Décroissance exponentielle : 0.5^(age / demi_vie)."""
    return 0.5 ** (age_annees / DEMI_VIE_ANNEES)


def poids_scrutin(type_scrutin: str, age_annees: float) -> float:
    """Poids effectif d'un scrutin = poids_brut × poids_recence.

    Retourne 0 si le type de scrutin n'est pas dans POIDS_TYPE
    (seconds tours exclus).
    """
    if type_scrutin not in POIDS_TYPE:
        return 0.0
    return POIDS_TYPE[type_scrutin] * poids_recence(age_annees)


# ---------------------------------------------------------------------------
# Fonction principale
# ---------------------------------------------------------------------------


def _dominance(classement: list[tuple[str, float]], algo: str) -> tuple[str, float, float]:
    """Choisit (gagnante, part, marge) dans un classement trié décroissant.

    - complet : pluralité brute sur tout le classement.
    - tendance : divers exclu, parts renormalisées sur le total politique ;
      retombe sur « complet » si aucune famille politique n'a de voix.
    - blocs : familles agrégées par bloc (cf. BLOCS, divers et familles
      inconnues exclus), marge entre blocs renormalisée sur le total
      politique ; la gagnante est la sous-famille dominante du bloc gagnant ;
      même repli que « tendance » si aucun bloc n'a de voix.
    """
    if algo == "tendance":
        politiques = [(f, v) for f, v in classement if f != "divers"]
        total = sum(v for _, v in politiques)
        if total > 0:
            gagnante, part = politiques[0]
            part2 = politiques[1][1] if len(politiques) > 1 else 0.0
            return gagnante, part / total, (part - part2) / total
    elif algo == "blocs":
        politiques = [(f, v) for f, v in classement if f in BLOCS]
        total = sum(v for _, v in politiques)
        if total > 0:
            par_bloc: dict[str, float] = {}
            for f, v in politiques:
                par_bloc[BLOCS[f]] = par_bloc.get(BLOCS[f], 0.0) + v
            blocs = sorted(par_bloc.items(), key=lambda kv: kv[1], reverse=True)
            bloc_gagnant, part_bloc = blocs[0]
            part_bloc2 = blocs[1][1] if len(blocs) > 1 else 0.0
            # Teinte = sous-famille dominante du bloc gagnant (1re du classement)
            gagnante = next(f for f, _ in politiques if BLOCS[f] == bloc_gagnant)
            return gagnante, part_bloc / total, (part_bloc - part_bloc2) / total
    # « complet », ou repli des deux autres algos quand tout est divers.
    (gagnante, part) = classement[0]
    part2 = classement[1][1] if len(classement) > 1 else 0.0
    return gagnante, part, part - part2


def couleur_ville(
    scrutins: list[ResultatScrutin],
    participation_mediane: float,
    algo: str = "complet",
) -> dict:
    """Calcule la couleur politique synthétique d'une ville.

    Paramètres
    ----------
    scrutins : liste de ResultatScrutin (tours 1 uniquement ; les seconds
        tours sont automatiquement exclus car absents de POIDS_TYPE).
    participation_mediane : participation médienne nationale, utilisée
        comme référence pour le facteur de désaturation.
    algo : algo de dominance (cf. ALGOS). Ne change QUE le choix de la
        famille gagnante, la part/marge rapportées (renormalisées pour
        tendance/blocs) et donc la teinte et sa netteté ; la participation
        et la répartition retournée (classement complet, divers inclus —
        transparence) sont identiques pour les trois algos.

    Retourne
    --------
    dict avec les clés :
        - hex : couleur finale au format #RRGGBB
        - algo : algo de dominance utilisé
        - famille_dominante : nom de la famille gagnante
        - part_synthetique : part de la famille dominante (arr. 3 ;
          renormalisée sur les familles politiques pour tendance/blocs)
        - marge : écart avec la 2ᵉ famille ou le 2ᵉ bloc (arr. 3 ; même
          renormalisation)
        - participation : participation synthétique (arr. 3)
        - scrutins_inclus : [(type, poids_relatif), ...]
        - repartition : classement complet [(famille, part), ...]
    """
    if algo not in ALGOS:
        raise ValueError(f"algo inconnu: {algo!r} (attendu: {', '.join(ALGOS)})")
    # 1. Poids de chaque scrutin (liste de tuples car ResultatScrutin
    #    n'est pas hashable — il contient un dict)
    poids = [
        (s, poids_scrutin(s.type_scrutin, s.age_annees))
        for s in scrutins
        if s.type_scrutin in POIDS_TYPE
    ]
    total_poids = sum(p for _, p in poids)

    if total_poids == 0:
        raise ValueError(
            "Aucun scrutin de premier tour fourni (tous les scrutins sont "
            "des seconds tours ou de type inconnu). Impossible de calculer "
            "une couleur politique."
        )

    # 2. Parts synthétiques par famille + participation synthétique
    # familles est construit uniquement à partir des scrutins retenus
    # (ceux dans `poids`), pas tous les scrutins — une famille n'apparaissant
    # qu'en second tour ne doit pas figurer dans la synthèse.
    familles = {f for s, _ in poids for f in s.parts_familles}
    synthese = {
        f: sum(p * s.parts_familles.get(f, 0.0) for s, p in poids) / total_poids
        for f in familles
    }
    participation = sum(p * s.participation for s, p in poids) / total_poids

    # 3. Famille dominante et marge, selon l'algo choisi
    classement = sorted(synthese.items(), key=lambda kv: kv[1], reverse=True)
    gagnante, part, marge = _dominance(classement, algo)

    # 4. Couleur : teinte de la famille dominante,
    #    intensité = netteté du résultat × niveau de participation
    saturation_marge = clamp(0.45 + marge * 1.6, 0.45, 1.0)
    if participation_mediane == 0:
        facteur_participation = 0.55  # plancher : éviter ZeroDivisionError
    else:
        facteur_participation = clamp(participation / participation_mediane, 0.55, 1.0)
    # Fallback : si la famille gagnante n'est pas dans COULEURS, utiliser « divers »
    base = hex_to_oklch(COULEURS.get(gagnante, COULEURS["divers"]))
    couleur = OKLCH(
        L=base.L,
        C=base.C * saturation_marge * facteur_participation,
        H=base.H,
    )

    return {
        "hex": oklch_to_hex(couleur),
        "algo": algo,
        "famille_dominante": gagnante,
        "part_synthetique": round(part, 3),
        "marge": round(marge, 3),
        "participation": round(participation, 3),
        "scrutins_inclus": [
            (s.type_scrutin, round(p / total_poids, 3)) for s, p in poids
        ],
        "repartition": [(f, round(v, 3)) for f, v in classement],
    }
