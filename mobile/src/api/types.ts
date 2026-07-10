/**
 * Types manuels des données de CaVoteQuoiIci — miroir des schémas Pydantic du
 * backend (`pipeline/schemas/*.py`) et de `pipeline/couleur.py::ALGOS`.
 *
 * Historiquement générés depuis l'OpenAPI de l'API FastAPI (retirée — l'app
 * est 100 % statique) : ils sont désormais tenus à jour À LA MAIN, réduits
 * aux schémas réellement consommés, avec la même nullabilité que la
 * génération d'origine (champs optionnels ET nullables côté Pydantic).
 * Toute évolution de forme côté pipeline doit être répercutée ici (et dans
 * `types-statiques.ts` pour les artefacts composés).
 */

/** Algo de dominance (pipeline/couleur.py::ALGOS). En statique, l'algo
 * sélectionne la clé `couleurs[algo]` de la fiche (plus de `?algo=`). */
export type Algo = "complet" | "tendance" | "blocs";

/** Part synthétique (pondérée) d'une famille politique dans la couleur de la ville. */
export type FamilleSynthese = {
  famille: string;
  part: number;
};

/**
 * Couleur politique synthétique d'une commune.
 *
 * `algo` = algo de dominance servi ; `famille_dominante` en dépend — pour
 * « tendance »/« blocs » elle peut différer de la première entrée de
 * `repartition` (qui reste le classement complet, divers inclus, identique
 * pour tous les algos).
 */
export type CouleurSynthese = {
  code_insee: string;
  l: number;
  c: number;
  h: number;
  hex: string;
  algo: string;
  famille_dominante?: string | null;
  participation_mediane: number;
  scrutins_inclus: [string, number][];
  repartition: FamilleSynthese[];
};

/** Élément d'autocomplétion / de recherche. `hex` et `famille` sont nuls
 * pour une commune sans couleur calculée. */
export type CommuneResultat = {
  code_insee: string;
  nom: string;
  departement?: string | null;
  hex?: string | null;
  famille?: string | null;
};

/** Fiche complète : métadonnées + couleur synthétique. */
export type CommuneFiche = {
  code_insee: string;
  nom: string;
  departement?: string | null;
  region?: string | null;
  population?: number | null;
  couleur: CouleurSynthese;
  lat?: number | null;
  lon?: number | null;
};

/** Un scrutin inclus dans la synthèse de la commune. */
export type ScrutinInclus = {
  scrutin_id: string;
  type: string;
  date: string;
  poids_relatif: number;
};

/** Liste des scrutins d'une commune (reconstituée depuis la fiche statique). */
export type ListeScrutinsResponse = {
  insee: string;
  scrutins: ScrutinInclus[];
};

/** Voix d'une famille politique pour un scrutin. */
export type FamilleVoix = {
  famille: string;
  voix: number;
  pourcentage: number;
};

/** Couleur OKLCH d'un scrutin pour une commune. */
export type CouleurScrutin = {
  l: number;
  c: number;
  h: number;
};

/** Détail d'un scrutin pour une commune (embarqué dans la fiche statique). */
export type DetailScrutinResponse = {
  insee: string;
  scrutin_id: string;
  familles: FamilleVoix[];
  participation: number;
  couleur: CouleurScrutin;
};

/** Classement officiel d'une nuance (code parti/liste) dans une famille. */
export type NuanceClassee = {
  nuance: string;
  famille: string;
  source: string;
  statut?: string | null;
};

/** Grille de nuances d'un scrutin (une ligne par nuance, ordre du CSV). */
export type ScrutinNuances = {
  scrutin_id: string;
  type: string;
  annee: number;
  date_classification: string;
  nuances: NuanceClassee[];
};

/** nuances.json : grilles triées par année décroissante. */
export type NuancesResponse = {
  scrutins: ScrutinNuances[];
};
