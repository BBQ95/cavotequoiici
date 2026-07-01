import { Tabs } from "expo-router";
import { MaterialIcons } from "@expo/vector-icons";

import { colors } from "../../src/theme/tokens";

/**
 * Barre d'onglets persistante (cf. maquettes) : Rechercher · Carte · Méthode.
 * Fiche commune (poussée) et Partager (modale) ne sont pas des onglets.
 */
export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.accentBright,
        tabBarInactiveTintColor: colors.tabInactive,
        tabBarStyle: {
          backgroundColor: colors.bg,
          borderTopColor: colors.separator,
        },
        tabBarLabelStyle: { fontSize: 11 },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: "Rechercher",
          tabBarIcon: ({ color, size }) => (
            <MaterialIcons name="search" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="carte"
        options={{
          title: "Carte",
          tabBarIcon: ({ color, size }) => (
            <MaterialIcons name="map" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="methode"
        options={{
          title: "Méthode",
          tabBarIcon: ({ color, size }) => (
            <MaterialIcons name="menu-book" size={size} color={color} />
          ),
        }}
      />
    </Tabs>
  );
}
