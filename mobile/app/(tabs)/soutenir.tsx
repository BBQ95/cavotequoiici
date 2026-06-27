import { useState } from "react";
import { ScrollView, View, Text, Pressable, StyleSheet, Linking } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { MaterialIcons } from "@expo/vector-icons";

import { colors, radius, space, type } from "../../src/theme/tokens";

const DEPOT = "https://github.com/BBQ95/cavotequoiici";
// Plateformes de don (liens sortants ; pas de paiement in-app au lancement).
const DON_URL = "https://liberapay.com/cavotequoiici";

const MONTANTS = [
  { val: "1", label: "1 €" },
  { val: "2", label: "2 €", populaire: true },
  { val: "5", label: "5 €" },
  { val: "autre", label: "Autre" },
];

export default function Soutenir() {
  const insets = useSafeAreaInsets();
  const [choix, setChoix] = useState("2");

  return (
    <ScrollView
      style={styles.page}
      contentContainerStyle={{
        paddingTop: insets.top + space.lg,
        paddingBottom: insets.bottom + space.xxl,
        paddingHorizontal: space.xl,
      }}
    >
      <View style={styles.cercle}>
        <MaterialIcons name="favorite" size={36} color={colors.accentBright} />
      </View>
      <Text style={styles.h1}>Soutenir le projet</Text>
      <Text style={styles.intro}>
        CaVoteQuoiIci est gratuit, sans publicité et sans compte. Les seuls coûts
        (serveurs, données) sont couverts par vos dons. Aucun don ne déverrouille de
        fonction : c'est un geste de soutien, rien d'autre.
      </Text>

      <View style={styles.montants}>
        {MONTANTS.map((m) => {
          const actif = m.val === choix;
          return (
            <Pressable
              key={m.val}
              onPress={() => setChoix(m.val)}
              accessibilityRole="button"
              style={[styles.montant, actif && styles.montantActif]}
            >
              <Text style={[styles.montantTxt, actif && styles.montantTxtActif]}>
                {m.label}
              </Text>
              {m.populaire ? <Text style={styles.populaire}>Populaire</Text> : null}
            </Pressable>
          );
        })}
      </View>

      <Pressable
        onPress={() => Linking.openURL(DON_URL)}
        accessibilityRole="button"
        style={styles.donBtn}
      >
        <Text style={styles.donTxt}>Faire un don</Text>
      </Pressable>
      <Text style={styles.plateformes}>
        Liberapay · GitHub Sponsors — sans intermédiaire commercial.
      </Text>

      <View style={styles.carte}>
        <View style={styles.carteEntete}>
          <MaterialIcons name="lock-open" size={20} color={colors.accentBright} />
          <Text style={styles.carteTitre}>100 % open source</Text>
        </View>
        <Text style={styles.carteTxt}>
          Le code et la méthode de calcul des couleurs sont publics et auditables, sous
          licence AGPL v3. Rien n'est caché : les scrutins inclus et leurs poids sont
          toujours visibles.
        </Text>
        <Pressable
          onPress={() => Linking.openURL(DEPOT)}
          accessibilityRole="link"
          style={styles.lienBtn}
        >
          <MaterialIcons name="open-in-new" size={18} color={colors.accentBright} />
          <Text style={styles.lien}>Voir le code source</Text>
        </Pressable>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  cercle: {
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: space.lg,
  },
  h1: { fontSize: 26, color: colors.text, ...type.title },
  intro: { fontSize: 15, color: colors.textSecondary, lineHeight: 22, marginTop: space.sm },
  montants: { flexDirection: "row", gap: space.sm, marginTop: space.xl },
  montant: {
    flex: 1,
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: radius.cardSm,
    paddingVertical: space.lg,
    alignItems: "center",
    minHeight: 56,
    justifyContent: "center",
  },
  montantActif: { borderColor: colors.accentBright },
  montantTxt: { fontSize: 16, color: colors.textLight, ...type.label },
  montantTxtActif: { color: colors.text },
  populaire: { fontSize: 10, color: colors.accentBright, marginTop: 2 },
  donBtn: {
    backgroundColor: colors.accent,
    borderRadius: radius.cardSm,
    paddingVertical: space.lg,
    alignItems: "center",
    marginTop: space.lg,
    minHeight: 52,
    justifyContent: "center",
  },
  donTxt: { color: colors.text, fontSize: 16, ...type.label },
  plateformes: {
    fontSize: 13,
    color: colors.textTertiary,
    textAlign: "center",
    marginTop: space.md,
  },
  carte: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: radius.card,
    padding: space.lg,
    marginTop: space.xl,
  },
  carteEntete: { flexDirection: "row", alignItems: "center", gap: space.sm },
  carteTitre: { fontSize: 16, color: colors.text, ...type.heading },
  carteTxt: { fontSize: 14, color: colors.textLight, lineHeight: 21, marginTop: space.sm },
  lienBtn: { flexDirection: "row", alignItems: "center", gap: space.sm, marginTop: space.md },
  lien: { fontSize: 15, color: colors.accentBright, ...type.label },
});
