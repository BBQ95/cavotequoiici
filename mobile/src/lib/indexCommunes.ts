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
import { ALGOS } from "../api/types";
import type { IndexCommunes, VersionDonnees } from "../api/types-statiques";
import {
  indexerEntree,
  communesProches,
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

/** Partagée entre appels concurrents, puis conservée pour la session après
 * succès. Un repli sur le cache permet une nouvelle tentative au prochain appel. */
let chargement: Promise<IndexCharge> | null = null;

/** Le typage de get/JSON.parse ne valide pas les données à l'exécution.
 * Refuser un index inutilisable avant de remplacer un cache encore valide. */
function validerIndex(valeur: unknown): asserts valeur is IndexCommunes {
  const index = valeur as IndexCommunes | null;
  const coordonnee = (v: unknown, max: number) =>
    v === null || (typeof v === "number" && Number.isFinite(v) && Math.abs(v) <= max);
  if (!index ||
      !Array.isArray(index.algos) || index.algos.length !== ALGOS.length ||
      !ALGOS.every((algo) => index.algos.includes(algo)) ||
      !Array.isArray(index.familles) || !index.familles.every((f) => typeof f === "string") ||
      !Array.isArray(index.communes) || !index.communes.every((c) =>
        Array.isArray(c) && c.length === 7 &&
        typeof c[0] === "string" && typeof c[1] === "string" &&
        (c[2] === null || typeof c[2] === "string") &&
        coordonnee(c[3], 90) && coordonnee(c[4], 180) &&
        Array.isArray(c[5]) && c[5].length === index.algos.length &&
        c[5].every((hex) => typeof hex === "string" && /^#[0-9a-f]{6}$/i.test(hex)) &&
        Array.isArray(c[6]) && c[6].length === index.algos.length &&
        c[6].every((f) => f === null ||
          (Number.isInteger(f) && f >= 0 && f < index.familles.length)))) {
    throw new Error("Index de recherche invalide");
  }
}

function deplier(index: IndexCommunes): IndexCharge {
  return {
    algos: index.algos,
    familles: index.familles,
    communes: index.communes.map(indexerEntree),
  };
}

function lireCache(): IndexCharge | null {
  try {
    const fichier = new File(Paths.cache, FICHIER_INDEX);
    if (!fichier.exists) {
      return null;
    }
    const index: unknown = JSON.parse(fichier.textSync());
    validerIndex(index);
    return deplier(index);
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

async function charger(): Promise<{ index: IndexCharge; reessayer: boolean }> {
  let versionDistante: string | null = null;
  try {
    const version = (await get<VersionDonnees>("/meta/version.json")).genere_le;
    if (typeof version === "string" && version.length > 0) {
      versionDistante = version;
    }
  } catch {
    // Hors ligne (ou CDN indisponible) : le cache, s'il existe, fait foi.
  }
  const enCache = lireCache();
  if (versionDistante === null) {
    if (enCache) {
      return { index: enCache, reessayer: true };
    }
    throw new Error("Index de recherche indisponible (hors ligne, sans cache)");
  }
  if (enCache && versionEnCache() === versionDistante) {
    return { index: enCache, reessayer: false };
  }
  try {
    const index = await get<unknown>("/index/communes.json");
    validerIndex(index);
    const charge = deplier(index);
    ecrireCache(index, versionDistante);
    return { index: charge, reessayer: false };
  } catch (err) {
    if (enCache) {
      return { index: enCache, reessayer: true };
    }
    throw err;
  }
}

function obtenirIndex(): Promise<IndexCharge> {
  if (!chargement) {
    chargement = charger().then(({ index, reessayer }) => {
      if (reessayer) chargement = null;
      return index;
    }).catch((err) => {
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

/** Communes à proposer pour confirmation : la proximité des points de
 * l'index ne prouve pas l'appartenance de la position à une commune. */
export async function suggererCommunesProches(
  lat: number,
  lon: number,
): Promise<Pick<CommuneResultat, "code_insee" | "nom" | "departement">[]> {
  const index = await obtenirIndex();
  return communesProches(index.communes, lat, lon).map(
    ({ code_insee, nom, departement }) => ({ code_insee, nom, departement }),
  );
}
