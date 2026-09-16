import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { test } from "node:test";
import { runInThisContext } from "node:vm";
import ts from "typescript";

import type { IndexCommunes } from "../api/types-statiques";
import * as types from "../api/types";
import * as recherche from "./recherche";

const FICHIER_INDEX = "index-communes.json";
const FICHIER_VERSION = "index-communes.version.txt";
const paris: IndexCommunes = {
  algos: [...types.ALGOS],
  familles: ["gauche"],
  communes: [["75056", "Paris", "75", 48.85, 2.35,
    ["#123456", "#123456", "#123456"], [0, 0, 0]]],
};
const nouveau: IndexCommunes = {
  ...paris,
  communes: [...paris.communes, ["06088", "Nice", "06", 43.7, 7.27,
    ["#654321", "#654321", "#654321"], [null, null, null]]],
};
const panne = new Error("Connexion interrompue");

// Charge le vrai module dans une session neuve, sans runtime natif Expo.
// Seules ses frontières réseau/disque sont simulées ; recherche.ts reste réel.
const source = ts.transpileModule(
  readFileSync(join(__dirname, "indexCommunes.ts"), "utf8"),
  { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } },
).outputText;

function session(cache?: unknown, version = "v1") {
  const fichiers = new Map<string, string>();
  if (cache !== undefined) {
    fichiers.set(FICHIER_INDEX, JSON.stringify(cache));
    fichiers.set(FICHIER_VERSION, version);
  }
  const appels: string[] = [];
  const ecritures: string[] = [];
  const reseau = {
    version: "v2" as string | Error,
    index: nouveau as unknown,
    disqueIndisponible: false,
  };
  class File {
    constructor(_racine: unknown, private nom: string) {}
    get exists() { return fichiers.has(this.nom); }
    textSync() { return fichiers.get(this.nom)!; }
    write(contenu: string) {
      if (reseau.disqueIndisponible) throw new Error("Disque plein");
      ecritures.push(this.nom);
      fichiers.set(this.nom, contenu);
    }
  }
  const exports = {} as typeof import("./indexCommunes");
  const dependances: Record<string, unknown> = {
    "expo-file-system": { File, Paths: { cache: "cache" } },
    "../api/types": types,
    "../api/client": {
      get: async (path: string) => {
        appels.push(path);
        const valeur = path === "/meta/version.json"
          ? reseau.version instanceof Error ? reseau.version : { genere_le: reseau.version }
          : reseau.index;
        if (valeur instanceof Error) throw valeur;
        return valeur;
      },
    },
    "./recherche": recherche,
  };
  runInThisContext(`(function(require, exports) { ${source}\n})`)(
    (nom: string) => {
      assert.ok(nom in dependances, `Import inattendu : ${nom}`);
      return dependances[nom];
    }, exports,
  );
  return { api: exports, fichiers, appels, ecritures, reseau };
}

test("index — panne du nouvel index : recherche et proximité utilisent le cache, puis réessaient", async () => {
  const s = session(paris);
  s.reseau.index = panne;
  const avant = new Map(s.fichiers);
  const [resultats, proches] = await Promise.all([
    s.api.rechercherCommunes("Paris", "complet"),
    s.api.suggererCommunesProches(48.85, 2.35),
  ]);
  assert.equal(resultats[0].code_insee, "75056");
  assert.equal(proches[0].code_insee, "75056");
  assert.deepEqual(s.appels, ["/meta/version.json", "/index/communes.json"]);
  assert.deepEqual(s.fichiers, avant);
  assert.deepEqual(s.ecritures, []);

  s.reseau.index = nouveau;
  assert.equal((await s.api.rechercherCommunes("Nice", "complet"))[0].code_insee, "06088");
  assert.equal(s.fichiers.get(FICHIER_VERSION), "v2");
  assert.deepEqual(JSON.parse(s.fichiers.get(FICHIER_INDEX)!), nouveau);
  assert.deepEqual(s.ecritures, [FICHIER_INDEX, FICHIER_VERSION]);
  assert.equal(s.appels.length, 4);
  // Une mise à jour réussie reste memoïsée pour la session.
  s.reseau.version = panne;
  await s.api.rechercherCommunes("Paris", "complet");
  assert.equal(s.appels.length, 4);
});

test("index — métadonnées hors ligne : cache disponible et récupération ultérieure", async () => {
  const s = session(paris);
  s.reseau.version = panne;
  assert.equal((await s.api.rechercherCommunes("Paris", "complet"))[0].nom, "Paris");
  assert.deepEqual(s.appels, ["/meta/version.json"]);
  s.reseau.version = "v2";
  assert.equal((await s.api.rechercherCommunes("Nice", "complet"))[0].nom, "Nice");
});

test("index — version inchangée : aucun téléchargement d'index", async () => {
  const s = session(paris);
  s.reseau.version = "v1";
  await s.api.rechercherCommunes("Paris", "complet");
  await s.api.suggererCommunesProches(48.85, 2.35);
  assert.deepEqual(s.appels, ["/meta/version.json"]);
  assert.deepEqual(s.ecritures, []);
});

test("index — sans cache : erreur réseau propagée, puis nouvelle tentative réussie", async () => {
  const s = session();
  s.reseau.index = panne;
  await assert.rejects(s.api.rechercherCommunes("Paris", "complet"), (err) => err === panne);
  assert.equal(s.fichiers.size, 0);
  s.reseau.index = nouveau;
  assert.equal((await s.api.rechercherCommunes("Nice", "complet"))[0].nom, "Nice");
});

test("index — sans cache et métadonnées hors ligne : erreur explicite", async () => {
  const s = session();
  s.reseau.version = panne;
  await assert.rejects(s.api.rechercherCommunes("Paris", "complet"), /hors ligne, sans cache/);
  assert.equal(s.fichiers.size, 0);
});

for (const [nom, invalide] of Object.entries({
  "JSON tronqué": new SyntaxError("Unexpected end of JSON input"),
  "objet vide": {},
  "communes absentes": { ...paris, communes: null },
  "nom invalide": { ...paris, communes: [["75056", null, "75", 48.85, 2.35, [], []]] },
  "couleurs absentes": { ...paris, communes: [["75056", "Paris", "75", 48.85, 2.35, [], [0, 0, 0]]] },
  "famille hors légende": { ...paris, communes: [["75056", "Paris", "75", 48.85, 2.35,
    ["#123456", "#123456", "#123456"], [99, 0, 0]]] },
})) {
  test(`index — téléchargement invalide (${nom}) : préserver le cache et sa version`, async () => {
    const s = session(paris);
    const avant = new Map(s.fichiers);
    s.reseau.index = invalide;
    assert.equal((await s.api.rechercherCommunes("Paris", "complet"))[0].nom, "Paris");
    assert.deepEqual(s.fichiers, avant);
    assert.deepEqual(s.ecritures, []);
  });
}

for (const contenu of ["{", "{}", JSON.stringify({ ...paris, communes: [["75056"]] })]) {
  test(`index — cache corrompu (${contenu}) : retéléchargement même à version égale`, async () => {
    const s = session(paris);
    s.fichiers.set(FICHIER_INDEX, contenu);
    s.reseau.version = "v1";
    assert.equal((await s.api.rechercherCommunes("Nice", "complet"))[0].nom, "Nice");
    assert.deepEqual(s.appels, ["/meta/version.json", "/index/communes.json"]);
  });
}

test("index — cache invalide et téléchargement invalide : aucune version enregistrée", async () => {
  const s = session({});
  const avant = new Map(s.fichiers);
  s.reseau.index = {};
  await assert.rejects(s.api.rechercherCommunes("Paris", "complet"));
  assert.deepEqual(s.fichiers, avant);
});

test("index — disque indisponible : le téléchargement reste utilisable en mémoire", async () => {
  const s = session();
  s.reseau.disqueIndisponible = true;
  assert.equal((await s.api.rechercherCommunes("Nice", "complet"))[0].nom, "Nice");
  await s.api.rechercherCommunes("Paris", "complet");
  assert.equal(s.appels.length, 2);
});
