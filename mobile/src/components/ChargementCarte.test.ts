import assert from "node:assert/strict";
import { test } from "node:test";
import * as jsx from "react/jsx-runtime";
import { creerChargeur, hooks, type Element } from "../../test-utils/components";
import * as tokens from "../theme/tokens";
import * as territoires from "../lib/territoires";

const charger = creerChargeur(__dirname);
const vue = { center: [2.4, 46.6], zoom: 6.5, bearing: 12, pitch: 20 };
function session() {
  const h = hooks();
  const memoire = charger("../lib/cadrage.ts", {});
  const vols: unknown[] = [];
  let cible: unknown;
  let arbre: Element[] = [];
  const { CommunesMap } = charger("CommunesMap.native.tsx", {
    "react/jsx-runtime": jsx, react: h.react,
    "react-native": {
      ...Object.fromEntries(["View", "Text", "Pressable", "ActivityIndicator"].map(n => [n, n])),
      StyleSheet: { create: (v: unknown) => v }, Alert: {},
    },
    "expo-router": { router: {} }, "@expo/vector-icons": { MaterialIcons: "MaterialIcons" },
    "expo-location": {}, "@maplibre/maplibre-react-native": {
      Map: "Map", Camera: "Camera", Layer: "Layer", VectorSource: "VectorSource",
    },
    "../theme/tokens": tokens, "../api/client": { DATA_BASE: "https://data.example.test" },
    "../lib/territoires": territoires, "../lib/cadrage": memoire,
    "../lib/tiles": charger("../lib/tiles.ts", { "../api/client": { DATA_BASE: "https://data.example.test" } }),
  });
  const s = {
    vols,
    unmount: h.unmount,
    render() {
      arbre = h.render(() => CommunesMap({ cible }));
      arbre.find(e => e.type === "Camera")!.props.ref.current = { flyTo: (v: unknown) => vols.push(v) };
      h.flush();
      arbre = h.render(() => CommunesMap({ cible }));
      return arbre;
    },
    get map() { return arbre.find(e => e.type === "Map")!; },
    get camera() { return arbre.find(e => e.type === "Camera")!; },
    texte() { return arbre.filter(e => e.type === "Text").map(e => e.props.children).join(" "); },
    evenement(nom: string, nativeEvent: unknown = null) {
      s.map.props[nom]?.({ nativeEvent }); s.render();
    },
    territoire() { cible = memoire.demanderCadrage(territoires.CENTRE_FRANCE, territoires.ZOOM_METROPOLE); s.render(); },
    reessayer() {
      const bouton = arbre.find(e => e.type === "Pressable" && e.props.accessibilityLabel === "Réessayer le chargement de la carte");
      assert.ok(bouton, "Action Réessayer accessible"); bouton.props.onPress(); s.render();
    },
  };
  s.render(); return s;
}

test("chargement — visible initialement jusqu'au rendu complet, pas seulement au style chargé", t => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const s = session(); assert.match(s.texte(), /Chargement de la carte/);
  s.evenement("onDidFinishLoadingMap"); s.evenement("onDidFinishLoadingStyle");
  assert.match(s.texte(), /Chargement de la carte/);
  s.evenement("onDidFinishRenderingFrame"); assert.match(s.texte(), /Chargement de la carte/);
  s.evenement("onDidFinishRenderingFrameFully"); assert.equal(s.texte(), "");
  t.mock.timers.tick(60_000); s.render(); assert.equal(s.texte(), "");
});

for (const completAvantArret of [false, true]) {
  test(`chargement — territoire, rendu complet ${completAvantArret ? "avant" : "après"} l'arrêt de caméra`, t => {
    t.mock.timers.enable({ apis: ["setTimeout"] });
    const s = session(); s.evenement("onDidFinishRenderingFrameFully");
    s.territoire(); assert.match(s.texte(), /Chargement de la carte/);
    assert.equal(s.vols.length, 1);
    s.evenement("onRegionWillChange", vue);
    if (completAvantArret) s.evenement("onDidFinishRenderingFrameFully");
    else s.evenement("onDidFinishRenderingFrame");
    assert.match(s.texte(), /Chargement de la carte/);
    s.evenement("onRegionDidChange", vue);
    if (!completAvantArret) {
      assert.match(s.texte(), /Chargement de la carte/);
      s.evenement("onDidFinishRenderingFrameFully");
    }
    assert.equal(s.texte(), "");
  });
}

test("chargement — rendu incomplet après un panoramique puis récupération", t => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const s = session(); s.evenement("onDidFinishRenderingFrameFully");
  s.evenement("onRegionWillChange", vue); s.evenement("onDidFinishRenderingFrameFully");
  s.evenement("onDidFinishRenderingFrame"); s.evenement("onRegionDidChange", vue);
  assert.match(s.texte(), /Chargement de la carte/);
  s.evenement("onDidFinishRenderingMapFully"); assert.equal(s.texte(), "");
});

test("chargement — attente prolongée bornée malgré des rendus partiels répétés, puis récupération tardive", t => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const s = session();
  for (let i = 0; i < 30; i++) { s.evenement("onDidFinishRenderingFrame"); t.mock.timers.tick(1000); }
  s.render(); assert.match(s.texte(), /plus de temps que prévu/); assert.match(s.texte(), /Réessayer/);
  assert.ok(!s.render().some(e => e.type === "ActivityIndicator"));
  s.evenement("onDidFinishRenderingFrameFully"); assert.equal(s.texte(), "");
});

test("chargement — erreur native persistante, nouvelle tentative au même cadrage et événements obsolètes ignorés", t => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const s = session(); s.evenement("onRegionDidChange", vue);
  const ancienneCarte = s.map;
  s.evenement("onDidFailLoadingMap"); assert.match(s.texte(), /Impossible de charger la carte/);
  s.evenement("onDidFinishRenderingFrameFully"); assert.match(s.texte(), /Impossible de charger la carte/);
  s.reessayer(); assert.match(s.texte(), /Chargement de la carte/);
  assert.notEqual((s.map as any).key, (ancienneCarte as any).key, "Vue native et sources recréées");
  assert.deepEqual(s.camera.props.initialViewState, vue);
  ancienneCarte.props.onDidFailLoadingMap?.(); ancienneCarte.props.onDidFinishRenderingFrameFully?.();
  s.render(); assert.match(s.texte(), /Chargement de la carte/);
  s.evenement("onDidFinishRenderingFrameFully"); assert.equal(s.texte(), "");
  assert.equal(s.vols.length, 0, "Aucune ancienne commande de cadrage rejouée");
});


test("chargement — territoire à cache chaud, aucun indicateur résiduel", t => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const s = session(); s.evenement("onDidFinishRenderingMapFully");
  s.territoire(); s.evenement("onRegionWillChange", vue);
  s.evenement("onDidFinishRenderingMapFully"); s.evenement("onRegionDidChange", vue);
  t.mock.timers.tick(60_000); s.render(); assert.equal(s.texte(), "");
});

test("chargement — chaque nouvelle tentative dispose de son propre délai", t => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const s = session();
  t.mock.timers.tick(19_000); s.evenement("onDidFailLoadingMap"); s.reessayer();
  t.mock.timers.tick(2_000); s.render(); assert.match(s.texte(), /Chargement de la carte/);
  t.mock.timers.tick(18_000); s.render(); assert.match(s.texte(), /plus de temps que prévu/);
  s.reessayer(); assert.match(s.texte(), /Chargement de la carte/);
  s.evenement("onDidFinishRenderingFrameFully"); assert.equal(s.texte(), "");
});

test("chargement — démontage annule le délai et ignore les événements natifs tardifs", t => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const annulations = t.mock.method(globalThis, "clearTimeout");
  const s = session(); s.unmount();
  assert.equal(annulations.mock.callCount(), 1);
  t.mock.timers.tick(60_000);
  s.evenement("onDidFailLoadingMap"); s.evenement("onDidFinishRenderingFrameFully");
  assert.match(s.texte(), /Chargement de la carte/, "Aucun changement d'état après démontage");
});
