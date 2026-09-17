import assert from "node:assert/strict";
import { test } from "node:test";
import "./test-globals";
import { creerChargeur } from "../../test-utils/components";
import * as versionDonnees from "../lib/versionDonnees";

const charger = creerChargeur(__dirname);

test("données — fiches, index, version et PMTiles utilisent la même révision HTTP", async t => {
  const avant = process.env.EXPO_PUBLIC_DATA_URL;
  process.env.EXPO_PUBLIC_DATA_URL = "https://data.example.test";
  t.after(() => {
    if (avant === undefined) delete process.env.EXPO_PUBLIC_DATA_URL;
    else process.env.EXPO_PUBLIC_DATA_URL = avant;
  });
  const urls: unknown[] = [];
  t.mock.method(globalThis, "fetch", async (url: unknown) => {
    urls.push(url); return { ok: true, json: async () => ({}) };
  });
  const client = charger("client.ts", { "../lib/versionDonnees": versionDonnees });
  await client.api.ficheStatique("06088");
  await client.get("/index/communes.json");
  await client.get("/meta/version.json");
  assert.deepEqual(urls, ["communes/06088.json", "index/communes.json", "meta/version.json"]
    .map(p => `https://data.example.test/${p}?palette_blocs=2`));
  const tiles = charger("../lib/tiles.ts", { "../api/client": client, "./versionDonnees": versionDonnees });
  assert.equal(tiles.TUILES_COMMUNES_URL, "pmtiles://https://data.example.test/tiles/communes.pmtiles?palette_blocs=2");
});
