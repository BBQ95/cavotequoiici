/**
 * Client des artefacts statiques de CaVoteQuoiIci (data.cavotequoiici.fr).
 *
 * Depuis la bascule statique, l'app ne parle plus à l'API FastAPI : les fiches
 * (avec scrutins embarqués), les nuances, les glyphes de carte et l'index de
 * recherche sont des fichiers publiés sur le CDN par le pipeline
 * (`pipeline/export_communes.py`). Les types de retour restent ceux de
 * l'OpenAPI (src/api/types.ts) : les écrans n'ont pas changé, seuls les
 * chemins et le découpage des fichiers diffèrent.
 */
import type { components, operations } from "./types";
import type { FicheStatique } from "./types-statiques";

type Schemas = components["schemas"];

/**
 * Algo de dominance, dérivé du schéma OpenAPI : si le backend ajoute ou
 * renomme un algo, `make types` fait échouer tsc ici. En statique, l'algo
 * sélectionne la clé `couleurs[algo]` de la fiche (plus de `?algo=`).
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
export type ListeScrutinsResponse = Schemas["ListeScrutinsResponse"];
export type ScrutinInclus = Schemas["ScrutinInclus"];
export type DetailScrutinResponse = Schemas["DetailScrutinResponse"];
export type FamilleVoix = Schemas["FamilleVoix"];
export type NuancesResponse = Schemas["NuancesResponse"];
export type ScrutinNuances = Schemas["ScrutinNuances"];
export type NuanceClassee = Schemas["NuanceClassee"];

/**
 * `EXPO_PUBLIC_DATA_URL` **doit** être définie (variable inlinée au build —
 * voir `mobile/.env.example`, chargé nativement par Expo). Sans elle, la base
 * reste vide et chaque requête échoue avec un message explicite. En pratique :
 * `https://data.cavotequoiici.fr` (les données sont publiques, le CDN sert
 * aussi le développement local).
 */
const BASE_URL = process.env.EXPO_PUBLIC_DATA_URL?.replace(/\/$/, "") ?? "";

/**
 * Base des données statiques, exposée pour la carte : le style MapLibre
 * construit son endpoint de glyphes (`/fonts/{fontstack}/{range}.pbf`) et sa
 * source de tuiles dessus. Vide si `EXPO_PUBLIC_DATA_URL` n'est pas définie
 * (la carte omet alors les étiquettes).
 */
export const DATA_BASE = BASE_URL;

if (__DEV__ && !BASE_URL) {
  console.warn(
    "EXPO_PUBLIC_DATA_URL non définie : copier mobile/.env.example vers mobile/.env " +
      "(voir mobile/README.md).",
  );
}

export async function get<T>(path: string): Promise<T> {
  if (!BASE_URL) {
    throw new ApiError("Données non configurées (EXPO_PUBLIC_DATA_URL manquante)", 0);
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

/** Fiche API historique reconstituée depuis la fiche statique : la couleur
 * de l'algo choisi remonte en `couleur`, comme la servait `?algo=`. */
export function versFiche(fiche: FicheStatique, algo: Algo): CommuneFiche {
  const { couleurs, scrutins: _scrutins, ...meta } = fiche;
  return { ...meta, couleur: couleurs[algo] };
}

/** Réponse « liste des scrutins » reconstituée (sans les détails embarqués). */
export function versScrutins(fiche: FicheStatique): ListeScrutinsResponse {
  return {
    insee: fiche.code_insee,
    scrutins: fiche.scrutins.map(({ detail: _detail, ...scrutin }) => scrutin),
  };
}

/** Détail d'un scrutin depuis la fiche statique ; null si le scrutin n'a pas
 * de couleur pour la commune (l'ancien 404 maîtrisé de l'API). */
export function versDetailScrutin(
  fiche: FicheStatique,
  scrutinId: string,
): DetailScrutinResponse | null {
  return fiche.scrutins.find((s) => s.scrutin_id === scrutinId)?.detail ?? null;
}

export const api = {
  /** Fiche statique brute : une requête par commune, tout embarqué (couleurs
   * des 3 algos + scrutins). Les hooks en dérivent fiche/scrutins/détail. */
  ficheStatique: (insee: string) =>
    get<FicheStatique>(`/communes/${insee}.json`),
  nuances: () => get<NuancesResponse>("/nuances.json"),
};
