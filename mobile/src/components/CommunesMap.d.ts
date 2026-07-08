/**
 * Déclaration partagée pour les deux implémentations de plateforme :
 * `CommunesMap.native.tsx` (vraie carte MapLibre) et `CommunesMap.web.tsx`
 * (placeholder). `tsc` résout l'import via ce fichier ; Metro choisit la bonne
 * implémentation selon la plateforme au moment du bundling.
 */
export declare function CommunesMap(props: {
  /** Propriété de tuile à peindre (`hex` ou `hex_<scrutin_id>`) — cf. lib/tiles.ts. */
  couleurProperty?: string;
  /**
   * Centre de carte optionnel `[lon, lat]` (WGS84). Quand il change, la caméra
   * vole vers ce centre ; sinon, la carte reste centrée sur la France.
   */
  center?: [number, number];
  /**
   * Cible de cadrage explicite (sélecteur de territoire) : vole vers `centre`
   * au `zoom` d'ensemble donné. `cle` rejoue le vol à chaque sélection.
   */
  cible?: { centre: [number, number]; zoom: number; cle: number };
}): import("react").JSX.Element;
