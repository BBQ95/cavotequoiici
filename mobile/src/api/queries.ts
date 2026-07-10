/** Hooks TanStack Query au-dessus des artefacts statiques.
 *
 * Une fiche statique porte tout (couleurs des 3 algos + scrutins + détails) :
 * les hooks fiche/scrutins/détail partagent la MÊME entrée de cache
 * (`["fiche-statique", insee]`) et en dérivent leur forme via `select` — une
 * seule requête réseau par commune, et le changement d'algo ne refetch pas.
 */
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { api, versDetailScrutin, versFiche, versScrutins } from "./client";
import { rechercherCommunes } from "../lib/indexCommunes";
import { useAlgo } from "../lib/algo";

/** Valeur retardée de `delaiMs` : évite de balayer l'index à chaque frappe. */
function useDebouncedValue<T>(value: T, delaiMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delaiMs);
    return () => clearTimeout(t);
  }, [value, delaiMs]);
  return debounced;
}

export function useSearch(q: string) {
  const dq = useDebouncedValue(q, 250);
  // L'algo choisi teinte les pastilles des résultats : il fait partie de la clé.
  const { algo } = useAlgo();
  return useQuery({
    queryKey: ["search", dq, algo],
    // Recherche locale sur l'index statique (téléchargé puis caché sur
    // disque) : fonctionne hors ligne après un premier chargement.
    queryFn: () => rechercherCommunes(dq, algo),
    enabled: dq.trim().length >= 2,
    // Garde la liste précédente affichée pendant que la nouvelle recherche part.
    placeholderData: (prev) => prev,
  });
}

function useFicheStatique(insee: string) {
  return useQuery({
    queryKey: ["fiche-statique", insee],
    queryFn: () => api.ficheStatique(insee),
  });
}

export function useFiche(insee: string) {
  const { algo } = useAlgo();
  const query = useFicheStatique(insee);
  return {
    ...query,
    data: query.data ? versFiche(query.data, algo) : undefined,
  };
}

export function useScrutins(insee: string) {
  const query = useFicheStatique(insee);
  return {
    ...query,
    data: query.data ? versScrutins(query.data) : undefined,
  };
}

/** Détail d'un scrutin, lu dans la fiche statique déjà chargée. `data` vaut
 * `null` quand le scrutin n'a pas de détail pour la commune (participation
 * nulle — l'ancien 404 de l'API). */
export function useDetailScrutin(insee: string, scrutinId: string | null) {
  const query = useFicheStatique(insee);
  return {
    ...query,
    data:
      query.data && scrutinId ? versDetailScrutin(query.data, scrutinId) : undefined,
  };
}

export function useNuances() {
  return useQuery({
    queryKey: ["nuances"],
    queryFn: api.nuances,
  });
}
