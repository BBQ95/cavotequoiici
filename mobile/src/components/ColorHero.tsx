import { View, Text, StyleSheet, Pressable } from "react-native";
import { MaterialIcons } from "@expo/vector-icons";

import { texteSurFond } from "../lib/color";
import { radius, space, type } from "../theme/tokens";

/**
 * Hero plein fond = couleur synthétique de la commune. Porte le retour, le
 * partage, le dept·code INSEE, le nom en très grand et la pill « tendance ».
 *
 * NB status bar : ce bloc démarre SOUS la bande système (cf. maquettes) ; le
 * parent réserve l'espace `insets.top` en `colors.bg`, le hero ne remonte pas
 * derrière l'horloge.
 */
export function ColorHero({
  hex,
  nom,
  departement,
  codeInsee,
  tendance,
  onBack,
  onShare,
}: {
  hex: string;
  nom: string;
  departement?: string | null;
  codeInsee: string;
  tendance?: string | null;
  onBack: () => void;
  onShare: () => void;
}) {
  const couleurTexte = texteSurFond(hex);
  const sousTitre = [departement && `Dépt ${departement}`, `INSEE ${codeInsee}`]
    .filter(Boolean)
    .join(" · ");

  return (
    <View style={[styles.hero, { backgroundColor: hex }]}>
      <View style={styles.actions}>
        <Pressable onPress={onBack} accessibilityLabel="Retour" style={styles.iconBtn}>
          <MaterialIcons name="arrow-back" size={24} color={couleurTexte} />
        </Pressable>
        <Pressable onPress={onShare} accessibilityLabel="Partager" style={styles.iconBtn}>
          <MaterialIcons name="share" size={22} color={couleurTexte} />
        </Pressable>
      </View>

      <View style={styles.bas}>
        <Text style={[styles.sousTitre, { color: couleurTexte, opacity: 0.85 }]}>
          {sousTitre}
        </Text>
        <Text style={[styles.nom, { color: couleurTexte }]}>{nom}</Text>
        {tendance ? (
          <View style={[styles.pill, { borderColor: couleurTexte }]}>
            <Text style={[styles.pillTxt, { color: couleurTexte }]}>{tendance}</Text>
          </View>
        ) : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  hero: { minHeight: 230, paddingHorizontal: space.xl, paddingBottom: space.xl },
  actions: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingTop: space.md,
  },
  iconBtn: {
    width: 44,
    height: 44,
    alignItems: "center",
    justifyContent: "center",
    marginHorizontal: -space.md,
  },
  bas: { marginTop: "auto" },
  sousTitre: { fontSize: 13, ...type.label },
  nom: { fontSize: 38, marginTop: space.xs, ...type.title },
  pill: {
    alignSelf: "flex-start",
    borderWidth: 1.5,
    borderRadius: radius.pill,
    paddingHorizontal: space.md,
    paddingVertical: space.xs,
    marginTop: space.md,
  },
  pillTxt: { fontSize: 13, ...type.label },
});
