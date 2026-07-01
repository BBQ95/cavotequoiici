/**
 * Déclaration partagée pour les deux implémentations de plateforme :
 * `CommunesMap.native.tsx` (vraie carte MapLibre) et `CommunesMap.web.tsx`
 * (placeholder). `tsc` résout l'import via ce fichier ; Metro choisit la bonne
 * implémentation selon la plateforme au moment du bundling.
 */
export declare function CommunesMap(): import("react").JSX.Element;
