/**
 * Recherche de communes et géolocalisation LOCALES, sur l'index statique
 * (`index/communes.json`) — remplace `GET /communes/search` et
 * `/communes/proximite` depuis la bascule statique.
 *
 * Ce module est PUR (aucun import Expo/React Native) : il est testé sous Node
 * (`npm test`) contre les fixtures de parité générées par le backend
 * (`tests/fixtures/normalisation_parite.json`). Le chargement et le cache de
 * l'index vivent dans `indexCommunes.ts`.
 */
import type { CommuneResultat } from "../api/client";
import type { EntreeIndex } from "../api/types-statiques";

/** Entrée d'index prête à chercher : nom normalisé précalculé au chargement. */
export type CommuneIndexee = {
  code_insee: string;
  nom: string;
  nomRecherche: string;
  departement: string | null;
  lat: number | null;
  lon: number | null;
  /** hex et indice de famille par algo, dans l'ordre de `index.algos`. */
  hexes: string[];
  familles: (number | null)[];
};

/**
 * Port TypeScript de `pipeline/normalisation.normaliser_nom` — TOUTE évolution
 * doit rester en parité (fixtures `tests/fixtures/normalisation_parite.json`,
 * gardées à jour par un test Python côté backend) : minuscules, ligatures
 * œ/æ dépliées, séparateurs (tiret, apostrophes droite et typographique)
 * ramenés à l'espace, accents supprimés (NFD sans diacritiques — les
 * combinants des noms français vivent tous dans U+0300–U+036F), espaces réduits.
 */
export function normaliserNom(nom: string): string {
  let s = nom.toLowerCase();
  s = s.replace(/œ/g, "oe").replace(/æ/g, "ae");
  s = s.replace(/[-'’]/g, " ");
  s = s.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  return s.split(/\s+/).filter(Boolean).join(" ");
}

/** Déplie une entrée compacte de l'index en entrée cherchable. */
export function indexerEntree(entree: EntreeIndex): CommuneIndexee {
  const [code_insee, nom, departement, lat, lon, hexes, familles] = entree;
  return {
    code_insee,
    nom,
    nomRecherche: normaliserNom(nom),
    departement,
    lat,
    lon,
    hexes,
    familles,
  };
}

/**
 * Ordre d'affichage : nom normalisé (comparaison binaire — équivaut à l'ordre
 * français puisque accents/casse/séparateurs sont déjà neutralisés), tiebreak
 * sur le nom brut. ⚠️ Pas de `localeCompare` ici : sur Hermes (Android),
 * chaque appel Intl traverse JNI vers java.text.Collator — des SECONDES de
 * tri par frappe sur une requête courte (constaté en QA le 10/07).
 */
function comparerCommunes(a: CommuneIndexee, b: CommuneIndexee): number {
  if (a.nomRecherche !== b.nomRecherche) {
    return a.nomRecherche < b.nomRecherche ? -1 : 1;
  }
  return a.nom < b.nom ? -1 : a.nom > b.nom ? 1 : 0;
}

/** Insère `c` à sa place dans `top` (trié), borné à `k` éléments — sélection
 * des k plus petits en un passage, sans trier les milliers de matchs. */
function insererTop(top: CommuneIndexee[], c: CommuneIndexee, k: number): void {
  if (top.length === k && comparerCommunes(c, top[k - 1]) >= 0) {
    return;
  }
  let i = top.length;
  while (i > 0 && comparerCommunes(c, top[i - 1]) < 0) {
    i--;
  }
  top.splice(i, 0, c);
  if (top.length > k) {
    top.pop();
  }
}

/**
 * Recherche par nom — mêmes règles que l'endpoint `/communes/search` : match
 * en préfixe ou en milieu de nom sur le nom normalisé, préfixes d'abord,
 * puis ordre alphabétique. `iAlgo` (indice dans `index.algos`) sélectionne la
 * pastille (hex + famille) comme le faisait `?algo=`.
 *
 * Cette fonction tourne à CHAQUE frappe (débouncée) sur le thread JS : le
 * balayage des 35 000 entrées reste linéaire et la sélection est bornée à
 * `limite` — aucun tri global, aucun appel Intl (cf. `comparerCommunes`).
 */
export function rechercher(
  communes: readonly CommuneIndexee[],
  legendeFamilles: readonly string[],
  q: string,
  iAlgo: number,
  limite = 10,
): CommuneResultat[] {
  const qn = normaliserNom(q);
  if (!qn) {
    return [];
  }
  // Deux top-k séparés : le classement global met TOUS les préfixes avant
  // les infixes (comme l'API) — un simple compteur ne suffirait pas.
  const prefixes: CommuneIndexee[] = [];
  const infixes: CommuneIndexee[] = [];
  for (const c of communes) {
    if (c.nomRecherche.startsWith(qn)) {
      insererTop(prefixes, c, limite);
    } else if (c.nomRecherche.includes(qn)) {
      insererTop(infixes, c, limite);
    }
  }
  return [...prefixes, ...infixes].slice(0, limite).map((c) => {
    const iFamille = c.familles[iAlgo];
    return {
      code_insee: c.code_insee,
      nom: c.nom,
      departement: c.departement,
      hex: c.hexes[iAlgo] ?? null,
      famille: iFamille === null ? null : (legendeFamilles[iFamille] ?? null),
    };
  });
}

/** Rayon terrestre moyen (m) — même échelle que ST_Distance en geography. */
const RAYON_TERRE_M = 6_371_000;

/** Distance haversine en mètres entre deux points WGS84. */
export function distanceM(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number,
): number {
  const rad = Math.PI / 180;
  const dLat = (lat2 - lat1) * rad;
  const dLon = (lon2 - lon1) * rad;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1 * rad) * Math.cos(lat2 * rad) * Math.sin(dLon / 2) ** 2;
  return 2 * RAYON_TERRE_M * Math.asin(Math.sqrt(a));
}

/**
 * Commune (avec coordonnées) la plus proche du point, à moins de `rayonM`
 * mètres — remplace `/communes/proximite` (dont l'app ne consommait que le
 * premier résultat). Le point représentatif de l'index (ST_PointOnSurface)
 * approxime la géométrie : suffisant pour « quelle commune sous mes pieds ? ».
 */
export function plusProche(
  communes: readonly CommuneIndexee[],
  lat: number,
  lon: number,
  rayonM: number,
): CommuneIndexee | null {
  let meilleure: CommuneIndexee | null = null;
  let meilleureDistance = Infinity;
  for (const c of communes) {
    if (c.lat === null || c.lon === null) {
      continue;
    }
    const d = distanceM(lat, lon, c.lat, c.lon);
    if (d < meilleureDistance) {
      meilleureDistance = d;
      meilleure = c;
    }
  }
  return meilleureDistance <= rayonM ? meilleure : null;
}
