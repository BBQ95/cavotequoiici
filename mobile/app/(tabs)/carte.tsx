import { useCallback, useRef, useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useFocusEffect } from "expo-router";

import { colors, fontScaleCap, radius, space, type } from "../../src/theme/tokens";
import { CommunesMap } from "../../src/components/CommunesMap";
import { COUCHES_COULEUR, PROPRIETE_SYNTHESE_PAR_ALGO } from "../../src/lib/tiles";
import { useAlgo } from "../../src/lib/algo";
import { getRecents } from "../../src/lib/recents";
import { TERRITOIRES } from "../../src/lib/territoires";

/**
 * Écran 2 — Carte (Étape 6, sélecteur carte v2). Rend la carte choroplèthe des
 * communes, peinte selon la couche choisie : synthèse (défaut) ou couleur d'un
 * scrutin (cf. `lib/tiles.ts` COUCHES_COULEUR). L'implémentation de la carte
 * dépend de la plateforme : MapLibre natif sur iOS/Android, placeholder sur le
 * web (cf. `src/components/CommunesMap.*`).
 *
 * Au focus de l'onglet, la carte se recentre sur la dernière commune visitée
 * (si ses coordonnées sont disponibles dans l'historique local) — sinon, elle
 * reste centrée sur la France métropolitaine.
 */
export default function Carte() {
  const insets = useSafeAreaInsets();
  const [couche, setCouche] = useState(COUCHES_COULEUR[0]);
  // La couche « Synthèse » suit l'algo de dominance choisi dans Paramètres ;
  // les couches par scrutin n'en dépendent pas.
  const { algo } = useAlgo();
  const property =
    couche.id === "synthese" ? PROPRIETE_SYNTHESE_PAR_ALGO[algo] : couche.property;

  // Centre de la carte : [lon, lat] de la dernière commune visitée, ou null
  // (→ France) si aucune coordonnée n'est disponible.
  const [center, setCenter] = useState<[number, number] | undefined>(undefined);

  // Territoire cadré via le sélecteur (métropole / outre-mer). `cle` (jeton
  // incrémental) force le re-cadrage même si on re-tape le même territoire.
  const [terrId, setTerrId] = useState(TERRITOIRES[0].id);
  const [cible, setCible] = useState<
    { centre: [number, number]; zoom: number; cle: number } | undefined
  >(undefined);
  const cleRef = useRef(0);

  useFocusEffect(
    useCallback(() => {
      let actif = true;
      getRecents().then((recents) => {
        if (!actif) return;
        const recent = recents.find(
          (r) =>
            typeof r.lat === "number" &&
            typeof r.lon === "number" &&
            !Number.isNaN(r.lat) &&
            !Number.isNaN(r.lon),
        );
        if (recent && recent.lat != null && recent.lon != null) {
          setCenter([recent.lon, recent.lat]);
        } else {
          setCenter(undefined);
        }
      });
      return () => {
        actif = false;
      };
    }, []),
  );

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
              <Text
                style={[styles.pillTxt, active && styles.pillTxtActive]}
                numberOfLines={1}
                maxFontSizeMultiplier={fontScaleCap.contraint}
              >
                {c.label}
              </Text>
            </Pressable>
          );
        })}
      </ScrollView>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        style={styles.selecteur}
        contentContainerStyle={styles.selecteurContenu}
      >
        {TERRITOIRES.map((t) => {
          const active = t.id === terrId;
          return (
            <Pressable
              key={t.id}
              onPress={() => {
                cleRef.current += 1;
                setTerrId(t.id);
                setCible({ centre: t.centre, zoom: t.zoom, cle: cleRef.current });
              }}
              accessibilityRole="button"
              accessibilityState={{ selected: active }}
              style={[styles.pill, active && styles.pillActive]}
            >
              <Text
                style={[styles.pillTxt, active && styles.pillTxtActive]}
                numberOfLines={1}
                maxFontSizeMultiplier={fontScaleCap.contraint}
              >
                {t.label}
              </Text>
            </Pressable>
          );
        })}
      </ScrollView>
      <CommunesMap couleurProperty={property} center={center} cible={cible} />
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
