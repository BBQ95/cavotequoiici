import { ScrollView, View, Text, StyleSheet, ActivityIndicator } from "react-native";
import { useLocalSearchParams, Stack } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { useFiche, useScrutins } from "../../src/api/queries";
import { ColorHero } from "../../src/components/ColorHero";
import { ParticipationBadge } from "../../src/components/ParticipationBadge";
import { TransparenceEncart } from "../../src/components/TransparenceEncart";

export default function FicheCommune() {
  const { insee } = useLocalSearchParams<{ insee: string }>();
  const insets = useSafeAreaInsets();
  const fiche = useFiche(insee);
  const scrutins = useScrutins(insee);

  if (fiche.isLoading) {
    return (
      <View style={styles.centre}>
        <ActivityIndicator />
      </View>
    );
  }

  if (fiche.isError || !fiche.data) {
    return (
      <View style={styles.centre}>
        <Text style={styles.err}>Commune introuvable.</Text>
      </View>
    );
  }

  const { nom, departement, couleur } = fiche.data;

  return (
    <>
      <Stack.Screen options={{ title: nom }} />
      <ScrollView
        style={styles.page}
        contentContainerStyle={{ paddingBottom: insets.bottom + 32 }}
      >
        <ColorHero hex={couleur.hex} nom={nom} departement={departement} />

        <View style={styles.row}>
          <ParticipationBadge participation={couleur.participation_mediane} />
        </View>

        <Text style={styles.honnete}>
          Cette couleur reflète les <Text style={styles.gras}>suffrages exprimés</Text> sur
          l'ensemble des scrutins récents — pas l'opinion de tous les habitants. Moins une
          commune vote, plus sa couleur est pâle.
        </Text>

        {scrutins.data ? (
          <TransparenceEncart insee={insee} scrutins={scrutins.data.scrutins} />
        ) : null}
      </ScrollView>
    </>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, paddingHorizontal: 20 },
  centre: { flex: 1, alignItems: "center", justifyContent: "center" },
  err: { fontSize: 16, color: "#b00" },
  row: { marginTop: 16 },
  honnete: { fontSize: 14, color: "#555", lineHeight: 21, marginTop: 18 },
  gras: { fontWeight: "700", color: "#1a1a1a" },
});
