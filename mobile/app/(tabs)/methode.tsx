import { ScrollView, View, Text, StyleSheet, Linking, Pressable } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { MaterialIcons } from "@expo/vector-icons";

import { FAMILLES } from "../../src/lib/familles";
import { colors, radius, space, type } from "../../src/theme/tokens";

const DEPOT = "https://github.com/BBQ95/cavotequoiici";

function Point({
  icone,
  couleur,
  children,
}: {
  icone: keyof typeof MaterialIcons.glyphMap;
  couleur: string;
  children: React.ReactNode;
}) {
  return (
    <View style={styles.point}>
      <MaterialIcons name={icone} size={20} color={couleur} style={{ marginTop: 1 }} />
      <Text style={styles.pointTxt}>{children}</Text>
    </View>
  );
}

export default function Methode() {
  const insets = useSafeAreaInsets();
  return (
    <ScrollView
      style={styles.page}
      contentContainerStyle={{
        paddingTop: insets.top + space.lg,
        paddingBottom: insets.bottom + space.xxl,
        paddingHorizontal: space.xl,
      }}
    >
      <Text style={styles.h1}>Comment lire la couleur</Text>

      <Text style={styles.h2}>Ce que la couleur dit</Text>
      <View style={styles.carte}>
        <Point icone="check-circle" couleur={colors.accentBright}>
          C'est une <Text style={styles.b}>synthèse pondérée</Text> de tous les scrutins
          récents (présidentielle, législatives, européennes, municipales) : les plus
          récents et structurants pèsent davantage.
        </Point>
        <Point icone="check-circle" couleur={colors.accentBright}>
          L'<Text style={styles.b}>abstention</Text> entre dans le calcul : plus une commune
          vote peu, plus sa couleur est <Text style={styles.b}>pâle</Text>.
        </Point>
        <Point icone="check-circle" couleur={colors.accentBright}>
          La participation est <Text style={styles.b}>toujours affichée</Text> à côté de la
          couleur, au même niveau.
        </Point>
      </View>

      <Text style={styles.h2}>Ce qu'elle ne dit pas</Text>
      <View style={styles.carte}>
        <Point icone="cancel" couleur={colors.textTertiary}>
          Elle décrit les <Text style={styles.b}>électeurs</Text> qui se sont exprimés, pas
          « les habitants » de la commune.
        </Point>
        <Point icone="cancel" couleur={colors.textTertiary}>
          Ce n'est <Text style={styles.b}>pas un jugement</Text> : « les électeurs de X ont
          voté… », jamais « X est une ville de droite ou de gauche ».
        </Point>
      </View>

      <Text style={styles.h2}>La palette</Text>
      <View style={styles.carte}>
        {Object.entries(FAMILLES).map(([cle, f]) => (
          <View key={cle} style={styles.familleLigne}>
            <View style={[styles.pastille, { backgroundColor: f.hex }]} />
            <Text style={styles.familleTxt}>{f.label}</Text>
          </View>
        ))}
      </View>

      <Pressable
        onPress={() => Linking.openURL(DEPOT)}
        accessibilityRole="link"
        style={styles.lienBtn}
      >
        <MaterialIcons name="open-in-new" size={18} color={colors.accentBright} />
        <Text style={styles.lien}>Voir le code source (AGPL v3)</Text>
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
    gap: space.md,
  },
  point: { flexDirection: "row", gap: space.md, alignItems: "flex-start" },
  pointTxt: { flex: 1, fontSize: 14, color: colors.textLight, lineHeight: 21, ...type.body },
  b: { color: colors.text, ...type.label },
  familleLigne: { flexDirection: "row", alignItems: "center", gap: space.md },
  pastille: { width: 14, height: 14, borderRadius: 4 },
  familleTxt: { fontSize: 15, color: colors.textLight, ...type.body },
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
