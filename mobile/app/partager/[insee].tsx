import { useRef } from "react";
import {
  View,
  Text,
  StyleSheet,
  Pressable,
  ScrollView,
  ActivityIndicator,
  Alert,
} from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { MaterialIcons } from "@expo/vector-icons";
import { captureRef } from "react-native-view-shot";
import * as Sharing from "expo-sharing";

import { useFiche } from "../../src/api/queries";
import { texteSurFond, pourcent } from "../../src/lib/color";
import { familleInfo } from "../../src/lib/familles";
import { colors, space, radius, type } from "../../src/theme/tokens";

export default function Partager() {
  const { insee } = useLocalSearchParams<{ insee: string }>();
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const fiche = useFiche(insee);
  const data = fiche.data;
  // Vue capturée en image (l'aperçu de la carte de partage).
  const carteRef = useRef<View>(null);

  async function partager() {
    if (!data) return;
    try {
      const uri = await captureRef(carteRef, { format: "png", quality: 1 });
      if (await Sharing.isAvailableAsync()) {
        await Sharing.shareAsync(uri, {
          mimeType: "image/png",
          dialogTitle: `Partager ${data.nom}`,
        });
      } else {
        Alert.alert("Partage indisponible", "Le partage d'image n'est pas disponible ici.");
      }
    } catch {
      Alert.alert("Export impossible", "La carte n'a pas pu être capturée.");
    }
  }

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

  const { nom, departement, couleur } = data;
  // Même règle que la fiche : la dominante servie par l'API (selon l'algo)
  // prime sur le classement complet.
  const dominante = couleur.famille_dominante ?? couleur.repartition[0]?.famille;
  const tendance = dominante ? familleInfo(dominante).label : null;
  const txt = texteSurFond(couleur.hex);

  return (
    <View style={[styles.page, { paddingTop: insets.top + space.sm }]}>
      <View style={styles.entete}>
        <Pressable
          onPress={() => (router.canGoBack() ? router.back() : router.replace("/"))}
          accessibilityLabel="Fermer"
          style={styles.iconBtn}
        >
          <MaterialIcons name="close" size={24} color={colors.text} />
        </Pressable>
        <Text style={styles.titre} numberOfLines={1}>
          Partager {nom}
        </Text>
        <View style={styles.iconBtn} />
      </View>

      <ScrollView
        contentContainerStyle={{
          padding: space.xl,
          paddingBottom: insets.bottom + space.xxl,
        }}
      >
        {/* Carte de partage (aperçu ET vue capturée en image). collapsable=false :
            requis pour que react-native-view-shot puisse la capturer sur Android.
            allowFontScaling=false sur tous ses textes : le PNG partagé est un
            livrable graphique, il doit sortir identique quelle que soit la
            taille de police système (sinon l'image capturée sort cassée). */}
        <View
          ref={carteRef}
          collapsable={false}
          style={[styles.carte, { backgroundColor: couleur.hex }]}
        >
          <Text
            style={[styles.wordmark, { color: txt, opacity: 0.85 }]}
            allowFontScaling={false}
          >
            CaVoteQuoiIci
          </Text>
          <Text
            style={[styles.carteDept, { color: txt, opacity: 0.85 }]}
            allowFontScaling={false}
          >
            {departement ? `Département ${departement}` : ""}
          </Text>
          <Text style={[styles.carteNom, { color: txt }]} allowFontScaling={false}>
            {nom}
          </Text>
          {tendance ? (
            <Text style={[styles.carteTendance, { color: txt }]} allowFontScaling={false}>
              {tendance}
            </Text>
          ) : null}
          <Text style={[styles.carteParticipation, { color: txt }]} allowFontScaling={false}>
            {pourcent(couleur.participation_mediane)} de participation
          </Text>
          {couleur.repartition.length > 0 ? (
            <View style={styles.miniBarre}>
              {[...couleur.repartition]
                .sort((a, b) => b.part - a.part)
                .map((f) => (
                  <View
                    key={f.famille}
                    style={{
                      flex: Math.max(f.part, 0.001),
                      backgroundColor: familleInfo(f.famille).hex,
                    }}
                  />
                ))}
            </View>
          ) : null}
          <Text
            style={[styles.cartePied, { color: txt, opacity: 0.85 }]}
            allowFontScaling={false}
          >
            Synthèse pondérée · scrutins récents
          </Text>
        </View>
        <Text style={styles.apercu}>Aperçu de l'image partagée</Text>

        <Pressable onPress={partager} accessibilityRole="button" style={styles.partagerBtn}>
          <MaterialIcons name="share" size={20} color={colors.text} />
          <Text style={styles.partagerTxt}>Partager…</Text>
        </Pressable>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bgFull },
  centre: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.bgFull,
  },
  err: { fontSize: 16, color: "#e0707a", ...type.body },
  entete: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: space.lg,
  },
  iconBtn: { width: 44, height: 44, alignItems: "center", justifyContent: "center" },
  titre: { flex: 1, textAlign: "center", fontSize: 17, color: colors.text, ...type.heading },
  carte: { borderRadius: radius.card, padding: space.xl },
  wordmark: { fontSize: 13, ...type.label },
  carteDept: { fontSize: 13, marginTop: space.lg, ...type.body },
  carteNom: { fontSize: 32, marginTop: space.xs, ...type.title },
  carteTendance: { fontSize: 15, marginTop: space.xs, ...type.label },
  carteParticipation: { fontSize: 15, marginTop: space.lg, ...type.label },
  miniBarre: {
    flexDirection: "row",
    height: 12,
    borderRadius: 6,
    overflow: "hidden",
    marginTop: space.sm,
  },
  cartePied: { fontSize: 12, marginTop: space.lg, ...type.body },
  apercu: {
    fontSize: 12,
    color: colors.textTertiary,
    textAlign: "center",
    marginTop: space.md,
    ...type.body,
  },
  partagerBtn: {
    flexDirection: "row",
    gap: space.sm,
    backgroundColor: colors.accent,
    borderRadius: radius.cardSm,
    paddingVertical: space.lg,
    alignItems: "center",
    justifyContent: "center",
    marginTop: space.xl,
    minHeight: 52,
  },
  partagerTxt: { color: colors.text, fontSize: 16, ...type.label },
});