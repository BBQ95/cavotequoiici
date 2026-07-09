import { ScrollView, View, Text, StyleSheet, Linking, Pressable } from "react-native";
import { useRouter } from "expo-router";
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
  const router = useRouter();
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

      <Text style={styles.h2}>Pourquoi ces poids ?</Text>
      <View style={styles.carte}>
        <Point icone="how-to-vote" couleur={colors.accentBright}>
          La couleur est une <Text style={styles.b}>moyenne pondérée de quatre scrutins</Text>,
          qui ne pèsent pas pareil : présidentielle <Text style={styles.b}>1</Text> (le plus
          politique, la plus forte participation), législatives <Text style={styles.b}>0,8</Text>,
          européennes <Text style={styles.b}>0,5</Text>, municipales <Text style={styles.b}>0,35</Text>{" "}
          (le plus local, le moins comparable d'une commune à l'autre).
        </Point>
        <Point icone="history" couleur={colors.accentBright}>
          <Text style={styles.b}>Ancienneté</Text> : un scrutin de 6 ans pèse moitié moins
          qu'un scrutin de cette année. Seuls comptent les écarts d'âge entre scrutins — la
          règle s'applique d'elle-même à chaque nouvelle élection.
        </Point>
        <Point icone="label-off" couleur={colors.textTertiary}>
          <Text style={styles.b}>Listes sans étiquette</Text> : dans beaucoup de petites
          communes, les candidats municipaux n'ont pas de nuance. Le poids des municipales y
          est réduit d'autant — jusqu'à zéro — pour ne pas grisonner des communes qui votent
          clairement aux scrutins nationaux.
        </Point>
        <Point icone="lock-open" couleur={colors.textTertiary}>
          Ces poids sont un <Text style={styles.b}>choix assumé et public</Text>, versionné dans
          un fichier de configuration ouvert (AGPL) : chacun peut vérifier le calcul.
        </Point>
      </View>

      <Text style={styles.h2}>Trois façons de désigner la famille en tête</Text>
      <View style={styles.carte}>
        <Point icone="tune" couleur={colors.accentBright}>
          <Text style={styles.b}>Synthèse complète</Text> : la famille en tête sur
          l'ensemble des suffrages, listes sans étiquette (« divers ») comprises.
          Le plus fidèle aux données brutes ; grâce à la pondération des municipales
          (ci-dessus), très peu de communes restent grises.
        </Point>
        <Point icone="tune" couleur={colors.accentBright}>
          <Text style={styles.b}>Tendance politique</Text> (défaut) : les listes sans
          étiquette ne concourent pas à la teinte, qui vient de la première famille
          politique. Elles restent visibles dans la répartition de chaque fiche.
        </Point>
        <Point icone="tune" couleur={colors.accentBright}>
          <Text style={styles.b}>Par blocs</Text> : gauche, centre et droite sont
          regroupés avant de désigner la teinte — un camp divisé ne perd plus la
          première place face à un camp uni.
        </Point>
        <Point icone="settings" couleur={colors.textTertiary}>
          Le choix se fait dans l'onglet <Text style={styles.b}>Paramètres</Text> et ne
          change que la teinte affichée, jamais les chiffres.
        </Point>
      </View>

      <Text style={styles.h2}>D'où viennent les familles ?</Text>
      <View style={styles.carte}>
        <Point icone="account-balance" couleur={colors.accentBright}>
          Chaque parti ou liste reçoit une <Text style={styles.b}>nuance officielle</Text>,
          fixée scrutin par scrutin par le ministère de l'Intérieur ; l'app range
          chaque nuance dans une famille.
        </Point>
        <Point icone="gavel" couleur={colors.accentBright}>
          En cas de recours, le <Text style={styles.b}>Conseil d'État</Text> tranche —
          il a déjà corrigé plusieurs classements.
        </Point>
        <Point icone="fact-check" couleur={colors.textTertiary}>
          Chaque ligne de la grille est <Text style={styles.b}>sourcée</Text> (Légifrance,
          data.gouv.fr) et versionnée avec le code : l'attribution est vérifiable.
        </Point>
        <Pressable
          onPress={() => router.push("/nuances")}
          accessibilityRole="button"
          style={[styles.lienBtn, { marginTop: space.xs, paddingVertical: space.xs }]}
        >
          <MaterialIcons name="chevron-right" size={18} color={colors.accentBright} />
          <Text style={styles.lien}>Voir la grille, élection par élection</Text>
        </Pressable>
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
