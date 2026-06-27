/**
 * Jetons visuels — thème sombre unique (cf. Outline « Application mobile —
 * Maquettes & specs », section « Système visuel »). Source unique : tout écran
 * et composant lit ces valeurs, jamais une couleur en dur.
 */

export const colors = {
  /** Fond principal des écrans. */
  bg: "#14181c",
  /** Fond des écrans pleins / cartes / sheets (plus sombre). */
  bgFull: "#0c0f13",
  /** Surface des cartes, champs, encarts. */
  surface: "#1d2329",
  /** Bordure des surfaces. */
  border: "#2a323a",
  /** Séparateurs (lignes fines, bordure haute de la barre d'onglets). */
  separator: "#232a31",
  /** Accent : boutons pleins, hero d'action. */
  accent: "#4e8e3c",
  /** Accent vif : points actifs, icône d'onglet active. */
  accentBright: "#4cc23f",
  /** Texte primaire. */
  text: "#ffffff",
  /** Texte secondaire. */
  textSecondary: "#8b96a0",
  /** Texte tertiaire. */
  textTertiary: "#7d8893",
  /** Texte clair (sur surfaces sombres, plus contrasté que secondaire). */
  textLight: "#c2cad2",
  /** Icône / label d'onglet inactif. */
  tabInactive: "#5c6670",
} as const;

/** Rayons d'arrondi. */
export const radius = {
  card: 16,
  cardSm: 14,
  pill: 24,
  pillLg: 30,
} as const;

/** Échelle d'espacement (multiples de 4). */
export const space = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  xxl: 24,
} as const;

/**
 * Rôles typographiques. Cible : Archivo (titres 800–900) + Public Sans (labels).
 * Les polices ne sont pas encore chargées (suivi) ; on s'appuie sur la police
 * système avec les graisses correspondantes. Centraliser ici facilite le swap.
 */
export const type = {
  title: { fontWeight: "900" as const },
  heading: { fontWeight: "800" as const },
  label: { fontWeight: "600" as const },
} as const;
