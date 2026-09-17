/**
 * Déclaration partagée pour les deux implémentations de plateforme :
 * `CommunesMap.native.tsx` (vraie carte MapLibre) et `CommunesMap.web.tsx`
 * (placeholder). `tsc` résout l'import via ce fichier ; Metro choisit la bonne
 * implémentation selon la plateforme au moment du bundling.
 */
export type CommunesMapProps = {
  /** Propriété de tuile à peindre (`hex` ou `hex_<scrutin_id>`). */
  couleurProperty?: string;
  /** Commande explicite ; chaque sélection possède une nouvelle clé de session. */
  cible?: import("../lib/cadrage").CibleCadrage;
};
export declare function CommunesMap(props: CommunesMapProps): import("react").JSX.Element;
