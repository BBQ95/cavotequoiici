/**
 * Configuration des tuiles vectorielles des communes (Étape 6 — carte).
 *
 * Les tuiles sont servies en XYZ/MVT (source-layer `communes`, z4→z11) par un
 * serveur qui traduit `tiles/communes.pmtiles` en `{z}/{x}/{y}.mvt`. Chaque
 * feature porte : `insee`, `nom`, `hex` (sRGB, OKLCH de synthèse déjà désaturé
 * par la participation — même couleur que la fiche), `famille`, `participation`.
 *
 * `EXPO_PUBLIC_TILES_URL` **doit** être définie (variable inlinée au build — voir
 * `mobile/.env.example`, chargé nativement par Expo ; en dev local :
 * `make tiles-serve`). Sans elle, la base reste vide (carte sans tuiles = échec
 * visible) plutôt qu'un fallback codé en dur vers l'infra d'un mainteneur.
 */
const TILES_BASE = process.env.EXPO_PUBLIC_TILES_URL?.replace(/\/$/, "") ?? "";

if (__DEV__ && !TILES_BASE) {
  console.warn(
    "EXPO_PUBLIC_TILES_URL non définie : la carte restera vide " +
      "(copier mobile/.env.example vers mobile/.env avec l'IP LAN du backend).",
  );
}

/** Templates de tuiles vectorielles (MVT) pour la `VectorSource` MapLibre. */
export const TUILES_COMMUNES = [`${TILES_BASE}/communes/{z}/{x}/{y}.mvt`];

/**
 * Couches de couleur sélectionnables sur la carte (carte v2). Chaque entrée
 * pointe la propriété de tuile à peindre : `hex` (synthèse) ou
 * `hex_<scrutin_id>` (couleur du scrutin, précalculée par le pipeline —
 * cf. `pipeline/export_tiles.py`). Une commune sans résultat pour un scrutin
 * n'a pas la propriété : la carte retombe sur une teinte neutre (`coalesce`).
 * Ordre d'affichage : synthèse d'abord, puis du plus récent au plus ancien.
 */
export type CoucheCouleur = {
  /** Identifiant stable (scrutin_id du pipeline, ou "synthese"). */
  id: string;
  /** Libellé court du sélecteur. */
  label: string;
  /** Propriété de tuile portant le hex à peindre. */
  property: string;
};

export const COUCHES_COULEUR: readonly CoucheCouleur[] = [
  { id: "synthese", label: "Synthèse", property: "hex" },
  { id: "municipales_2026_t1", label: "Municipales 2026", property: "hex_municipales_2026_t1" },
  { id: "europeennes_2024", label: "Européennes 2024", property: "hex_europeennes_2024" },
  { id: "legislatives_2024_t1", label: "Législatives 2024", property: "hex_legislatives_2024_t1" },
  { id: "presidentielle_2022_t1", label: "Présidentielle 2022", property: "hex_presidentielle_2022_t1" },
] as const;

/** Nom de la couche interne aux tuiles (fixé par le pipeline tippecanoe). */
export const SOURCE_LAYER_COMMUNES = "communes";

/** Bornes de zoom des tuiles (cf. `pipeline/export_tiles.py`). */
export const TUILES_MINZOOM = 4;
export const TUILES_MAXZOOM = 11;
