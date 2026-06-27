/**
 * Client de l'API CaVoteQuoiIci (lecture seule).
 * Types dérivés du schéma OpenAPI (src/api/types.ts).
 */
import type { components } from "./types";

type Schemas = components["schemas"];
export type CommuneResultat = Schemas["CommuneResultat"];
export type CouleurSynthese = Schemas["CouleurSynthese"];
export type CommuneFiche = Schemas["CommuneFiche"];
export type FamilleSynthese = Schemas["FamilleSynthese"];
export type CommuneProximite = Schemas["CommuneProximite"];
export type ListeScrutinsResponse = Schemas["ListeScrutinsResponse"];
export type ScrutinInclus = Schemas["ScrutinInclus"];
export type DetailScrutinResponse = Schemas["DetailScrutinResponse"];
export type FamilleVoix = Schemas["FamilleVoix"];

const BASE_URL =
  process.env.EXPO_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://localhost:8200";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`);
  if (res.status === 404) {
    throw new ApiError("Commune introuvable", 404);
  }
  if (!res.ok) {
    throw new ApiError(`Erreur serveur (${res.status})`, res.status);
  }
  return (await res.json()) as T;
}

export class ApiError extends Error {
  constructor(message: string, public readonly status: number) {
    super(message);
    this.name = "ApiError";
  }
}

export const api = {
  search: (q: string) =>
    get<CommuneResultat[]>(`/communes/search?q=${encodeURIComponent(q)}`),
  fiche: (insee: string) => get<CommuneFiche>(`/communes/${insee}`),
  couleur: (insee: string) => get<CouleurSynthese>(`/communes/${insee}/couleur`),
  scrutins: (insee: string) =>
    get<ListeScrutinsResponse>(`/communes/${insee}/scrutins`),
  detailScrutin: (insee: string, scrutinId: string) =>
    get<DetailScrutinResponse>(`/communes/${insee}/scrutins/${scrutinId}`),
  proximite: (lat: number, lon: number, rayonM = 10000) =>
    get<CommuneProximite[]>(
      `/communes/proximite?lat=${lat}&lon=${lon}&rayon_m=${rayonM}`,
    ),
};
