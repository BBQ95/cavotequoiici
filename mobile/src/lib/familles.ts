/** Familles politiques : libellés et couleurs canoniques (cf. pipeline COULEURS). */
export const FAMILLES: Record<string, { label: string; hex: string }> = {
  extreme_gauche: { label: "Extrême gauche", hex: "#D60B0B" },
  gauche: { label: "Gauche", hex: "#E84E6B" },
  ecologistes: { label: "Écologistes", hex: "#46A302" },
  centre: { label: "Centre", hex: "#FFB300" },
  droite: { label: "Droite", hex: "#2D6FCB" },
  extreme_droite: { label: "Extrême droite", hex: "#16243F" },
  divers: { label: "Divers / régionalistes", hex: "#9AA0A6" },
};

export function familleInfo(f: string): { label: string; hex: string } {
  return FAMILLES[f] ?? { label: f, hex: "#9AA0A6" };
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
