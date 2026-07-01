import { StyleSheet, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { colors } from "../../src/theme/tokens";
import { CommunesMap } from "../../src/components/CommunesMap";

/**
 * Écran 2 — Carte (Étape 6). Rend la carte choroplèthe des communes.
 * L'implémentation dépend de la plateforme : carte MapLibre native sur
 * iOS/Android, placeholder sur le web (cf. `src/components/CommunesMap.*`).
 */
export default function Carte() {
  const insets = useSafeAreaInsets();
  return (
    <View style={[styles.page, { paddingTop: insets.top, paddingBottom: insets.bottom }]}>
      <CommunesMap />
    </View>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bgFull },
});
