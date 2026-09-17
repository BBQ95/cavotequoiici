/** Mémoire de session : survit au démontage des écrans, pas à l'arrêt de l'app. */
export const ZOOM_COMMUNE = 11;

export type Cadrage = {
  center: [number, number];
  zoom: number;
  bearing: number;
  pitch: number;
};
export type CibleCadrage = { centre: [number, number]; zoom: number; cle: number };

export const sessionCarte = {
  cadrage: undefined as Cadrage | undefined,
  cible: undefined as CibleCadrage | undefined,
  cleAppliquee: 0,
  historiqueLu: false,
};

export function demanderCadrage(centre: [number, number], zoom: number): CibleCadrage {
  const cible = { centre, zoom, cle: (sessionCarte.cible?.cle ?? 0) + 1 };
  sessionCarte.cible = cible;
  return cible;
}

export function memoriserCadrage({ center, zoom, bearing, pitch }:
  Pick<Cadrage, "center" | "zoom"> & Partial<Pick<Cadrage, "bearing" | "pitch">>,
): void {
  // Android peut aussi émettre un objet vide avant qu'une cible soit disponible.
  if (!Array.isArray(center) || center.length !== 2 ||
      ![...center, zoom].every(Number.isFinite)) return;
  // MapLibre 11 fournit ces deux champs sur Android/iOS. Un événement partiel
  // ou invalide doit néanmoins conserver le panoramique et le zoom reçus.
  const precedent = sessionCarte.cadrage;
  sessionCarte.cadrage = {
    center: [...center], zoom,
    bearing: typeof bearing === "number" && Number.isFinite(bearing)
      ? bearing : precedent?.bearing ?? 0,
    pitch: typeof pitch === "number" && Number.isFinite(pitch)
      ? pitch : precedent?.pitch ?? 0,
  };
}
