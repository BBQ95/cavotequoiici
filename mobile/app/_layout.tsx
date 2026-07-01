import { useEffect } from "react";
import { Stack } from "expo-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { StatusBar } from "expo-status-bar";
import { useFonts } from "expo-font";
import * as SplashScreen from "expo-splash-screen";
// Imports par sous-chemin (une variante = un fichier) plutôt que le barrel du
// paquet, qui embarquerait TOUTES les graisses/italiques (plusieurs Mo inutiles).
import { Archivo_800ExtraBold } from "@expo-google-fonts/archivo/800ExtraBold";
import { Archivo_900Black } from "@expo-google-fonts/archivo/900Black";
import { PublicSans_400Regular } from "@expo-google-fonts/public-sans/400Regular";
import { PublicSans_600SemiBold } from "@expo-google-fonts/public-sans/600SemiBold";

import { colors } from "../src/theme/tokens";

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 5 * 60 * 1000, retry: 1 } },
});

// Maintient le splash tant que les polices de marque ne sont pas prêtes (évite
// un flash en police système). Idempotent, au chargement du module. Le .catch
// absorbe un rejet natif bénin (ex. splash déjà masqué).
SplashScreen.preventAutoHideAsync().catch(() => {});

export default function RootLayout() {
  // Variantes utilisées par les rôles de src/theme/tokens.ts (title/heading =
  // Archivo, label/body = Public Sans). La graisse est intégrée à la variante.
  const [fontsLoaded, fontError] = useFonts({
    Archivo_800ExtraBold,
    Archivo_900Black,
    PublicSans_400Regular,
    PublicSans_600SemiBold,
  });

  useEffect(() => {
    if (fontsLoaded || fontError) SplashScreen.hideAsync().catch(() => {});
  }, [fontsLoaded, fontError]);

  // Rien tant que les polices chargent. En cas d'échec (fontError), on affiche
  // quand même l'app : dégradation en police système plutôt qu'écran bloqué.
  if (!fontsLoaded && !fontError) return null;

  return (
    <QueryClientProvider client={queryClient}>
      <SafeAreaProvider>
        {/* Thème sombre unique : barre système en texte clair. */}
        <StatusBar style="light" />
        <Stack
          screenOptions={{
            headerShown: false,
            contentStyle: { backgroundColor: colors.bg },
          }}
        >
          <Stack.Screen name="(tabs)" />
          <Stack.Screen name="commune/[insee]" />
          {/* Écran 4 — Partager : modale plein écran. */}
          <Stack.Screen
            name="partager/[insee]"
            options={{ presentation: "modal" }}
          />
        </Stack>
      </SafeAreaProvider>
    </QueryClientProvider>
  );
}
