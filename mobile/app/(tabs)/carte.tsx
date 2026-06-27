import { View, Text, StyleSheet } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { MaterialIcons } from "@expo/vector-icons";

import { colors, space, type } from "../../src/theme/tokens";

/**
 * Écran 2 — Carte. Placeholder en attendant l'Étape 6 (MapLibre Native + tuiles
 * vectorielles PMTiles). La génération des tuiles dépend de tippecanoe (install
 * système, sudo) ; l'écran est posé pour que l'onglet existe et soit cohérent.
 */
export default function Carte() {
  const insets = useSafeAreaInsets();
  return (
    <View style={[styles.page, { paddingTop: insets.top, paddingBottom: insets.bottom }]}>
      <View style={styles.centre}>
        <View style={styles.cercle}>
          <MaterialIcons name="map" size={40} color={colors.accentBright} />
        </View>
        <Text style={styles.titre}>Carte en préparation</Text>
        <Text style={styles.texte}>
          La carte interactive — chaque commune colorée par sa famille dominante,
          déplaçable et zoomable — arrive avec l'étape suivante. En attendant,
          cherchez une commune par son nom dans l'onglet Rechercher.
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bgFull },
  centre: { flex: 1, alignItems: "center", justifyContent: "center", padding: space.xxl },
  cercle: {
    width: 88,
    height: 88,
    borderRadius: 44,
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: space.xl,
  },
  titre: { fontSize: 20, color: colors.text, marginBottom: space.sm, ...type.heading },
  texte: {
    fontSize: 15,
    color: colors.textSecondary,
    textAlign: "center",
    lineHeight: 22,
    maxWidth: 320,
  },
});
