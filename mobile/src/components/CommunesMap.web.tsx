import { StyleSheet, Text, View } from "react-native";
import { MaterialIcons } from "@expo/vector-icons";

import { colors, space, type } from "../theme/tokens";

/**
 * Variante WEB de la carte : placeholder. MapLibre React Native est un module
 * natif sans support web ; on ne l'importe donc jamais côté web pour que
 * `expo export web` (job CI `mobile`) reste vert. La vraie carte est dans
 * `CommunesMap.native.tsx`.
 */
export function CommunesMap(_props: { couleurProperty?: string }) {
  return (
    <View style={styles.centre}>
      <View style={styles.cercle}>
        <MaterialIcons name="map" size={40} color={colors.accentBright} />
      </View>
      <Text style={styles.titre}>Carte disponible sur mobile</Text>
      <Text style={styles.texte}>
        La carte interactive des communes s'affiche dans l'application mobile
        (iOS / Android). Sur le web, cherchez une commune par son nom dans
        l'onglet Rechercher.
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  centre: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    padding: space.xxl,
  },
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
    ...type.body,
  },
});
