import { Tabs } from "expo-router";
import { MaterialIcons } from "@expo/vector-icons";

import { colors, type } from "../../src/theme/tokens";

/**
 * Barre d'onglets persistante (cf. maquettes) : Rechercher · Carte · Méthode ·
 * Paramètres. Fiche commune (poussée) et Partager (modale) ne sont pas des
 * onglets.
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
        tabBarLabelStyle: { fontSize: 11, ...type.label },
        // La barre d'onglets a une hauteur quasi fixe : en grande police système,
        // « Rechercher »/« Méthode » tronquent. Les labels restent à ×1 (les
        // icônes + l'ordre suffisent à l'identification).
        tabBarAllowFontScaling: false,
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
      <Tabs.Screen
        name="parametres"
        options={{
          title: "Paramètres",
          tabBarIcon: ({ color, size }) => (
            <MaterialIcons name="tune" size={size} color={color} />
          ),
        }}
      />
    </Tabs>
  );
}
