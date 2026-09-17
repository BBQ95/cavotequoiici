import assert from "node:assert/strict";
import { test } from "node:test";
import * as jsx from "react/jsx-runtime";
import * as tokens from "../theme/tokens";

import { creerChargeur, hooks } from "../../test-utils/components";

const charger = creerChargeur(__dirname);
const feature = (insee: unknown) => ({ properties: { insee } });
const point = [120, 240];
const lngLat = [2.35, 48.85];

function session({ glyphs = true } = {}) {
  const queries: { point: unknown; layers: string[] }[] = [];
  const routes: string[] = [];
  const vols: any[] = [];
  const s = {
    etiquettes: [] as ReturnType<typeof feature>[],
    polygones: [] as ReturnType<typeof feature>[],
    erreur: "",
    zoom: 9,
  };
  const map = {
    async queryRenderedFeatures(point: unknown, { layers }: { layers: string[] }) {
      queries.push({ point, layers });
      if (s.erreur === layers[0]) throw new Error("Interrogation native échouée");
      return layers[0] === "communes-etiquettes" ? s.etiquettes : s.polygones;
    },
    async getViewState() {
      if (s.erreur === "camera") throw new Error("Caméra indisponible");
      return { zoom: s.zoom };
    },
  };
  const h = hooks();
  const dependencies: Record<string, unknown> = {
    "react/jsx-runtime": jsx,
    react: h.react,
    "react-native": {
      ...Object.fromEntries(["View", "Pressable", "ActivityIndicator"].map(n => [n, n])),
      StyleSheet: { create: (styles: unknown) => styles }, Alert: {},
    },
    "expo-router": { router: { push: (route: string) => routes.push(route) } },
    "@expo/vector-icons": { MaterialIcons: "MaterialIcons" },
    "expo-location": {},
    "@maplibre/maplibre-react-native": {
      Map: "Map", Camera: "Camera", Layer: "Layer", VectorSource: "VectorSource",
    },
    "../theme/tokens": tokens,
    "../api/client": { DATA_BASE: glyphs ? "https://data.example.test" : "" },
    "../lib/territoires": { CENTRE_FRANCE: [2, 47], ZOOM_METROPOLE: 5 },
    "../lib/cadrage": charger("../lib/cadrage.ts", {}),
    "../lib/tiles": {
      FONTSTACK_ETIQUETTES: "Noto Sans Medium", SOURCE_LAYER_COMMUNES: "communes",
      SOURCE_LAYER_ETIQUETTES: "etiquettes", TUILES_COMMUNES_URL: "pmtiles://test",
      TUILES_MINZOOM: 4, TUILES_MAXZOOM: 11,
    },
  };
  const { CommunesMap } = charger("CommunesMap.native.tsx", dependencies);
  const arbre = h.render(() => CommunesMap({}));
  const carte = arbre.find(e => e.type === "Map")!;
  if (carte.props.ref) carte.props.ref.current = map;
  arbre.find(e => e.type === "Camera")!.props.ref.current = {
    flyTo: (options: unknown) => vols.push(options),
  };
  h.flush();
  return {
    s, queries, routes, vols, arbre,
    detach() { carte.props.ref.current = null; },
    async tap() {
      assert.equal(typeof carte.props.onPress, "function", "Gestionnaire unique sur Map");
      await carte.props.onPress({ nativeEvent: { point, lngLat } });
    },
  };
}

test("carte — étiquette touchée prioritaire sur la commune sous son texte", async () => {
  const s = session();
  s.s.etiquettes = [feature("75056")];
  s.s.polygones = [feature("93066")];
  await s.tap();
  assert.deepEqual(s.routes, ["/commune/75056"]);
  assert.deepEqual(s.queries, [{ point, layers: ["communes-etiquettes"] }]);
  assert.equal(s.arbre.find(e => e.type === "VectorSource")!.props.onPress, undefined);
});

test("carte — sans étiquette, seul le remplissage au point exact est interrogé", async () => {
  const s = session();
  s.s.polygones = [feature("01001")];
  await s.tap();
  assert.deepEqual(s.queries, [
    { point, layers: ["communes-etiquettes"] }, { point, layers: ["communes-fill"] },
  ]);
  assert.deepEqual(s.routes, ["/commune/01001"]);
});

for (const couche of ["etiquettes", "polygones"] as const) {
  test(`carte — doublons de ${couche} dédupliqués par INSEE`, async () => {
    const s = session();
    s.s[couche] = [feature("2A004"), feature("2A004")];
    await s.tap();
    assert.deepEqual(s.routes, ["/commune/2A004"]);
    assert.deepEqual(s.vols, []);
  });

  test(`carte — plusieurs ${couche} : zoom au toucher sans choix arbitraire`, async () => {
    for (const zoom of [5, 12]) {
      const s = session();
      s.s.zoom = zoom;
      s.s[couche] = [feature("75056"), feature("93066"), feature("75056")];
      await s.tap();
      assert.deepEqual(s.routes, []);
      assert.equal(s.vols.length, 1);
      assert.deepEqual(s.vols[0].center, lngLat);
      assert.ok(s.vols[0].zoom > zoom);
      if (couche === "etiquettes") assert.equal(s.queries.length, 1);
    }
  });
}

test("carte — couche d'étiquettes absente : interroger directement le remplissage", async () => {
  const s = session({ glyphs: false });
  s.s.polygones = [feature("01001")];
  await s.tap();
  assert.deepEqual(s.queries, [{ point, layers: ["communes-fill"] }]);
  assert.deepEqual(s.routes, ["/commune/01001"]);
});

test("carte — résultats vides ou sans INSEE exploitable : aucune action", async () => {
  const s = session();
  for (const features of [[], [feature(null), feature(""), feature(123)]]) {
    s.s.etiquettes = features;
    s.s.polygones = features;
    await s.tap();
  }
  assert.deepEqual(s.routes, []);
  assert.deepEqual(s.vols, []);
});

for (const erreur of ["communes-etiquettes", "communes-fill", "camera"]) {
  test(`carte — erreur ${erreur} : aucune fiche, puis toucher suivant fonctionnel`, async () => {
    const s = session();
    s.s.erreur = erreur;
    s.s.polygones = [feature("75056"), feature("93066")];
    await s.tap();
    assert.deepEqual(s.routes, []);
    assert.deepEqual(s.vols, []);
    if (erreur === "communes-etiquettes") assert.equal(s.queries.length, 1);
    s.s.erreur = "";
    s.s.polygones = [feature("01001")];
    await s.tap();
    assert.deepEqual(s.routes, ["/commune/01001"]);
  });
}

test("carte — touchers simultanés : une seule navigation", async () => {
  const s = session();
  s.s.etiquettes = [feature("75056")];
  await Promise.all([s.tap(), s.tap()]);
  assert.deepEqual(s.routes, ["/commune/75056"]);
});

test("carte — réponse après démontage : aucune navigation", async () => {
  const s = session();
  s.s.etiquettes = [feature("75056")];
  const pending = s.tap();
  s.detach();
  await pending;
  assert.deepEqual(s.routes, []);
});
