import { View, Text, StyleSheet } from "react-native";

import { pourcent } from "../lib/color";

/** Affiché AU MÊME NIVEAU que la couleur (règle d'honnêteté n° 1). */
export function ParticipationBadge({ participation }: { participation: number }) {
  return (
    <View style={styles.badge}>
      <Text style={styles.valeur}>{pourcent(participation)}</Text>
      <Text style={styles.label}>de participation</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    backgroundColor: "#f2f3f5",
    borderRadius: 16,
    paddingVertical: 16,
    paddingHorizontal: 20,
    alignItems: "center",
  },
  valeur: { fontSize: 28, fontWeight: "800", color: "#1a1a1a" },
  label: { fontSize: 14, color: "#5a5a5a", marginTop: 2 },
});
