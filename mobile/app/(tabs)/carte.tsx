import { useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { colors, radius, space, type } from "../../src/theme/tokens";
import { CommunesMap } from "../../src/components/CommunesMap";
import { COUCHES_COULEUR } from "../../src/lib/tiles";

/**
 * Écran 2 — Carte (Étape 6, sélecteur carte v2). Rend la carte choroplèthe des
 * communes, peinte selon la couche choisie : synthèse (défaut) ou couleur d'un
 * scrutin (cf. `lib/tiles.ts` COUCHES_COULEUR). L'implémentation de la carte
 * dépend de la plateforme : MapLibre natif sur iOS/Android, placeholder sur le
 * web (cf. `src/components/CommunesMap.*`).
 */
export default function Carte() {
  const insets = useSafeAreaInsets();
  const [couche, setCouche] = useState(COUCHES_COULEUR[0]);

  return (
    <View style={[styles.page, { paddingTop: insets.top, paddingBottom: insets.bottom }]}>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        style={styles.selecteur}
        contentContainerStyle={styles.selecteurContenu}
      >
        {COUCHES_COULEUR.map((c) => {
          const active = c.id === couche.id;
          return (
            <Pressable
              key={c.id}
              onPress={() => setCouche(c)}
              accessibilityRole="button"
              accessibilityState={{ selected: active }}
              style={[styles.pill, active && styles.pillActive]}
            >
              <Text style={[styles.pillTxt, active && styles.pillTxtActive]}>{c.label}</Text>
            </Pressable>
          );
        })}
      </ScrollView>
      <CommunesMap couleurProperty={couche.property} />
    </View>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bgFull },
  // flexGrow: 0 : le ScrollView horizontal garde sa hauteur naturelle,
  // la carte prend tout le reste.
  selecteur: { flexGrow: 0 },
  selecteurContenu: {
    paddingHorizontal: space.lg,
    paddingVertical: space.sm,
    gap: space.sm,
  },
  pill: {
    paddingHorizontal: space.lg,
    paddingVertical: space.sm,
    borderRadius: radius.pill,
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
  },
  pillActive: {
    backgroundColor: colors.accent,
    borderColor: colors.accent,
  },
  pillTxt: { fontSize: 13, color: colors.textLight, ...type.label },
  pillTxtActive: { color: colors.text },
});
