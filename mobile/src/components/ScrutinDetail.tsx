import { useState } from "react";
import { View, Text, Pressable, StyleSheet, ActivityIndicator } from "react-native";
import { MaterialIcons } from "@expo/vector-icons";

import { useDetailScrutin } from "../api/queries";
import { libelleScrutin } from "../lib/familles";
import { pourcent } from "../lib/color";
import { RepartitionBar } from "./RepartitionBar";
import { colors, radius, space, type } from "../theme/tokens";
import type { ScrutinInclus } from "../api/client";

export function ScrutinDetail({
  insee,
  scrutin,
}: {
  insee: string;
  scrutin: ScrutinInclus;
}) {
  const [ouvert, setOuvert] = useState(false);
  const { data, isLoading, isError } = useDetailScrutin(
    insee,
    ouvert ? scrutin.scrutin_id : null,
  );

  return (
    <View style={styles.bloc}>
      <Pressable
        onPress={() => setOuvert((o) => !o)}
        style={styles.entete}
        accessibilityRole="button"
      >
        <View style={{ flex: 1 }}>
          <Text style={styles.titre}>{libelleScrutin(scrutin.type)}</Text>
          <Text style={styles.meta}>
            {scrutin.date ?? ""} · poids {Math.round(scrutin.poids_relatif * 100)} %
          </Text>
        </View>
        <MaterialIcons
          name={ouvert ? "expand-less" : "expand-more"}
          size={22}
          color={colors.textSecondary}
        />
      </Pressable>

      {ouvert ? (
        <View style={styles.contenu}>
          {isLoading ? <ActivityIndicator color={colors.textSecondary} /> : null}
          {isError ? <Text style={styles.err}>Détail indisponible.</Text> : null}
          {data ? (
            <>
              <Text style={styles.part}>
                Les électeurs ont voté à {pourcent(data.participation)} de participation.
              </Text>
              <RepartitionBar
                segments={data.familles.map((f) => ({
                  famille: f.famille,
                  part: f.pourcentage,
                }))}
              />
            </>
          ) : null}
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  bloc: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.cardSm,
    marginTop: space.sm,
    overflow: "hidden",
  },
  entete: { flexDirection: "row", alignItems: "center", padding: space.lg },
  titre: { fontSize: 15, color: colors.text, ...type.label },
  meta: { fontSize: 12, color: colors.textSecondary, marginTop: 2 },
  contenu: { paddingHorizontal: space.lg, paddingBottom: space.lg, gap: space.md },
  part: { fontSize: 13, color: colors.textLight },
  err: { fontSize: 13, color: "#e0707a" },
});
