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
 * Rôles typographiques : Archivo (titres) + Public Sans (labels & corps).
 * Les polices sont chargées au démarrage par `app/_layout.tsx` (expo-font) ;
 * la graisse est intégrée à chaque variante, donc pas de `fontWeight` ici.
 * Source unique : tout écran lit ces rôles, jamais une famille en dur.
 */
export const type = {
  title: { fontFamily: "Archivo_900Black" },
  heading: { fontFamily: "Archivo_800ExtraBold" },
  label: { fontFamily: "PublicSans_600SemiBold" },
  body: { fontFamily: "PublicSans_400Regular" },
} as const;

/**
 * Plafonds de grossissement (prop `maxFontSizeMultiplier`) quand la police
 * système est agrandie (accessibilité). Seules les zones à géométrie serrée
 * sont plafonnées — le corps de texte scale librement, c'est lui qu'on lit.
 * `grand` : titres 30-38 pt (déjà énormes, déborderaient en largeur) ;
 * `contraint` : libellés dans pilules, boutons, cartes à largeur bornée.
 */
export const fontScaleCap = {
  grand: 1.2,
  contraint: 1.4,
} as const;
