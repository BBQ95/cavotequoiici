import { View, Text, StyleSheet } from "react-native";

import { familleInfo } from "../lib/familles";
import { colors, space, type } from "../theme/tokens";

/** Une part de famille, normalisée pour l'affichage (0–1). */
export type Segment = { famille: string; part: number };

/**
 * Barre segmentée colorée par famille + légende. Source unique pour la
 * répartition de synthèse (fiche) ET la répartition par scrutin (accordéon).
 */
export function RepartitionBar({ segments }: { segments: Segment[] }) {
  const tri = [...segments].sort((a, b) => b.part - a.part);
  return (
    <View>
      <View style={styles.barre}>
        {tri.map((s) => (
          <View
            key={s.famille}
            style={{
              flex: Math.max(s.part, 0.001),
              backgroundColor: familleInfo(s.famille).hex,
            }}
          />
        ))}
      </View>
      <View style={styles.legende}>
        {tri
          .filter((s) => s.part >= 0.02)
          .map((s) => (
            <View key={s.famille} style={styles.item}>
              <View style={[styles.puce, { backgroundColor: familleInfo(s.famille).hex }]} />
              <Text style={styles.texte}>
                {familleInfo(s.famille).label} · {Math.round(s.part * 100)} %
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
    backgroundColor: colors.border,
  },
  legende: { marginTop: space.md, gap: space.xs },
  item: { flexDirection: "row", alignItems: "center", gap: space.sm },
  puce: { width: 12, height: 12, borderRadius: 3 },
  texte: { fontSize: 13, color: colors.textLight, ...type.label },
});
