import assert from "node:assert/strict";
import { afterEach, beforeEach, mock, test } from "node:test";
import * as jsx from "react/jsx-runtime";
import * as tokens from "../theme/tokens";
import * as versionDonnees from "../lib/versionDonnees";
import * as territoires from "../lib/territoires";
import { creerChargeur, hooks, type Element } from "../../test-utils/components";

beforeEach(() => { mock.timers.enable({ apis: ["setTimeout"] }); });
afterEach(() => { mock.timers.reset(); });

const charger = creerChargeur(__dirname);
const tiles = charger("../lib/tiles.ts", { "./versionDonnees": versionDonnees, "../api/client": { DATA_BASE: "" } });
const exploration = { center: [1.25, 47.8], zoom: 6.75, bearing: 32, pitch: 20 };
const paris = { code_insee: "75056", nom: "Paris", lon: 2.35, lat: 48.85 };
function session() {
  const memoire = charger("../lib/cadrage.ts", {});
  const native = {
    ...Object.fromEntries(["View", "Text", "ScrollView", "Pressable", "ActivityIndicator"].map(n => [n, n])),
    StyleSheet: { create: (s: unknown) => s }, Alert: {},
  };
  let recents = [paris];
  let resolveRecents: ((value: typeof recents) => void) | undefined;
  let retarder = false;
  const vols: any[] = [];
  let carteHooks: ReturnType<typeof hooks>;
  let mapHooks: ReturnType<typeof hooks>;
  let Carte: () => unknown;
  let Map: ((props: object) => unknown) | undefined;
  let props: any;
  let arbre: Element[];
  const s = {
    memoire, vols,
    set recents(value: typeof recents) { recents = value; },
    retarder() { retarder = true; },
    async resoudre() { resolveRecents!(recents); await Promise.resolve(); },
    monterEcran() {
      carteHooks = hooks();
      Carte = charger("../../app/(tabs)/carte.tsx", {
        "react/jsx-runtime": jsx, react: carteHooks.react, "react-native": native,
        "expo-router": { useFocusEffect: carteHooks.useFocusEffect },
        "react-native-safe-area-context": { useSafeAreaInsets: () => ({ top: 0, bottom: 0 }) },
        "../../src/theme/tokens": tokens,
        "../../src/components/CommunesMap": { CommunesMap: "CommunesMap" },
        "../../src/lib/tiles": tiles,
        "../../src/lib/algo": { useAlgo: () => ({ algo: "tendance" }) },
        "../../src/lib/recents": { getRecents: () => retarder ? new Promise(r => { resolveRecents = r; }) : Promise.resolve(structuredClone(recents)) },
        "../../src/lib/territoires": territoires, "../../src/lib/cadrage": memoire,
      }).default;
      s.render();
    },
    monterCarte() {
      mapHooks = hooks();
      Map = charger("CommunesMap.native.tsx", {
        "react/jsx-runtime": jsx, react: mapHooks.react, "react-native": native,
        "expo-router": { router: {} }, "@expo/vector-icons": { MaterialIcons: "MaterialIcons" },
        "expo-location": {}, "@maplibre/maplibre-react-native": {
          Map: "Map", Camera: "Camera", Layer: "Layer", VectorSource: "VectorSource",
        },
        "../theme/tokens": tokens, "../api/client": { DATA_BASE: "" },
        "../lib/territoires": territoires, "../lib/tiles": tiles, "../lib/cadrage": memoire,
      }).CommunesMap;
      s.renderCarte();
    },
    render() {
      arbre = carteHooks.render(Carte);
      props = arbre.find(e => e.type === "CommunesMap")!.props;
      carteHooks.flush();
      if (Map) s.renderCarte();
    },
    renderCarte() {
      const a = mapHooks.render(() => Map!(props));
      a.find(e => e.type === "Camera")!.props.ref.current = { flyTo: (v: unknown) => vols.push(v) };
      mapHooks.flush(); return a;
    },
    async focus() { await carteHooks.focus(); s.render(); },
    blur() { carteHooks.blur(); },
    bouger(fin = true, vue: object = exploration) {
      s.renderCarte().find(e => e.type === "Map")!.props[
        fin ? "onRegionDidChange" : "onRegionIsChanging"
      ]?.({ nativeEvent: vue });
    },
    couche() {
      arbre.filter(e => e.type === "Pressable")[1].props.onPress(); s.render();
    },
    territoire() {
      arbre.filter(e => e.type === "Pressable")[tiles.COUCHES_COULEUR.length + 1].props.onPress(); s.render();
    },
  };
  s.monterEcran(); return s;
}

test("cadrage — retour Paramètres conserve le panoramique et le zoom", async () => {
  const s = session(); await s.focus(); s.monterCarte(); s.bouger(); s.vols.length = 0;
  s.blur(); await s.focus(); assert.deepEqual(s.vols, []);
});
for (const fin of [true, false]) {
  test(`cadrage — remontage restaure la vue ${fin ? "arrêtée" : "en mouvement"}`, async () => {
    const s = session(); await s.focus(); s.monterCarte(); s.bouger(fin); s.blur();
    s.monterEcran(); s.monterCarte(); s.vols.length = 0; await s.focus();
    assert.deepEqual(s.renderCarte().find(e => e.type === "Camera")!.props.initialViewState, exploration);
    assert.deepEqual(s.vols, []);
  });
}
test("cadrage — territoire rejouable, mais pas au remontage", async () => {
  const s = session(); await s.focus(); s.monterCarte(); s.vols.length = 0;
  s.territoire(); s.territoire(); assert.equal(s.vols.length, 2);
  assert.deepEqual(s.vols[0].center, territoires.TERRITOIRES[1].centre);
  assert.equal(s.vols[0].zoom, territoires.TERRITOIRES[1].zoom);
  s.bouger(); s.vols.length = 0; s.monterCarte(); assert.deepEqual(s.vols, []);
});
test("cadrage — nouvelle sélection, même identique, recentre une fois", async () => {
  const s = session(); await s.focus(); s.monterCarte(); s.bouger(); s.vols.length = 0;
  assert.equal(typeof s.memoire.demanderCadrage, "function");
  for (let i = 0; i < 2; i++) {
    s.blur(); s.memoire.demanderCadrage([7.26, 43.7], 11); await s.focus();
    assert.deepEqual(s.vols.at(-1).center, [7.26, 43.7]); assert.equal(s.vols.at(-1).zoom, 11);
  }
  assert.equal(s.vols.length, 2);
});
test("cadrage — historique tardif ne remplace pas un territoire choisi", async () => {
  const s = session(); s.retarder(); s.monterCarte(); await s.focus();
  s.territoire(); s.vols.length = 0; await s.resoudre(); s.render(); assert.deepEqual(s.vols, []);
});
test("cadrage — premier accès sans historique : métropole", async () => {
  const s = session(); s.recents = []; await s.focus(); s.monterCarte();
  assert.deepEqual(s.renderCarte().find(e => e.type === "Camera")!.props.initialViewState,
    { center: territoires.CENTRE_FRANCE, zoom: territoires.ZOOM_METROPOLE });
  assert.deepEqual(s.vols, []);
});

test("cadrage — fiche chargée : une demande par visite, aucune au changement d'algo", () => {
  const demandes: unknown[] = [];
  let insee = paris.code_insee;
  const fiche = { isLoading: true, data: undefined as any };
  let h = hooks();
  const Fiche = charger("../../app/commune/[insee].tsx", {
    "react/jsx-runtime": jsx,
    react: { useRef: (v: unknown) => h.react.useRef(v), useEffect: (f: () => void, d: any[]) => h.react.useEffect(f, d) },
    "react-native": { View: "View", ActivityIndicator: "ActivityIndicator", StyleSheet: { create: (v: unknown) => v } },
    "expo-router": { useLocalSearchParams: () => ({ insee }), useRouter: () => ({}) },
    "react-native-safe-area-context": { useSafeAreaInsets: () => ({ top: 0, bottom: 0 }) },
    "../../src/api/queries": { useFiche: () => fiche, useScrutins: () => ({}) },
    ...Object.fromEntries(["ColorHero", "StatCard", "RepartitionBar", "TransparenceEncart"].map(n => [`../../src/components/${n}`, {}])),
    "../../src/lib/algo": { useAlgo: () => ({ algo: "tendance" }) },
    "../../src/lib/blocs": {}, "../../src/lib/familles": {}, "../../src/lib/color": {},
    "../../src/lib/cadrage": { ZOOM_COMMUNE: 11, demanderCadrage: (...args: unknown[]) => demandes.push(args) },
    "../../src/lib/recents": { addRecent: () => {} }, "../../src/theme/tokens": tokens,
  }).default;
  const render = () => { h.render(Fiche); h.flush(); };
  render(); assert.equal(demandes.length, 0);
  fiche.data = { ...paris, couleur: { repartition: [] } };
  render(); assert.deepEqual(demandes, [[[paris.lon, paris.lat], 11]]);
  fiche.data = { ...fiche.data, couleur: { hex: "#123456", repartition: [] } };
  render(); assert.equal(demandes.length, 1);
  h = hooks(); render(); assert.equal(demandes.length, 2);
  insee = "06088";
  render(); assert.equal(demandes.length, 2, "Anciennes données ignorées pendant une nouvelle navigation");
  fiche.data = { ...fiche.data, code_insee: insee, lon: 7.26, lat: 43.7 };
  render(); assert.deepEqual(demandes.at(-1), [[7.26, 43.7], 11]);
});

test("cadrage — réponse d'historique après sortie ignorée", async () => {
  const s = session(); s.retarder(); s.monterCarte(); await s.focus(); s.blur();
  await s.resoudre(); s.render(); assert.deepEqual(s.vols, []);
  assert.equal(s.memoire.sessionCarte.cible, undefined);
});

test("cadrage — changement de couche ne déplace pas la caméra", async () => {
  const s = session(); await s.focus(); s.monterCarte(); s.bouger(); s.vols.length = 0;
  s.couche(); assert.deepEqual(s.vols, []);
});

for (const fin of [true, false]) {
  test(`cadrage — événement ${fin ? "final" : "en mouvement"} sans orientation : centre et zoom restaurés`, async () => {
    const s = session(); s.recents = []; await s.focus(); s.monterCarte();
    const vue = { center: [7.26, 43.7], zoom: 8.25 };
    s.bouger(fin, vue); s.monterCarte();
    assert.deepEqual(s.renderCarte().find(e => e.type === "Camera")!.props.initialViewState,
      { ...vue, bearing: 0, pitch: 0 });
  });
}

for (const champ of ["bearing", "pitch"] as const) {
  test(`cadrage — ${champ} absent ou invalide conserve sa dernière valeur connue`, async () => {
    const s = session(); await s.focus(); s.monterCarte();
    for (const valeur of [undefined, null, NaN, Infinity, -Infinity, "12"]) {
      s.bouger();
      const vue = { center: [7.26, 43.7], zoom: 8.25, bearing: 12, pitch: 5, [champ]: valeur };
      s.bouger(true, vue); s.monterCarte();
      assert.deepEqual(s.renderCarte().find(e => e.type === "Camera")!.props.initialViewState,
        { ...vue, [champ]: exploration[champ] });
    }
    // Zéro est une orientation valide, pas une valeur manquante.
    s.bouger(true, { ...exploration, bearing: 0, pitch: 0 }); s.monterCarte();
    assert.deepEqual(s.renderCarte().find(e => e.type === "Camera")!.props.initialViewState,
      { ...exploration, bearing: 0, pitch: 0 });
  });
}

test("cadrage — événement vide, centre ou zoom invalide ne remplace pas la dernière vue valide", async () => {
  const s = session(); await s.focus(); s.monterCarte(); s.bouger();
  for (const vue of [
    {}, { center: undefined }, { center: null }, { center: [] }, { center: [7.26] },
    { center: [7.26, 43.7], zoom: undefined },
    { center: [NaN, 43.7], zoom: 8 }, { center: [7.26, Infinity], zoom: 8 },
    { center: [7.26, 43.7], zoom: NaN }, { center: [7.26, 43.7], zoom: Infinity },
  ]) {
    s.bouger(true, vue); s.monterCarte();
    assert.deepEqual(s.renderCarte().find(e => e.type === "Camera")!.props.initialViewState, exploration);
  }
});
