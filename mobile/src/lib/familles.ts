/**
 * Familles politiques : libellés et couleurs d'affichage (barres, points, légendes,
 * pastilles). Source UNIQUE de vérité côté app (cf. maquettes « Palette des familles »).
 *
 * NB : ces teintes servent à l'affichage des répartitions. La couleur du hero d'une
 * commune vient de l'API (`couleur.hex`, OKLCH désaturé par la participation) — elle
 * encode la pâleur liée à l'abstention et peut donc différer légèrement de la teinte
 * de famille brute ci-dessous. C'est voulu (principe produit « participation = couleur »).
 */
export const FAMILLES: Record<string, { label: string; hex: string }> = {
  extreme_gauche: { label: "Extrême gauche", hex: "#d6313b" },
  gauche: { label: "Gauche", hex: "#f06398" },
  ecologistes: { label: "Écologistes", hex: "#4cc23f" },
  centre: { label: "Centre", hex: "#f7b32b" },
  droite: { label: "Droite", hex: "#3d8bd6" },
  extreme_droite: { label: "Extrême droite", hex: "#2a3a5c" },
  divers: { label: "Divers / régionalistes", hex: "#9aa0a6" },
};

export function familleInfo(f: string): { label: string; hex: string } {
  return FAMILLES[f] ?? { label: f, hex: "#9aa0a6" };
}

const LIBELLES_SCRUTIN: Record<string, string> = {
  pres_t1: "Présidentielle (1er tour)",
  leg_t1: "Législatives (1er tour)",
  euro: "Européennes",
  reg_t1: "Régionales (1er tour)",
  dep_t1: "Départementales (1er tour)",
  mun_t1: "Municipales (1er tour)",
};

export function libelleScrutin(type: string): string {
  return LIBELLES_SCRUTIN[type] ?? type;
}
