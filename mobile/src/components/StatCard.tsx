import { View, Text, StyleSheet } from "react-native";

import { colors, fontScaleCap, radius, space, type } from "../theme/tokens";

/** Carte statistique : grande valeur + label + sous-label (participation, scrutins…). */
export function StatCard({
  valeur,
  label,
  sousLabel,
}: {
  valeur: string;
  label: string;
  sousLabel?: string;
}) {
  return (
    <View style={styles.carte}>
      {/* La carte partage la largeur d'écran avec sa voisine : plafonds serrés. */}
      <Text style={styles.valeur} maxFontSizeMultiplier={fontScaleCap.grand}>
        {valeur}
      </Text>
      <Text style={styles.label} maxFontSizeMultiplier={fontScaleCap.contraint}>
        {label}
      </Text>
      {sousLabel ? (
        <Text style={styles.sousLabel} maxFontSizeMultiplier={fontScaleCap.contraint}>
          {sousLabel}
        </Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  carte: {
    flex: 1,
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: radius.card,
    padding: space.lg,
  },
  valeur: { fontSize: 30, color: colors.text, ...type.title },
  label: { fontSize: 14, color: colors.textLight, marginTop: space.xs, ...type.label },
  sousLabel: { fontSize: 12, color: colors.textTertiary, marginTop: 2, ...type.body },
});
