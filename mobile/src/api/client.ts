/**
 * Client de l'API CaVoteQuoiIci (lecture seule).
 * Types dérivés du schéma OpenAPI (src/api/types.ts).
 */
import type { components, operations } from "./types";

type Schemas = components["schemas"];

/**
 * Algo de dominance accepté par l'API (`?algo=`), dérivé du schéma OpenAPI :
 * si le backend ajoute ou renomme un algo, `make types` fait échouer tsc ici.
 */
export type Algo = NonNullable<
  NonNullable<
    operations["couleur_communes__insee__couleur_get"]["parameters"]["query"]
  >["algo"]
>;
export type CommuneResultat = Schemas["CommuneResultat"];
export type CouleurSynthese = Schemas["CouleurSynthese"];
export type CommuneFiche = Schemas["CommuneFiche"];
export type FamilleSynthese = Schemas["FamilleSynthese"];
export type CommuneProximite = Schemas["CommuneProximite"];
export type ListeScrutinsResponse = Schemas["ListeScrutinsResponse"];
export type ScrutinInclus = Schemas["ScrutinInclus"];
export type DetailScrutinResponse = Schemas["DetailScrutinResponse"];
export type FamilleVoix = Schemas["FamilleVoix"];

/**
 * `EXPO_PUBLIC_API_URL` **doit** être définie (variable inlinée au build — voir
 * `mobile/.env.example`, chargé nativement par Expo). Sans elle, la base reste
 * vide et chaque requête échoue avec un message explicite : mieux qu'un fallback
 * codé en dur qui ferait développer tout le monde contre l'infra d'un mainteneur.
 * Même pattern que `src/lib/tiles.ts`.
 */
const BASE_URL = process.env.EXPO_PUBLIC_API_URL?.replace(/\/$/, "") ?? "";

/**
 * Base de l'API, exposée pour la carte : le style MapLibre construit son
 * endpoint de glyphes (`/fonts/{fontstack}/{range}.pbf`) dessus. Vide si
 * `EXPO_PUBLIC_API_URL` n'est pas définie (la carte omet alors les étiquettes).
 */
export const API_BASE = BASE_URL;

if (__DEV__ && !BASE_URL) {
  console.warn(
    "EXPO_PUBLIC_API_URL non définie : copier mobile/.env.example vers mobile/.env " +
      "avec l'IP LAN du backend (voir mobile/README.md).",
  );
}

async function get<T>(path: string): Promise<T> {
  if (!BASE_URL) {
    throw new ApiError("API non configurée (EXPO_PUBLIC_API_URL manquante)", 0);
  }
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
  search: (q: string, algo: Algo) =>
    get<CommuneResultat[]>(
      `/communes/search?q=${encodeURIComponent(q)}&algo=${algo}`,
    ),
  fiche: (insee: string, algo: Algo) =>
    get<CommuneFiche>(`/communes/${insee}?algo=${algo}`),
  couleur: (insee: string, algo: Algo) =>
    get<CouleurSynthese>(`/communes/${insee}/couleur?algo=${algo}`),
  scrutins: (insee: string) =>
    get<ListeScrutinsResponse>(`/communes/${insee}/scrutins`),
  detailScrutin: (insee: string, scrutinId: string) =>
    get<DetailScrutinResponse>(`/communes/${insee}/scrutins/${scrutinId}`),
  proximite: (lat: number, lon: number, rayonM = 10000) =>
    get<CommuneProximite[]>(
      `/communes/proximite?lat=${lat}&lon=${lon}&rayon_m=${rayonM}`,
    ),
};
