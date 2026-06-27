import {
  View,
  Text,
  StyleSheet,
  Pressable,
  ScrollView,
  ActivityIndicator,
  Share,
  Alert,
} from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { MaterialIcons } from "@expo/vector-icons";

import { useFiche } from "../../src/api/queries";
import { RepartitionBar } from "../../src/components/RepartitionBar";
import { texteSurFond, pourcent } from "../../src/lib/color";
import { familleInfo } from "../../src/lib/familles";
import { colors, radius, space, type } from "../../src/theme/tokens";

export default function Partager() {
  const { insee } = useLocalSearchParams<{ insee: string }>();
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const fiche = useFiche(insee);
  const data = fiche.data;

  const lien = `cavotequoiici://commune/${insee}`;

  async function partager() {
    if (!data) return;
    const tendance = data.couleur.repartition[0]
      ? familleInfo(data.couleur.repartition[0].famille).label
      : "tendance inconnue";
    try {
      await Share.share({
        message:
          `${data.nom} — ${tendance}, ${pourcent(data.couleur.participation_mediane)} ` +
          `de participation. La couleur politique de ma commune sur CaVoteQuoiIci.\n${lien}`,
      });
    } catch {
      // partage annulé : rien à faire
    }
  }

  function aVenir(quoi: string) {
    Alert.alert(quoi, "Disponible dans une prochaine version.");
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
  const dominante = couleur.repartition[0]?.famille;
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
        {/* Carte de partage (aperçu de l'image). */}
        <View style={[styles.carte, { backgroundColor: couleur.hex }]}>
          <Text style={[styles.wordmark, { color: txt, opacity: 0.85 }]}>
            CaVoteQuoiIci
          </Text>
          <Text style={[styles.carteDept, { color: txt, opacity: 0.85 }]}>
            {departement ? `Département ${departement}` : ""}
          </Text>
          <Text style={[styles.carteNom, { color: txt }]}>{nom}</Text>
          {tendance ? (
            <Text style={[styles.carteTendance, { color: txt }]}>{tendance}</Text>
          ) : null}
          <Text style={[styles.carteParticipation, { color: txt }]}>
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
          <Text style={[styles.cartePied, { color: txt, opacity: 0.85 }]}>
            Synthèse pondérée · scrutins récents
          </Text>
        </View>
        <Text style={styles.apercu}>Aperçu de l'image partagée</Text>

        <View style={styles.actionsRow}>
          <ActionSecondaire icone="link" label="Copier" onPress={partager} />
          <ActionSecondaire
            icone="image"
            label="Image"
            onPress={() => aVenir("Export image")}
          />
          <ActionSecondaire
            icone="qr-code-2"
            label="QR code"
            onPress={() => aVenir("QR code")}
          />
        </View>

        <Pressable onPress={partager} accessibilityRole="button" style={styles.partagerBtn}>
          <MaterialIcons name="share" size={20} color={colors.text} />
          <Text style={styles.partagerTxt}>Partager…</Text>
        </Pressable>
      </ScrollView>
    </View>
  );
}

function ActionSecondaire({
  icone,
  label,
  onPress,
}: {
  icone: keyof typeof MaterialIcons.glyphMap;
  label: string;
  onPress: () => void;
}) {
  return (
    <Pressable onPress={onPress} accessibilityRole="button" style={styles.action}>
      <MaterialIcons name={icone} size={22} color={colors.accentBright} />
      <Text style={styles.actionTxt}>{label}</Text>
    </Pressable>
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
  err: { fontSize: 16, color: "#e0707a" },
  entete: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: space.lg,
  },
  iconBtn: { width: 44, height: 44, alignItems: "center", justifyContent: "center" },
  titre: { flex: 1, textAlign: "center", fontSize: 17, color: colors.text, ...type.heading },
  carte: { borderRadius: radius.card, padding: space.xl },
  wordmark: { fontSize: 13, ...type.label },
  carteDept: { fontSize: 13, marginTop: space.lg },
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
  cartePied: { fontSize: 12, marginTop: space.lg },
  apercu: {
    fontSize: 12,
    color: colors.textTertiary,
    textAlign: "center",
    marginTop: space.md,
  },
  actionsRow: { flexDirection: "row", gap: space.md, marginTop: space.xl },
  action: {
    flex: 1,
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: radius.cardSm,
    paddingVertical: space.lg,
    alignItems: "center",
    gap: space.xs,
  },
  actionTxt: { fontSize: 13, color: colors.textLight, ...type.label },
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
