import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { test } from "node:test";
import { runInThisContext } from "node:vm";
import * as jsx from "react/jsx-runtime";
import ts from "typescript";
import * as tokens from "../theme/tokens";

// Exécute le vrai écran, avec les frontières natives et le hook réseau simulés.
// Les éléments de FlatList sont développés pour inspecter le contenu visible.
const source = ts.transpileModule(
  readFileSync(join(__dirname, "../../app/(tabs)/index.tsx"), "utf8"),
  { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX } },
).outputText;

type Element = { type: string; props: Record<string, any> };
function elements(value: any): Element[] {
  if (Array.isArray(value)) return value.flatMap(elements);
  if (!value || typeof value !== "object") return [];
  if (value.type === "Modal" && !value.props.visible) return [];
  const children = value.type === "FlatList"
    ? [value.props.ListHeaderComponent, value.props.data.length
      ? value.props.data.map((item: unknown) => value.props.renderItem({ item }))
      : value.props.ListEmptyComponent]
    : value.props.children;
  return [value, ...elements(children)];
}
function texte(arbre: Element[]) {
  return arbre.filter(e => e.type === "Text").map(e => e.props.children).join(" ");
}

function session() {
  const query = {
    data: undefined as any,
    isFetching: false, isError: true, isSuccess: false,
    isDebouncing: false, isPaused: false,
    refetch: () => { tentatives++; query.isFetching = true; },
  };
  let tentatives = 0;
  let q = "Paris";
  let stateIndex = 0;
  const dependencies: Record<string, unknown> = {
    "react/jsx-runtime": jsx,
    react: {
      useState: () => [[q, [], false, null][stateIndex++], () => {}],
      useCallback: (callback: unknown) => callback,
    },
    "react-native": {
      ...Object.fromEntries(["View", "Text", "TextInput", "FlatList", "Pressable",
        "ActivityIndicator", "Modal"].map(n => [n, n])),
      StyleSheet: { create: (styles: unknown) => styles }, Alert: {},
    },
    "expo-router": { useRouter: () => ({}), useFocusEffect: () => {} },
    "react-native-safe-area-context": { useSafeAreaInsets: () => ({ top: 0, bottom: 0 }) },
    "@expo/vector-icons": { MaterialIcons: "MaterialIcons" },
    "expo-location": {},
    "../../src/api/queries": { useSearch: () => query },
    "../../src/lib/indexCommunes": {},
    "../../src/lib/familles": {},
    "../../src/lib/recents": {},
    "../../src/theme/tokens": tokens,
  };
  const exports = {} as { default: () => unknown };
  runInThisContext(`(function(require, exports) { ${source}\n})`)(
    (name: string) => {
      assert.ok(name in dependencies, `Import inattendu : ${name}`);
      return dependencies[name];
    }, exports,
  );
  return {
    query,
    get tentatives() { return tentatives; },
    saisir(value: string) { q = value; },
    render() { stateIndex = 0; return elements(exports.default()); },
  };
}

test("accueil — échec sans cache, nouvelle tentative, puis résultats", () => {
  const s = session();
  let arbre = s.render();
  assert.match(texte(arbre), /Impossible de rechercher les communes/);
  assert.doesNotMatch(texte(arbre), /Aucune commune trouvée/);
  const bouton = arbre.find(e => e.type === "Pressable" &&
    texte(elements(e)).includes("Réessayer"));
  assert.ok(bouton, "Bouton Réessayer accessible");
  assert.equal(bouton.props.accessibilityRole, "button");
  bouton.props.onPress();
  assert.equal(s.tentatives, 1);
  arbre = s.render();
  assert.match(texte(arbre), /Recherche en cours/);
  assert.ok(arbre.some(e => e.type === "ActivityIndicator"));
  assert.doesNotMatch(texte(arbre), /Réessayer|Aucune commune trouvée/);

  Object.assign(s.query, { isFetching: false, isError: false, isSuccess: true,
    data: [{ code_insee: "75056", nom: "Paris", departement: "75" }] });
  arbre = s.render();
  assert.match(texte(arbre), /Paris/);
  assert.doesNotMatch(texte(arbre), /Impossible|Réessayer|Aucune commune|Recherche en cours/);
});

test("accueil — réponse vide réussie distincte d'une erreur", () => {
  const s = session();
  Object.assign(s.query, { data: [], isError: false, isSuccess: true });
  assert.match(texte(s.render()), /Aucune commune trouvée/);
  assert.doesNotMatch(texte(s.render()), /Impossible|Réessayer/);
});

test("accueil — pendant le debounce, masquer l'ancien état vide ou en erreur", () => {
  const s = session();
  for (const isError of [true, false]) {
    Object.assign(s.query, { data: [], isError, isSuccess: !isError, isDebouncing: true });
    assert.match(texte(s.render()), /Recherche en cours/);
    assert.doesNotMatch(texte(s.render()), /Aucune commune|Impossible|Réessayer/);
  }
});

test("accueil — réseau hors ligne : une requête suspendue affiche une explication", () => {
  const s = session();
  Object.assign(s.query, { isError: false, isPaused: true });
  assert.match(texte(s.render()), /connexion/);
  assert.match(texte(s.render()), /Réessayer/);
});

test("accueil — aucune erreur ni chargement pour une saisie de moins de deux caractères", () => {
  const s = session();
  for (const q of ["", "P", " P "]) {
    s.saisir(q);
    assert.doesNotMatch(texte(s.render()), /Impossible|Réessayer|Aucune commune|Recherche en cours/);
  }
});
