/**
 * Formes des artefacts statiques servis par data.cavotequoiici.fr
 * (pipeline/export_communes.py), composées des types de base de `types.ts`
 * (miroir manuel de `pipeline/schemas`) : toute dérive répercutée dans
 * types.ts casse le typecheck ici aussi.
 */
import type {
  Algo,
  CommuneFiche,
  CouleurSynthese,
  DetailScrutinResponse,
  ScrutinInclus,
} from "./client";

/** Entrée `scrutins` d'une fiche : liste + détail fusionnés par l'export.
 * `detail` est nul quand le scrutin n'a pas de couleur pour la commune
 * (participation nulle — le 404 maîtrisé de l'ancienne API). */
export type ScrutinStatique = ScrutinInclus & {
  detail: DetailScrutinResponse | null;
};

/** communes/{insee}.json : la fiche API, avec une couleur PAR algo (le client
 * choisit la clé là où l'API servait `?algo=`) et les scrutins embarqués. */
export type FicheStatique = Omit<CommuneFiche, "couleur"> & {
  couleurs: Record<Algo, CouleurSynthese>;
  scrutins: ScrutinStatique[];
};

/**
 * index/communes.json — index compact de recherche/géolocalisation :
 * [insee, nom, departement, lat, lon, [hex par algo], [famille indexée par algo]].
 * L'ordre des listes hex/famille suit `algos` ; les indices de famille
 * pointent dans la légende `familles` (null = pas de famille dominante).
 */
export type EntreeIndex = [
  string,
  string,
  string | null,
  number | null,
  number | null,
  string[],
  (number | null)[],
];

export type IndexCommunes = {
  algos: Algo[];
  familles: string[];
  communes: EntreeIndex[];
};

/** meta/version.json : identité du jeu de données publié (cache-busting). */
export type VersionDonnees = {
  schema: number;
  genere_le: string;
  nb_communes: number;
  algos: Algo[];
  scrutins: string[];
  nb_index: number;
};
