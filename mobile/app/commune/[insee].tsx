import { useEffect } from "react";
import { ScrollView, View, Text, StyleSheet, ActivityIndicator } from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { useFiche, useScrutins } from "../../src/api/queries";
import { ColorHero } from "../../src/components/ColorHero";
import { StatCard } from "../../src/components/StatCard";
import { RepartitionBar } from "../../src/components/RepartitionBar";
import { TransparenceEncart } from "../../src/components/TransparenceEncart";
import { ALGOS, useAlgo } from "../../src/lib/algo";
import { agregerParBlocs } from "../../src/lib/blocs";
import { familleInfo } from "../../src/lib/familles";
import { pourcent } from "../../src/lib/color";
import { addRecent } from "../../src/lib/recents";
import { colors, radius, space, type } from "../../src/theme/tokens";

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
  const { algo } = useAlgo();
  const fiche = useFiche(insee);
  const scrutins = useScrutins(insee);

  const data = fiche.data;
  // `famille_dominante` dépend de l'algo servi (tendance/blocs : divers exclu
  // ou blocs agrégés) ; `repartition[0]` reste le classement complet et sert
  // de repli pour une base pas encore recalculée.
  const dominante =
    data?.couleur.famille_dominante ?? data?.couleur.repartition[0]?.famille;
  const tendance = dominante ? familleInfo(dominante).label : null;

  // Enrichit l'historique local (pastille + tendance + coordonnées pour le
  // recentrage de la carte) une fois la fiche chargée.
  useEffect(() => {
    if (data) {
      addRecent({
        code_insee: data.code_insee,
        nom: data.nom,
        departement: data.departement,
        hex: data.couleur.hex,
        tendance,
        lat: data.lat,
        lon: data.lon,
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

  // La fiche suit le paramètre actif (`useFiche` sert déjà la couleur de
  // l'algo courant) : en mode « blocs », la répartition affichée est agrégée
  // par bloc, comme la teinte du hero.
  const parBlocs = algo === "blocs";
  const segments = parBlocs
    ? agregerParBlocs(couleur.repartition)
    : couleur.repartition.map((f) => ({ famille: f.famille, part: f.part }));
  const algoLabel = ALGOS.find((a) => a.id === algo)?.label ?? algo;

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
          {/* Paramètre actif : la couleur et la répartition en dépendent. */}
          <View style={styles.algoPill}>
            <Text style={styles.algoPillTexte}>
              Couleur calculée : <Text style={styles.algoPillLabel}>{algoLabel}</Text>
            </Text>
          </View>

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

          {segments.length > 0 ? (
            <View style={styles.bloc}>
              <Text style={styles.sectionTitre}>
                {parBlocs ? "Répartition par blocs" : "Répartition des familles"}
              </Text>
              <RepartitionBar segments={segments} />
              {parBlocs ? (
                <Text style={styles.noteBlocs}>
                  « Divers / régionalistes » reste affiché ici mais n'entre pas
                  dans le calcul de la couleur par blocs.
                </Text>
              ) : null}
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
  algoPill: {
    alignSelf: "flex-start",
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: radius.pill,
    paddingHorizontal: space.md,
    paddingVertical: space.xs + 2,
    marginBottom: space.lg,
  },
  algoPillTexte: { fontSize: 13, color: colors.textSecondary, ...type.body },
  algoPillLabel: { color: colors.textLight, ...type.label },
  statsRow: { flexDirection: "row", gap: space.md },
  bloc: { marginTop: space.xl },
  sectionTitre: { fontSize: 16, color: colors.text, marginBottom: space.md, ...type.heading },
  noteBlocs: {
    fontSize: 13,
    color: colors.textSecondary,
    lineHeight: 19,
    marginTop: space.md,
    ...type.body,
  },
  honnete: {
    fontSize: 14,
    color: colors.textSecondary,
    lineHeight: 21,
    marginTop: space.xl,
    ...type.body,
  },
  gras: { color: colors.text, ...type.label },
});
