/**
 * Agrégation de la répartition des familles en blocs (gauche/centre/droite)
 * pour la fiche commune quand l'algo « blocs » est actif.
 *
 * `BLOCS` est le port TypeScript de `pipeline/couleur.py::BLOCS`, verrouillé
 * par la fixture partagée `tests/fixtures/blocs_parite.json` (test Python +
 * test Node) : toute évolution du mapping casse l'un des deux dépôts.
 *
 * « divers » n'appartient à aucun bloc (il est exclu du calcul de dominance
 * de l'algo) mais reste affiché comme segment à part : la barre totalise
 * toujours 100 % des suffrages exprimés, rien n'est masqué.
 */
import type { FamilleSynthese } from "../api/types";

export const BLOCS: Record<string, "gauche" | "centre" | "droite"> = {
  extreme_gauche: "gauche",
  gauche: "gauche",
  ecologistes: "gauche",
  centre: "centre",
  droite: "droite",
  extreme_droite: "droite",
};

/** Ordre d'émission stable ; `RepartitionBar` retrie par part décroissante. */
const ORDRE = ["gauche", "centre", "droite", "divers"] as const;

/**
 * Somme les parts de `repartition` par bloc. Les ids émis (`gauche`, `centre`,
 * `droite`, `divers`) coïncident avec des ids de familles : libellés et teintes
 * de `lib/familles.ts` réutilisés tels quels par `RepartitionBar` (choix
 * assumé : couleur du bloc = couleur de la famille homonyme). Une famille
 * inconnue du mapping rejoint « divers » (défensif).
 */
export function agregerParBlocs(
  repartition: FamilleSynthese[],
): { famille: string; part: number }[] {
  const parts = new Map<string, number>();
  for (const { famille, part } of repartition) {
    const bloc = BLOCS[famille] ?? "divers";
    parts.set(bloc, (parts.get(bloc) ?? 0) + part);
  }
  return ORDRE.filter((bloc) => parts.has(bloc)).map((bloc) => ({
    famille: bloc,
    part: parts.get(bloc)!,
  }));
}
