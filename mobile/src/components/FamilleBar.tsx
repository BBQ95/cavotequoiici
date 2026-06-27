import { View, Text, StyleSheet } from "react-native";

import { familleInfo } from "../lib/familles";
import { pourcent } from "../lib/color";
import type { FamilleVoix } from "../api/client";

/** Barre segmentée colorée par famille politique + légende. */
export function FamilleBar({ familles }: { familles: FamilleVoix[] }) {
  const tri = [...familles].sort((a, b) => b.pourcentage - a.pourcentage);
  return (
    <View>
      <View style={styles.barre}>
        {tri.map((f) => (
          <View
            key={f.famille}
            style={{
              flex: Math.max(f.pourcentage, 0.001),
              backgroundColor: familleInfo(f.famille).hex,
            }}
          />
        ))}
      </View>
      <View style={styles.legende}>
        {tri
          .filter((f) => f.pourcentage >= 0.02)
          .map((f) => (
            <View key={f.famille} style={styles.item}>
              <View
                style={[styles.puce, { backgroundColor: familleInfo(f.famille).hex }]}
              />
              <Text style={styles.texte}>
                {familleInfo(f.famille).label} · {pourcent(f.pourcentage)}
              </Text>
            </View>
          ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  barre: {
    flexDirection: "row",
    height: 22,
    borderRadius: 6,
    overflow: "hidden",
  },
  legende: { marginTop: 10, gap: 4 },
  item: { flexDirection: "row", alignItems: "center", gap: 8 },
  puce: { width: 12, height: 12, borderRadius: 3 },
  texte: { fontSize: 13, color: "#333" },
});
