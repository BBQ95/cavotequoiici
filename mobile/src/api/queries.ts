/** Hooks TanStack Query au-dessus du client API. */
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { api } from "./client";

/** Valeur retardée de `delaiMs` : évite une requête réseau à chaque frappe. */
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
  return useQuery({
    queryKey: ["search", dq],
    queryFn: () => api.search(dq),
    enabled: dq.trim().length >= 2,
    // Garde la liste précédente affichée pendant que la nouvelle requête part.
    placeholderData: (prev) => prev,
  });
}

export function useFiche(insee: string) {
  return useQuery({
    queryKey: ["fiche", insee],
    queryFn: () => api.fiche(insee),
  });
}

export function useScrutins(insee: string) {
  return useQuery({
    queryKey: ["scrutins", insee],
    queryFn: () => api.scrutins(insee),
  });
}

export function useDetailScrutin(insee: string, scrutinId: string | null) {
  return useQuery({
    queryKey: ["detail", insee, scrutinId],
    queryFn: () => api.detailScrutin(insee, scrutinId as string),
    enabled: !!scrutinId,
  });
}
