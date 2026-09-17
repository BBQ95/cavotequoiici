/** Révision de présentation des données ; alignée sur le pipeline par fixture. */
export const VERSION_PALETTE_BLOCS = 2;

/** Invalide les anciennes réponses HTTP, y compris l'archive PMTiles native. */
export function versionnerDonnees(url: string): string {
  return `${url}${url.includes("?") ? "&" : "?"}palette_blocs=${VERSION_PALETTE_BLOCS}`;
}
