/**
 * Tests Node (`npm test`) de la configuration de release EAS (`mobile/eas.json`).
 *
 * Verrouille les décisions de juillet 2026 (doc Outline « Déploiement » et
 * sous-page « CI/CD ») :
 * - Android uniquement, 3 profils : development / preview / production ;
 * - PAS d'EAS Update (OTA) : aucun `channel` dans eas.json, pas d'`expo-updates`
 *   dans les dépendances, pas de bloc `updates` dans app.json — en production
 *   l'app ne doit contacter que data.cavotequoiici.fr ;
 * - la soumission automatique s'arrête en piste `internal` (la promotion vers
 *   test fermé puis production reste un clic humain) ;
 * - versionCode des builds store géré par EAS (`appVersionSource: remote` +
 *   `autoIncrement`) — le canal CI QA (EXPO_BUILD_NUMBER, cf. app.config.js)
 *   reste indépendant.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { test } from "node:test";

const MOBILE = join(__dirname, "../..");

const easJson = JSON.parse(readFileSync(join(MOBILE, "eas.json"), "utf-8"));
const appJson = JSON.parse(readFileSync(join(MOBILE, "app.json"), "utf-8"));
const packageJson = JSON.parse(
  readFileSync(join(MOBILE, "package.json"), "utf-8"),
);

/** Toutes les clés présentes dans un objet JSON, récursivement. */
function clesRecursives(valeur: unknown): string[] {
  if (Array.isArray(valeur)) return valeur.flatMap(clesRecursives);
  if (valeur === null || typeof valeur !== "object") return [];
  return Object.entries(valeur).flatMap(([cle, v]) => [
    cle,
    ...clesRecursives(v),
  ]);
}

test("eas.json — les trois profils de build existent", () => {
  assert.deepEqual(Object.keys(easJson.build).sort(), [
    "development",
    "preview",
    "production",
  ]);
});

test("eas.json — development : dev client, distribution interne, APK", () => {
  const dev = easJson.build.development;
  assert.equal(dev.developmentClient, true);
  assert.equal(dev.distribution, "internal");
  assert.equal(dev.android?.buildType, "apk");
});

test("eas.json — preview : distribution interne, APK, sans dev client", () => {
  const preview = easJson.build.preview;
  assert.equal(preview.distribution, "internal");
  assert.equal(preview.android?.buildType, "apk");
  assert.equal(preview.developmentClient, undefined);
});

test("eas.json — preview et production embarquent EXPO_PUBLIC_DATA_URL", () => {
  // La variable est inlinée au build Metro et mobile/.env est gitignoré (donc
  // absent des archives envoyées à EAS Build) : sans elle dans le profil,
  // l'app sortirait du build avec BASE_URL vide (« Données non configurées »).
  // Le profil development est exempté : le dev client charge le JS depuis le
  // serveur Metro local, qui lit mobile/.env.
  const CDN = "https://data.cavotequoiici.fr";
  assert.equal(easJson.build.preview.env?.EXPO_PUBLIC_DATA_URL, CDN);
  assert.equal(easJson.build.production.env?.EXPO_PUBLIC_DATA_URL, CDN);
});

test("eas.json — production : .aab store, versionCode auto-incrémenté", () => {
  const production = easJson.build.production;
  assert.equal(production.autoIncrement, true);
  // Pas de `distribution: internal` ni de buildType APK : le profil production
  // doit produire l'artefact store par défaut (.aab).
  assert.equal(production.distribution, undefined);
  assert.equal(production.android?.buildType, undefined);
  assert.equal(production.developmentClient, undefined);
});

test("eas.json — versionCode store géré par EAS (appVersionSource remote)", () => {
  assert.equal(easJson.cli?.appVersionSource, "remote");
});

test("eas.json — la soumission s'arrête en piste interne (clic humain ensuite)", () => {
  assert.equal(easJson.submit?.production?.android?.track, "internal");
});

test("eas.json — aucun channel : EAS Update n'est pas utilisé", () => {
  assert.ok(!clesRecursives(easJson).includes("channel"));
});

test("pas d'OTA — expo-updates absent des dépendances", () => {
  const deps = {
    ...packageJson.dependencies,
    ...packageJson.devDependencies,
  };
  assert.ok(!("expo-updates" in deps));
});

test("pas d'OTA — app.json sans bloc updates ni runtimeVersion", () => {
  assert.equal(appJson.expo.updates, undefined);
  assert.equal(appJson.expo.runtimeVersion, undefined);
});
