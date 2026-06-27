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
import { useRouter, useFocusEffect, Link } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import * as Location from "expo-location";

import { useSearch } from "../src/api/queries";
import { api } from "../src/api/client";
import { getRecents, addRecent, type Recent } from "../src/lib/recents";

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
  const donnees: { code_insee: string; nom: string; departement?: string | null }[] =
    listeRecherche ? (resultats ?? []) : recents;

  return (
    <View style={[styles.page, { paddingBottom: insets.bottom }]}>
      <Text style={styles.accroche}>C'est quoi la couleur de ta ville ?</Text>

      <TextInput
        style={styles.input}
        placeholder="Chercher une commune…"
        value={q}
        onChangeText={setQ}
        autoCorrect={false}
        clearButtonMode="while-editing"
      />

      <Pressable
        onPress={localiser}
        style={styles.geoBtn}
        accessibilityRole="button"
        disabled={geoloc}
      >
        {geoloc ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.geoTxt}>📍 Utiliser ma position</Text>
        )}
      </Pressable>

      {!listeRecherche && recents.length > 0 ? (
        <Text style={styles.section}>Récemment consultées</Text>
      ) : null}

      <FlatList
        data={donnees}
        keyExtractor={(c) => c.code_insee}
        keyboardShouldPersistTaps="handled"
        ListEmptyComponent={
          listeRecherche && !isFetching ? (
            <Text style={styles.vide}>Aucune commune trouvée.</Text>
          ) : null
        }
        renderItem={({ item }) => (
          <Pressable
            style={styles.ligne}
            onPress={() => ouvrir({ code_insee: item.code_insee, nom: item.nom })}
            accessibilityRole="button"
          >
            <Text style={styles.ligneNom}>{item.nom}</Text>
            <Text style={styles.ligneDept}>{item.departement ?? ""}</Text>
          </Pressable>
        )}
      />

      <Link href="/about" style={styles.lien}>
        Méthodologie & transparence
      </Link>
    </View>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, paddingHorizontal: 20, paddingTop: 8 },
  accroche: { fontSize: 22, fontWeight: "800", color: "#1a1a1a", marginBottom: 16 },
  input: {
    borderWidth: 1,
    borderColor: "#d8d8d8",
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 16,
  },
  geoBtn: {
    backgroundColor: "#1a1a1a",
    borderRadius: 12,
    paddingVertical: 12,
    alignItems: "center",
    marginTop: 10,
    minHeight: 48,
    justifyContent: "center",
  },
  geoTxt: { color: "#fff", fontSize: 15, fontWeight: "600" },
  section: { marginTop: 18, marginBottom: 4, fontSize: 13, color: "#888", fontWeight: "600" },
  ligne: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: "#f0f0f0",
    minHeight: 48,
  },
  ligneNom: { fontSize: 16, color: "#1a1a1a" },
  ligneDept: { fontSize: 14, color: "#999" },
  vide: { paddingVertical: 24, textAlign: "center", color: "#999" },
  lien: { paddingVertical: 16, color: "#2D6FCB", fontSize: 15 },
});
