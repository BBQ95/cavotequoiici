/**
 * Écran « D'où viennent les familles ? » (poussé depuis Méthode).
 *
 * Affiche, pour chaque scrutin, la grille officielle nuance → famille servie
 * par GET /nuances (les CSV versionnés du pipeline, colonne `source` comprise :
 * audit public), précédée du rôle du Conseil d'État dans le nuançage.
 * Contenu éditorial : pipeline/config/nuances/README.md (ne rien inventer).
 */
import { useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { MaterialIcons } from "@expo/vector-icons";

import { useNuances } from "../src/api/queries";
import { familleInfo, libelleScrutin } from "../src/lib/familles";
import { colors, fontScaleCap, radius, space, type } from "../src/theme/tokens";
import type { ScrutinNuances } from "../src/api/client";

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

/** Un scrutin = un accordéon (tout est déjà chargé : pas de fetch à l'ouverture). */
function GrilleScrutin({ scrutin }: { scrutin: ScrutinNuances }) {
  const [ouvert, setOuvert] = useState(false);
  const provisoire = scrutin.nuances.every((n) => n.statut === "provisoire");
  return (
    <View style={styles.bloc}>
      <Pressable
        onPress={() => setOuvert((o) => !o)}
        style={styles.entete}
        accessibilityRole="button"
        accessibilityState={{ expanded: ouvert }}
      >
        <View style={{ flex: 1 }}>
          <Text style={styles.titre} maxFontSizeMultiplier={fontScaleCap.contraint}>
            {libelleScrutin(scrutin.type)} · {scrutin.annee}
          </Text>
          <Text style={styles.meta}>
            classification du {scrutin.date_classification}
            {provisoire ? " · " : ""}
            {provisoire ? (
              <Text style={styles.badgeProvisoire}>provisoire</Text>
            ) : null}
          </Text>
        </View>
        <MaterialIcons
          name={ouvert ? "expand-less" : "expand-more"}
          size={22}
          color={colors.textSecondary}
        />
      </Pressable>

      {ouvert ? (
        <View style={styles.contenu}>
          {scrutin.nuances.map((n) => (
            <View key={n.nuance} style={styles.ligne}>
              <View
                style={[
                  styles.pastille,
                  { backgroundColor: familleInfo(n.famille).hex },
                ]}
              />
              <View style={{ flex: 1 }}>
                <Text style={styles.nuanceTxt}>
                  <Text style={styles.nuanceCode}>{n.nuance}</Text>
                  {"  "}
                  {familleInfo(n.famille).label}
                </Text>
                <Text style={styles.source}>{n.source}</Text>
              </View>
            </View>
          ))}
        </View>
      ) : null}
    </View>
  );
}

export default function Nuances() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { data, isLoading, isError } = useNuances();

  return (
    <ScrollView
      style={styles.page}
      contentContainerStyle={{
        paddingTop: insets.top + space.lg,
        paddingBottom: insets.bottom + space.xxl,
        paddingHorizontal: space.xl,
      }}
    >
      <View style={styles.enteteEcran}>
        <Pressable
          onPress={() => (router.canGoBack() ? router.back() : router.replace("/methode"))}
          accessibilityRole="button"
          accessibilityLabel="Retour"
          hitSlop={12}
          style={styles.retour}
        >
          <MaterialIcons name="arrow-back" size={24} color={colors.text} />
        </Pressable>
        <Text style={styles.h1} maxFontSizeMultiplier={fontScaleCap.grand}>
          D'où viennent les familles ?
        </Text>
      </View>

      <Text style={styles.h2}>Le rôle du Conseil d'État</Text>
      <View style={styles.carte}>
        <Point icone="account-balance" couleur={colors.accentBright}>
          Chaque scrutin a sa propre grille de nuances,{" "}
          <Text style={styles.b}>fixée par une circulaire ou instruction datée du
          ministère de l'Intérieur</Text>. En cas de recours, c'est le{" "}
          <Text style={styles.b}>Conseil d'État</Text> qui tranche.
        </Point>
        <Point icone="gavel" couleur={colors.accentBright}>
          <Text style={styles.b}>2020</Text> (décision CE n° 437675) : la circulaire des
          municipales est partiellement suspendue — seuil des 9 000 habitants, et
          classer « Debout la France » à l'extrême droite était une{" "}
          <Text style={styles.b}>erreur manifeste</Text> → famille « droite ».
        </Point>
        <Point icone="gavel" couleur={colors.accentBright}>
          <Text style={styles.b}>2022</Text> : le Conseil d'État enjoint au ministère
          d'ajouter la nuance <Text style={styles.b}>NUPES</Text> aux législatives —
          sans elle, les candidats de l'union restaient ventilés par parti.
        </Point>
        <Point icone="balance" couleur={colors.textTertiary}>
          La classification de <Text style={styles.b}>La France insoumise</Text> en
          « extrême gauche » dans les grilles récentes reste{" "}
          <Text style={styles.b}>débattue</Text> (contrôle du Conseil d'État) : la
          mention figure, ligne par ligne, dans la source de la grille concernée.
        </Point>
        <Point icone="schedule" couleur={colors.textTertiary}>
          La grille des <Text style={styles.b}>municipales 2026</Text> est{" "}
          <Text style={styles.b}>provisoire</Text> : la circulaire n'était pas encore
          publiée à la date de classification.
        </Point>
      </View>

      <Text style={styles.h2}>La grille, élection par élection</Text>
      {isLoading ? (
        <ActivityIndicator color={colors.textSecondary} style={{ marginTop: space.lg }} />
      ) : null}
      {isError ? <Text style={styles.err}>Grilles indisponibles.</Text> : null}
      {data?.scrutins.map((s) => (
        <GrilleScrutin key={s.scrutin_id} scrutin={s} />
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg },
  enteteEcran: {
    flexDirection: "row",
    alignItems: "center",
    gap: space.md,
    marginBottom: space.lg,
  },
  retour: { padding: space.xs },
  h1: { flex: 1, fontSize: 22, color: colors.text, ...type.title },
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
  bloc: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.cardSm,
    marginTop: space.sm,
    overflow: "hidden",
    backgroundColor: colors.surface,
  },
  entete: { flexDirection: "row", alignItems: "center", padding: space.lg },
  titre: { fontSize: 15, color: colors.text, ...type.label },
  meta: { fontSize: 12, color: colors.textSecondary, marginTop: 2, ...type.body },
  badgeProvisoire: { color: "#f7b32b" },
  contenu: {
    paddingHorizontal: space.lg,
    paddingBottom: space.lg,
    gap: space.md,
  },
  ligne: { flexDirection: "row", gap: space.md, alignItems: "flex-start" },
  pastille: { width: 14, height: 14, borderRadius: 4, marginTop: 3 },
  nuanceTxt: { fontSize: 14, color: colors.textLight, ...type.body },
  nuanceCode: { color: colors.text, ...type.label },
  source: { fontSize: 12, color: colors.textTertiary, marginTop: 2, ...type.body },
  err: { fontSize: 13, color: "#e0707a", marginTop: space.lg, ...type.body },
});
