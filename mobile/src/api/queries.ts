/** Hooks TanStack Query au-dessus du client API. */
import { useQuery } from "@tanstack/react-query";

import { api } from "./client";

export function useSearch(q: string) {
  return useQuery({
    queryKey: ["search", q],
    queryFn: () => api.search(q),
    enabled: q.trim().length >= 2,
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
