/**
 * Configuration des tuiles vectorielles des communes (Étape 6 — carte).
 *
 * Les tuiles sont servies en XYZ/MVT (source-layer `communes`, z4→z11) par un
 * serveur qui traduit `tiles/communes.pmtiles` en `{z}/{x}/{y}.mvt`. Chaque
 * feature porte : `insee`, `nom`, `hex` (sRGB, OKLCH de synthèse déjà désaturé
 * par la participation — même couleur que la fiche), `famille`, `participation`.
 *
 * En prod : pointer `EXPO_PUBLIC_TILES_URL` vers un CDN servant le même schéma.
 * Défaut : le serveur de dev exposé via Tailscale Funnel.
 */
const TILES_BASE =
  process.env.EXPO_PUBLIC_TILES_URL?.replace(/\/$/, "") ??
  "https://hermes-vps.tail5957ae.ts.net/tiles";

/** Templates de tuiles vectorielles (MVT) pour la `VectorSource` MapLibre. */
export const TUILES_COMMUNES = [`${TILES_BASE}/communes/{z}/{x}/{y}.mvt`];

/** Nom de la couche interne aux tuiles (fixé par le pipeline tippecanoe). */
export const SOURCE_LAYER_COMMUNES = "communes";

/** Bornes de zoom des tuiles (cf. `pipeline/export_tiles.py`). */
export const TUILES_MINZOOM = 4;
export const TUILES_MAXZOOM = 11;
