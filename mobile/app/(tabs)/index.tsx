import { useCallback, useState } from "react";
import {
  View,
  Text,
  TextInput,
  FlatList,
  Pressable,
  StyleSheet,
  ActivityIndicator,
  Alert,
} from "react-native";
import { useRouter, useFocusEffect } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { MaterialIcons } from "@expo/vector-icons";
import * as Location from "expo-location";

import { useSearch } from "../../src/api/queries";
import { api } from "../../src/api/client";
import { getRecents, addRecent, type Recent } from "../../src/lib/recents";
import { colors, radius, space, type } from "../../src/theme/tokens";

export default function Accueil() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const [q, setQ] = useState("");
  const [recents, setRecents] = useState<Recent[]>([]);
  const [geoloc, setGeoloc] = useState(false);
  const { data: resultats, isFetching } = useSearch(q);

  useFocusEffect(
    useCallback(() => {
      getRecents().then(setRecents);
    }, []),
  );

  function ouvrir(c: Recent) {
    addRecent(c);
    router.push(`/commune/${c.code_insee}`);
  }

  async function localiser() {
    try {
      setGeoloc(true);
      const perm = await Location.requestForegroundPermissionsAsync();
      if (perm.status !== "granted") {
        Alert.alert("Localisation refusée", "Autorisez la localisation ou cherchez par nom.");
        return;
      }
      const pos = await Location.getCurrentPositionAsync({});
      const proches = await api.proximite(pos.coords.latitude, pos.coords.longitude, 5000);
      if (proches.length > 0) {
        ouvrir({ code_insee: proches[0].code_insee, nom: proches[0].nom });
      } else {
        Alert.alert("Aucune commune trouvée", "Essayez la recherche par nom.");
      }
    } catch {
      Alert.alert("Localisation indisponible", "Essayez la recherche par nom.");
    } finally {
      setGeoloc(false);
    }
  }

  const listeRecherche = q.trim().length >= 2;
  const donnees: Recent[] = listeRecherche ? (resultats ?? []) : recents;

  return (
    <View style={[styles.page, { paddingTop: insets.top + space.sm }]}>
      <View style={styles.wordmarkRow}>
        <MaterialIcons name="how-to-vote" size={22} color={colors.accentBright} />
        <Text style={styles.wordmark}>CaVoteQuoiIci</Text>
      </View>

      <Text style={styles.accroche}>Quelle est la couleur de votre commune ?</Text>
      <Text style={styles.sousTitre}>
        La synthèse de ses derniers scrutins, participation comprise.
      </Text>

      <View style={styles.champ}>
        <MaterialIcons name="search" size={20} color={colors.textSecondary} />
        <TextInput
          style={styles.input}
          placeholder="Rechercher une commune…"
          placeholderTextColor={colors.textTertiary}
          value={q}
          onChangeText={setQ}
          autoCorrect={false}
          clearButtonMode="while-editing"
        />
      </View>

      <Pressable
        onPress={localiser}
        style={styles.geoBtn}
        accessibilityRole="button"
        disabled={geoloc}
      >
        {geoloc ? (
          <ActivityIndicator color={colors.text} />
        ) : (
          <>
            <MaterialIcons name="my-location" size={18} color={colors.text} />
            <Text style={styles.geoTxt}>Utiliser ma position</Text>
          </>
        )}
      </Pressable>

      {!listeRecherche && recents.length > 0 ? (
        <Text style={styles.section}>Récemment consultées</Text>
      ) : null}

      <FlatList
        style={styles.liste}
        data={donnees}
        keyExtractor={(c) => c.code_insee}
        keyboardShouldPersistTaps="handled"
        contentContainerStyle={{ paddingBottom: insets.bottom + space.lg }}
        ListEmptyComponent={
          listeRecherche && !isFetching ? (
            <Text style={styles.vide}>Aucune commune trouvée.</Text>
          ) : null
        }
        renderItem={({ item }) => (
          <Pressable
            style={styles.ligne}
            onPress={() =>
              ouvrir({
                code_insee: item.code_insee,
                nom: item.nom,
                departement: item.departement,
              })
            }
            accessibilityRole="button"
          >
            <View
              style={[
                styles.pastille,
                { backgroundColor: item.hex ?? colors.border },
              ]}
            />
            <View style={{ flex: 1 }}>
              <Text style={styles.ligneNom}>{item.nom}</Text>
              <Text style={styles.ligneMeta}>
                {[item.departement, item.tendance].filter(Boolean).join(" · ")}
              </Text>
            </View>
            <MaterialIcons name="chevron-right" size={22} color={colors.textTertiary} />
          </Pressable>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.bg, paddingHorizontal: space.xl },
  wordmarkRow: { flexDirection: "row", alignItems: "center", gap: space.sm },
  wordmark: { color: colors.text, fontSize: 17, ...type.heading },
  accroche: { fontSize: 30, color: colors.text, marginTop: space.xxl, ...type.title },
  sousTitre: {
    fontSize: 15,
    color: colors.textSecondary,
    marginTop: space.sm,
    lineHeight: 21,
    ...type.body,
  },
  champ: {
    flexDirection: "row",
    alignItems: "center",
    gap: space.sm,
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: radius.cardSm,
    paddingHorizontal: space.lg,
    marginTop: space.xl,
    minHeight: 50,
  },
  input: { flex: 1, color: colors.text, fontSize: 16, paddingVertical: space.md, ...type.body },
  geoBtn: {
    flexDirection: "row",
    gap: space.sm,
    backgroundColor: colors.accent,
    borderRadius: radius.cardSm,
    paddingVertical: space.md,
    alignItems: "center",
    justifyContent: "center",
    marginTop: space.md,
    minHeight: 50,
  },
  geoTxt: { color: colors.text, fontSize: 15, ...type.label },
  section: {
    marginTop: space.xl,
    marginBottom: space.xs,
    fontSize: 13,
    color: colors.textSecondary,
    ...type.label,
  },
  liste: { flex: 1, marginTop: space.sm },
  ligne: {
    flexDirection: "row",
    alignItems: "center",
    gap: space.md,
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: radius.cardSm,
    paddingHorizontal: space.lg,
    paddingVertical: space.md,
    marginBottom: space.sm,
    minHeight: 56,
  },
  pastille: { width: 16, height: 16, borderRadius: 8 },
  ligneNom: { fontSize: 16, color: colors.text, ...type.label },
  ligneMeta: { fontSize: 13, color: colors.textSecondary, marginTop: 2, ...type.body },
  vide: {
    paddingVertical: space.xxl,
    textAlign: "center",
    color: colors.textSecondary,
    ...type.body,
  },
});
