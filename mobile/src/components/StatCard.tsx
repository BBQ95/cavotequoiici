import { View, Text, StyleSheet } from "react-native";

import { colors, radius, space, type } from "../theme/tokens";

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
      <Text style={styles.valeur}>{valeur}</Text>
      <Text style={styles.label}>{label}</Text>
      {sousLabel ? <Text style={styles.sousLabel}>{sousLabel}</Text> : null}
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
