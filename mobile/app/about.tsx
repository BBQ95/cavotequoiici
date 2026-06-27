import { ScrollView, View, Text, StyleSheet, Linking, Pressable } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

const DEPOT = "https://github.com/BBQ95/cavotequoiici";

function Para({ children }: { children: React.ReactNode }) {
  return <Text style={styles.p}>{children}</Text>;
}

export default function About() {
  const insets = useSafeAreaInsets();
  return (
    <ScrollView
      style={styles.page}
      contentContainerStyle={{ paddingBottom: insets.bottom + 32 }}
    >
      <Text style={styles.h1}>La couleur, et ce qu'elle ne dit pas</Text>

      <Para>
        La couleur d'une commune est une <Text style={styles.b}>synthèse pondérée</Text> de ses
        scrutins récents (présidentielle, législatives, européennes, municipales). Les scrutins
        les plus récents et les plus structurants pèsent davantage.
      </Para>
      <Para>
        L'<Text style={styles.b}>abstention</Text> entre dans le calcul : elle ne change pas la
        teinte (on ne prête aucune opinion aux abstentionnistes), mais elle{" "}
        <Text style={styles.b}>pâlit</Text> la couleur. Une couleur vive = un résultat net et une
        participation normale.
      </Para>
      <Para>
        La couleur décrit les <Text style={styles.b}>électeurs</Text>, pas « les habitants », et
        n'est pas un jugement. Le taux de participation est toujours affiché à côté de la couleur.
      </Para>

      <Text style={styles.h2}>Familles politiques</Text>
      <Para>
        Les candidats et listes sont regroupés en familles à partir des nuances officielles du
        ministère de l'Intérieur. Ce regroupement est documenté, daté et discutable publiquement.
      </Para>

      <Text style={styles.h2}>Sources & code</Text>
      <Para>
        Données : résultats officiels (data.gouv.fr) et contours IGN/Etalab. Application{" "}
        <Text style={styles.b}>libre (AGPL v3)</Text> : la méthode et les pondérations sont
        auditables.
      </Para>
      <Pressable onPress={() => Linking.openURL(DEPOT)} accessibilityRole="link">
        <Text style={styles.lien}>Code source sur GitHub</Text>
      </Pressable>

      <View style={{ height: 24 }} />
      <Para>Gratuit, sans publicité, sans compte. Soutien : page dédiée à venir.</Para>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, paddingHorizontal: 20 },
  h1: { fontSize: 22, fontWeight: "800", color: "#1a1a1a", marginTop: 8, marginBottom: 8 },
  h2: { fontSize: 17, fontWeight: "700", color: "#1a1a1a", marginTop: 20, marginBottom: 4 },
  p: { fontSize: 15, color: "#444", lineHeight: 22, marginTop: 8 },
  b: { fontWeight: "700", color: "#1a1a1a" },
  lien: { fontSize: 15, color: "#2D6FCB", marginTop: 10 },
});
