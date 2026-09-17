import assert from "node:assert/strict";
import { test } from "node:test";
import * as jsx from "react/jsx-runtime";
import { creerChargeur, hooks } from "../../test-utils/components";
import * as tokens from "../theme/tokens";
import * as familles from "../lib/familles";
import * as blocs from "../lib/blocs";
import * as color from "../lib/color";

const charger = creerChargeur(__dirname);
const repartition = [
  { famille: "extreme_gauche", part: 0.25 }, { famille: "ecologistes", part: 0.3 },
  { famille: "extreme_droite", part: 0.2 }, { famille: "centre", part: 0.15 }, { famille: "divers", part: 0.1 },
];
const couleurs = ["#E84E6B", "#2D6FCB", "#FFB300", "#9AA0A6"];
const native = {
  ...Object.fromEntries(["View", "Text", "Pressable", "ScrollView", "ActivityIndicator"].map(n => [n, n])),
  StyleSheet: { create: (s: unknown) => s }, Alert: {},
};

test("blocs — barre de fiche et légende utilisent les teintes de référence", () => {
  const { RepartitionBar } = charger("RepartitionBar.tsx", {
    "react/jsx-runtime": jsx, "react-native": native, "../theme/tokens": tokens,
    "../lib/familles": familles, "../lib/blocs": blocs,
  });
  const arbre = hooks().render(() => RepartitionBar({ segments: blocs.agregerParBlocs(repartition), parBlocs: true }));
  const segments = arbre.filter(e => e.props.style?.flex && Object.keys(e.props.style).length === 2);
  assert.deepEqual(segments.map(e => e.props.style.backgroundColor), couleurs);
  const puces = arbre.filter(e => Array.isArray(e.props.style));
  assert.deepEqual(puces.map(e => e.props.style[1].backgroundColor), couleurs);
});

for (const algo of ["blocs", "tendance"]) {
  test(`blocs — partage ${algo} : fond servi et répartition adaptée`, () => {
    const h = hooks();
    const hex = "#CF7884";
    const { default: Partager } = charger("../../app/partager/[insee].tsx", {
      "react/jsx-runtime": jsx, react: h.react, "react-native": native,
      "expo-router": { useLocalSearchParams: () => ({ insee: "00001" }), useRouter: () => ({}) },
      "react-native-safe-area-context": { useSafeAreaInsets: () => ({ top: 0, bottom: 0 }) },
      "@expo/vector-icons": { MaterialIcons: "MaterialIcons" },
      "react-native-view-shot": {}, "expo-sharing": {},
      "../../src/theme/tokens": tokens, "../../src/lib/familles": familles,
      "../../src/lib/blocs": blocs, "../../src/lib/color": color,
      "../../src/api/queries": { useFiche: () => ({ data: { nom: "Exemple", couleur: {
        hex, algo, famille_dominante: "gauche", repartition, participation_mediane: 0.6,
      } } }) },
    });
    const arbre = h.render(Partager);
    assert.equal(arbre.find(e => e.props.collapsable === false)!.props.style[1].backgroundColor, hex);
    const segments = arbre.filter(e => e.props.style?.flex && Object.keys(e.props.style).length === 2);
    assert.equal(segments.length, algo === "blocs" ? 4 : 5);
    if (algo === "blocs") assert.deepEqual(segments.map(e => e.props.style.backgroundColor), couleurs);
    else assert.equal(segments[0].props.style.backgroundColor, familles.FAMILLES.ecologistes.hex);
  });
}

test("blocs — la fiche transmet la couleur servie et le mode blocs à sa barre", () => {
  const h = hooks();
  const hex = "#CF7884";
  const { default: Fiche } = charger("../../app/commune/[insee].tsx", {
    "react/jsx-runtime": jsx, react: h.react, "react-native": native,
    "expo-router": { useLocalSearchParams: () => ({ insee: "00001" }), useRouter: () => ({}) },
    "react-native-safe-area-context": { useSafeAreaInsets: () => ({ top: 0, bottom: 0 }) },
    "../../src/theme/tokens": tokens, "../../src/lib/familles": familles,
    "../../src/lib/blocs": blocs, "../../src/lib/color": color,
    "../../src/lib/algo": { useAlgo: () => ({ algo: "blocs" }), ALGOS: [{ id: "blocs", label: "Par blocs" }] },
    "../../src/lib/recents": {}, "../../src/lib/cadrage": {},
    ...Object.fromEntries(["ColorHero", "StatCard", "RepartitionBar", "TransparenceEncart"].map(n => [`../../src/components/${n}`, { [n]: n }])),
    "../../src/api/queries": {
      useFiche: () => ({ data: { nom: "Exemple", code_insee: "00001", couleur: {
        hex, algo: "blocs", famille_dominante: "gauche", repartition,
        participation_mediane: 0.6, scrutins_inclus: [],
      } } }), useScrutins: () => ({}),
    },
  });
  const arbre = h.render(Fiche);
  const hero = arbre.find(e => e.type === "ColorHero")!;
  assert.equal(hero.props.hex, hex);
  assert.equal(hero.props.tendance, "Gauche");
  const barre = arbre.find(e => e.type === "RepartitionBar")!;
  assert.equal(barre.props.parBlocs, true);
  assert.deepEqual(barre.props.segments, blocs.agregerParBlocs(repartition));
});
