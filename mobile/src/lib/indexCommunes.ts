/**
 * Chargement (et cache disque) de l'index statique de recherche
 * (`index/communes.json`, ~3 Mo brut) et façade au-dessus de la logique pure
 * de `recherche.ts`.
 *
 * Stratégie : `meta/version.json` (petit) donne l'horodatage du jeu de
 * données ; l'index n'est retéléchargé que s'il a changé, sinon il est relu
 * depuis le cache disque (expo-file-system — AsyncStorage plafonne à ~2 Mo
 * par entrée sur Android). Hors ligne, le cache sert tel quel : recherche et
 * géolocalisation marchent en avion après un premier lancement.
 */
import { File, Paths } from "expo-file-system";

import { get, type Algo, type CommuneResultat } from "../api/client";
import type { IndexCommunes, VersionDonnees } from "../api/types-statiques";
import {
  indexerEntree,
  plusProche,
  rechercher,
  type CommuneIndexee,
} from "./recherche";

const FICHIER_INDEX = "index-communes.json";
const FICHIER_VERSION = "index-communes.version.txt";

type IndexCharge = {
  algos: Algo[];
  familles: string[];
  communes: CommuneIndexee[];
};

/** Promesse memoïsée : un seul chargement par vie de l'app (l'index est
 * immuable entre deux releases de données). */
let chargement: Promise<IndexCharge> | null = null;

function deplier(index: IndexCommunes): IndexCharge {
  return {
    algos: index.algos,
    familles: index.familles,
    communes: index.communes.map(indexerEntree),
  };
}

function lireCache(): IndexCommunes | null {
  try {
    const fichier = new File(Paths.cache, FICHIER_INDEX);
    if (!fichier.exists) {
      return null;
    }
    return JSON.parse(fichier.textSync()) as IndexCommunes;
  } catch {
    return null; // cache corrompu → on retéléchargera
  }
}

function ecrireCache(index: IndexCommunes, version: string): void {
  try {
    new File(Paths.cache, FICHIER_INDEX).write(JSON.stringify(index));
    new File(Paths.cache, FICHIER_VERSION).write(version);
  } catch {
    // Cache best-effort : sans disque, l'index reste en mémoire pour la session.
  }
}

function versionEnCache(): string | null {
  try {
    const fichier = new File(Paths.cache, FICHIER_VERSION);
    return fichier.exists ? fichier.textSync() : null;
  } catch {
    return null;
  }
}

async function charger(): Promise<IndexCharge> {
  let versionDistante: string | null = null;
  try {
    versionDistante = (await get<VersionDonnees>("/meta/version.json")).genere_le;
  } catch {
    // Hors ligne (ou CDN indisponible) : le cache, s'il existe, fait foi.
  }
  const enCache = lireCache();
  if (enCache && (versionDistante === null || versionEnCache() === versionDistante)) {
    return deplier(enCache);
  }
  if (versionDistante === null && !enCache) {
    throw new Error("Index de recherche indisponible (hors ligne, sans cache)");
  }
  const index = await get<IndexCommunes>("/index/communes.json");
  ecrireCache(index, versionDistante ?? "");
  return deplier(index);
}

function obtenirIndex(): Promise<IndexCharge> {
  if (!chargement) {
    chargement = charger().catch((err) => {
      chargement = null; // un échec ne doit pas condamner la session
      throw err;
    });
  }
  return chargement;
}

/** Recherche par nom sur l'index, pastilles selon l'algo choisi — l'équivalent
 * local de `GET /communes/search?q=…&algo=…`. */
export async function rechercherCommunes(
  q: string,
  algo: Algo,
  limite = 10,
): Promise<CommuneResultat[]> {
  const index = await obtenirIndex();
  const iAlgo = index.algos.indexOf(algo);
  return rechercher(index.communes, index.familles, q, iAlgo, limite);
}

/** Commune la plus proche à moins de `rayonM` mètres, ou null — l'équivalent
 * local de `GET /communes/proximite` (premier résultat). */
export async function communeLaPlusProche(
  lat: number,
  lon: number,
  rayonM: number,
): Promise<{ code_insee: string; nom: string } | null> {
  const index = await obtenirIndex();
  const commune = plusProche(index.communes, lat, lon, rayonM);
  return commune ? { code_insee: commune.code_insee, nom: commune.nom } : null;
}
