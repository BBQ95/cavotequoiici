import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { MaterialIcons } from "@expo/vector-icons";

import { ALGO_DEFAUT, ALGOS, useAlgo } from "../../src/lib/algo";
import { colors, fontScaleCap, radius, space, type } from "../../src/theme/tokens";

/**
 * Écran Paramètres (P1.3) : choix de l'algorithme de dominance qui teinte
 * les communes — partout dans l'app (recherche, fiche, carte, partage).
 * Chaque option est expliquée en une phrase ; le détail vit dans Méthode.
 */
export default function Parametres() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { algo, setAlgo } = useAlgo();

  return (
    <ScrollView
      style={styles.page}
      contentContainerStyle={{
        paddingTop: insets.top + space.lg,
        paddingBottom: insets.bottom + space.xxl,
        paddingHorizontal: space.xl,
      }}
    >
      <Text style={styles.h1}>Paramètres</Text>

      <Text style={styles.h2}>Couleur des communes</Text>
      <View style={styles.carte}>
        {ALGOS.map((a, i) => {
          const actif = a.id === algo;
          return (
            <Pressable
              key={a.id}
              onPress={() => setAlgo(a.id)}
              accessibilityRole="radio"
              accessibilityState={{ checked: actif }}
              style={[styles.option, i > 0 && styles.optionSuivante]}
            >
              <MaterialIcons
                name={actif ? "radio-button-checked" : "radio-button-unchecked"}
                size={22}
                color={actif ? colors.accentBright : colors.textTertiary}
                style={{ marginTop: 1 }}
              />
              <View style={{ flex: 1 }}>
                <View style={styles.labelRow}>
                  <Text
                    style={styles.label}
                    maxFontSizeMultiplier={fontScaleCap.contraint}
                  >
                    {a.label}
                  </Text>
                  {a.id === ALGO_DEFAUT ? (
                    <Text
                      style={styles.badge}
                      maxFontSizeMultiplier={fontScaleCap.contraint}
                    >
                      défaut
                    </Text>
                  ) : null}
                </View>
                <Text style={styles.description}>{a.description}</Text>
              </View>
            </Pressable>
          );
        })}
      </View>

      <Text style={styles.note}>
        Ce choix change la <Text style={styles.b}>teinte</Text> affichée partout
        (recherche, fiche, carte, partage) et la façon dont la fiche présente la
        répartition : par famille, ou par bloc en mode « Par blocs ». Les données,
        elles, ne bougent pas — les « divers » restent toujours visibles, et la
        fiche rappelle le mode actif.
      </Text>

      <Pressable
        onPress={() => router.navigate("/methode")}
        accessibilityRole="link"
        style={styles.lienBtn}
      >
        <MaterialIcons name="menu-book" size={18} color={colors.accentBright} />
        <Text style={styles.lien}>Comprendre le calcul — onglet Méthode</Text>
      </Pressable>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  h1: { fontSize: 26, color: colors.text, marginBottom: space.lg, ...type.title },
  h2: {
    fontSize: 13,
    color: colors.textSecondary,
    marginTop: space.xl,
    marginBottom: space.sm,
    textTransform: "uppercase",
    letterSpacing: 0.5,
    ...type.label,
  },
  carte: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: radius.card,
    padding: space.lg,
  },
  option: { flexDirection: "row", gap: space.md, alignItems: "flex-start" },
  optionSuivante: {
    marginTop: space.lg,
    paddingTop: space.lg,
    borderTopColor: colors.separator,
    borderTopWidth: 1,
  },
  labelRow: { flexDirection: "row", alignItems: "center", gap: space.sm },
  label: { fontSize: 15, color: colors.text, ...type.label },
  badge: {
    fontSize: 11,
    color: colors.accentBright,
    borderColor: colors.accentBright,
    borderWidth: 1,
    borderRadius: radius.pill,
    paddingHorizontal: space.sm,
    paddingVertical: 1,
    ...type.label,
  },
  description: {
    fontSize: 13,
    color: colors.textSecondary,
    marginTop: space.xs,
    lineHeight: 19,
    ...type.body,
  },
  note: {
    fontSize: 14,
    color: colors.textSecondary,
    lineHeight: 21,
    marginTop: space.xl,
    ...type.body,
  },
  b: { color: colors.text, ...type.label },
  lienBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: space.sm,
    marginTop: space.xl,
    paddingVertical: space.md,
  },
  lien: { fontSize: 15, color: colors.accentBright, ...type.label },
});
