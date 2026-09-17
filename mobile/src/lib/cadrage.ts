/** Mémoire de session : survit au démontage des écrans, pas à l'arrêt de l'app. */
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

export function memoriserCadrage({ center, zoom, bearing, pitch }: Cadrage): void {
  if (![...center, zoom, bearing, pitch].every(Number.isFinite)) return;
  sessionCarte.cadrage = { center: [...center], zoom, bearing, pitch };
}
