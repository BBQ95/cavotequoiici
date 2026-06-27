import { Stack } from "expo-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { StatusBar } from "expo-status-bar";

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 5 * 60 * 1000, retry: 1 } },
});

export default function RootLayout() {
  return (
    <QueryClientProvider client={queryClient}>
      <SafeAreaProvider>
        <StatusBar style="auto" />
        <Stack
          screenOptions={{
            headerStyle: { backgroundColor: "#ffffff" },
            headerTitleStyle: { fontWeight: "700" },
            headerTintColor: "#1a1a1a",
            contentStyle: { backgroundColor: "#ffffff" },
          }}
        >
          <Stack.Screen name="index" options={{ title: "CaVoteQuoiIci" }} />
          <Stack.Screen name="commune/[insee]" options={{ title: "" }} />
          <Stack.Screen name="about" options={{ title: "Méthodologie" }} />
        </Stack>
      </SafeAreaProvider>
    </QueryClientProvider>
  );
}
