import { useEffect } from "react";
import { ScrollView, View, Text, StyleSheet, ActivityIndicator } from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { useFiche, useScrutins } from "../../src/api/queries";
import { ColorHero } from "../../src/components/ColorHero";
import { StatCard } from "../../src/components/StatCard";
import { RepartitionBar } from "../../src/components/RepartitionBar";
import { TransparenceEncart } from "../../src/components/TransparenceEncart";
import { familleInfo } from "../../src/lib/familles";
import { pourcent } from "../../src/lib/color";
import { addRecent } from "../../src/lib/recents";
import { colors, space, type } from "../../src/theme/tokens";

/** Période couverte par les scrutins (« 2022 – 2026 » ou année unique). */
function periode(dates: string[]): string {
  const annees = dates.map((d) => d.slice(0, 4)).filter(Boolean);
  if (annees.length === 0) return "";
  const min = annees.reduce((a, b) => (a < b ? a : b));
  const max = annees.reduce((a, b) => (a > b ? a : b));
  return min === max ? min : `${min} – ${max}`;
}

export default function FicheCommune() {
  const { insee } = useLocalSearchParams<{ insee: string }>();
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const fiche = useFiche(insee);
  const scrutins = useScrutins(insee);

  const data = fiche.data;
  const dominante = data?.couleur.repartition[0]?.famille;
  const tendance = dominante ? familleInfo(dominante).label : null;

  // Enrichit l'historique local (pastille + tendance) une fois la fiche chargée.
  useEffect(() => {
    if (data) {
      addRecent({
        code_insee: data.code_insee,
        nom: data.nom,
        departement: data.departement,
        hex: data.couleur.hex,
        tendance,
      });
    }
  }, [data, tendance]);

  if (fiche.isLoading) {
    return (
      <View style={styles.centre}>
        <ActivityIndicator color={colors.textSecondary} />
      </View>
    );
  }

  if (fiche.isError || !data) {
    return (
      <View style={styles.centre}>
        <Text style={styles.err}>Commune introuvable.</Text>
      </View>
    );
  }

  const { nom, departement, code_insee, couleur } = data;
  const lignesScrutins = scrutins.data?.scrutins ?? [];

  return (
    <View style={styles.page}>
      <ScrollView contentContainerStyle={{ paddingBottom: insets.bottom + space.xxl }}>
        {/* Bande système : reste en colors.bg, le hero démarre dessous. */}
        <View style={{ height: insets.top, backgroundColor: colors.bg }} />

        <ColorHero
          hex={couleur.hex}
          nom={nom}
          departement={departement}
          codeInsee={code_insee}
          tendance={tendance}
          onBack={() => (router.canGoBack() ? router.back() : router.replace("/"))}
          onShare={() => router.push(`/partager/${code_insee}`)}
        />

        <View style={styles.contenu}>
          <View style={styles.statsRow}>
            <StatCard
              valeur={pourcent(couleur.participation_mediane)}
              label="Participation"
              sousLabel="moyenne pondérée"
            />
            <StatCard
              valeur={String(couleur.scrutins_inclus.length)}
              label="Scrutins inclus"
              sousLabel={periode(lignesScrutins.map((s) => s.date))}
            />
          </View>

          {couleur.repartition.length > 0 ? (
            <View style={styles.bloc}>
              <Text style={styles.sectionTitre}>Répartition des familles</Text>
              <RepartitionBar
                segments={couleur.repartition.map((f) => ({
                  famille: f.famille,
                  part: f.part,
                }))}
              />
            </View>
          ) : null}

          <Text style={styles.honnete}>
            Cette couleur reflète les <Text style={styles.gras}>suffrages exprimés</Text>{" "}
            sur l'ensemble des scrutins récents — pas l'opinion de tous les habitants.
            Moins une commune vote, plus sa couleur est pâle.
          </Text>

          {lignesScrutins.length > 0 ? (
            <TransparenceEncart insee={insee} scrutins={lignesScrutins} />
          ) : null}
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  centre: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.bg,
  },
  err: { fontSize: 16, color: "#e0707a", ...type.body },
  contenu: { paddingHorizontal: space.xl, paddingTop: space.xl },
  statsRow: { flexDirection: "row", gap: space.md },
  bloc: { marginTop: space.xl },
  sectionTitre: { fontSize: 16, color: colors.text, marginBottom: space.md, ...type.heading },
  honnete: {
    fontSize: 14,
    color: colors.textSecondary,
    lineHeight: 21,
    marginTop: space.xl,
    ...type.body,
  },
  gras: { color: colors.text, ...type.label },
});
