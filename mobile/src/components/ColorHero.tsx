import { View, Text, StyleSheet } from "react-native";

import { texteSurFond } from "../lib/color";

export function ColorHero({
  hex,
  nom,
  departement,
}: {
  hex: string;
  nom: string;
  departement?: string | null;
}) {
  const couleurTexte = texteSurFond(hex);
  return (
    <View style={[styles.hero, { backgroundColor: hex }]}>
      <Text style={[styles.nom, { color: couleurTexte }]}>{nom}</Text>
      {departement ? (
        <Text style={[styles.dept, { color: couleurTexte, opacity: 0.85 }]}>
          Département {departement}
        </Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  hero: {
    minHeight: 180,
    borderRadius: 20,
    paddingHorizontal: 24,
    paddingVertical: 28,
    justifyContent: "flex-end",
  },
  nom: { fontSize: 32, fontWeight: "800" },
  dept: { fontSize: 15, marginTop: 4 },
});
