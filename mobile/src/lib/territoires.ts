/**
 * Territoires cadrables depuis le sélecteur de la carte. La métropole et
 * l'outre-mer sont géographiquement dispersés : sans ces raccourcis, un DOM/COM
 * est introuvable au pan (les tuiles couvrent pourtant déjà l'outre-mer). Chaque
 * entrée cadre un centre `[lon, lat]` (WGS84) + un zoom d'ensemble adapté à
 * l'étendue du territoire. Source unique, partagée par la carte native et le
 * sélecteur (`app/(tabs)/carte.tsx`).
 */

// Vue initiale de la carte : France métropolitaine.
export const CENTRE_FRANCE: [number, number] = [2.4, 46.6];
export const ZOOM_METROPOLE = 4.4;

export type Territoire = {
  id: string;
  label: string;
  centre: [number, number];
  zoom: number;
};

export const TERRITOIRES: Territoire[] = [
  { id: "metropole", label: "Métropole", centre: CENTRE_FRANCE, zoom: ZOOM_METROPOLE },
  { id: "guadeloupe", label: "Guadeloupe", centre: [-61.55, 16.2], zoom: 8.5 },
  { id: "martinique", label: "Martinique", centre: [-61.02, 14.64], zoom: 9 },
  { id: "guyane", label: "Guyane", centre: [-53.2, 4.2], zoom: 6.5 },
  { id: "reunion", label: "La Réunion", centre: [55.53, -21.13], zoom: 9.5 },
  { id: "mayotte", label: "Mayotte", centre: [45.16, -12.82], zoom: 10 },
  { id: "saint-pierre", label: "St-Pierre-et-Miquelon", centre: [-56.3, 46.95], zoom: 8.5 },
  { id: "polynesie", label: "Polynésie", centre: [-149.45, -17.65], zoom: 7 },
  { id: "nouvelle-caledonie", label: "Nouvelle-Calédonie", centre: [165.5, -21.3], zoom: 6.5 },
];
