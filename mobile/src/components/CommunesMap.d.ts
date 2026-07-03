/**
 * Déclaration partagée pour les deux implémentations de plateforme :
 * `CommunesMap.native.tsx` (vraie carte MapLibre) et `CommunesMap.web.tsx`
 * (placeholder). `tsc` résout l'import via ce fichier ; Metro choisit la bonne
 * implémentation selon la plateforme au moment du bundling.
 */
export declare function CommunesMap(props: {
  /** Propriété de tuile à peindre (`hex` ou `hex_<scrutin_id>`) — cf. lib/tiles.ts. */
  couleurProperty?: string;
}): import("react").JSX.Element;
