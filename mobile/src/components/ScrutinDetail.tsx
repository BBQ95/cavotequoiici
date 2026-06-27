import { useState } from "react";
import {
  View,
  Text,
  Pressable,
  StyleSheet,
  ActivityIndicator,
} from "react-native";

import { useDetailScrutin } from "../api/queries";
import { libelleScrutin } from "../lib/familles";
import { pourcent } from "../lib/color";
import { FamilleBar } from "./FamilleBar";
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
        <Text style={styles.chevron}>{ouvert ? "▲" : "▼"}</Text>
      </Pressable>

      {ouvert ? (
        <View style={styles.contenu}>
          {isLoading ? <ActivityIndicator /> : null}
          {isError ? <Text style={styles.err}>Détail indisponible.</Text> : null}
          {data ? (
            <>
              <Text style={styles.part}>
                Les électeurs ont voté à {pourcent(data.participation)} de participation
              </Text>
              <FamilleBar familles={data.familles} />
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
    borderColor: "#e6e6e6",
    borderRadius: 12,
    marginTop: 8,
    overflow: "hidden",
  },
  entete: {
    flexDirection: "row",
    alignItems: "center",
    padding: 14,
  },
  titre: { fontSize: 15, fontWeight: "600", color: "#1a1a1a" },
  meta: { fontSize: 12, color: "#777", marginTop: 2 },
  chevron: { fontSize: 12, color: "#999", paddingLeft: 8 },
  contenu: { paddingHorizontal: 14, paddingBottom: 14, gap: 10 },
  part: { fontSize: 13, color: "#444" },
  err: { fontSize: 13, color: "#b00" },
});
