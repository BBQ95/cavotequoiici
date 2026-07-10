/**
 * Tests Node (`npm test`) de la logique pure de recherche locale.
 *
 * La parité de `normaliserNom` avec `pipeline/normalisation.normaliser_nom`
 * est verrouillée par les fixtures générées côté backend
 * (`tests/fixtures/normalisation_parite.json`, gardées à jour par un test
 * Python) : si la normalisation évolue d'un côté, l'un des deux dépôts casse.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { test } from "node:test";

import type { EntreeIndex } from "../api/types-statiques";
import {
  distanceM,
  indexerEntree,
  normaliserNom,
  plusProche,
  rechercher,
} from "./recherche";

const FIXTURES = join(__dirname, "../../../tests/fixtures/normalisation_parite.json");

test("normaliserNom — parité avec pipeline.normalisation (fixtures backend)", () => {
  const { cas } = JSON.parse(readFileSync(FIXTURES, "utf-8")) as {
    cas: { entree: string; attendu: string }[];
  };
  assert.ok(cas.length >= 10, "fixtures anormalement courtes");
  for (const { entree, attendu } of cas) {
    assert.equal(normaliserNom(entree), attendu, `entrée : ${entree}`);
  }
});

const FAMILLES = ["gauche", "extreme_droite"];

function entree(
  insee: string,
  nom: string,
  extras: Partial<{ dpt: string; lat: number; lon: number; fam: number | null }> = {},
): EntreeIndex {
  return [
    insee,
    nom,
    extras.dpt ?? "Test",
    extras.lat ?? null,
    extras.lon ?? null,
    ["#111111", "#222222", "#333333"],
    [0, extras.fam === undefined ? 0 : extras.fam, 1],
  ];
}

const COMMUNES = [
  entree("30189", "Nîmes"),
  entree("93066", "Saint-Denis"),
  entree("97411", "Saint-Denis (La Réunion)"),
  entree("59178", "Denain"),
  entree("77133", "Coudenise"), // matche « deni » en infixe seulement
].map(indexerEntree);

test("rechercher — accents/casse indifférents, préfixes avant infixes, alphabétique", () => {
  // « DÈN » → « den » : préfixe de « denain » ; infixe de « coudenise » et
  // des deux « saint denis » — les préfixes sortent d'abord, puis alphabétique.
  const resultats = rechercher(COMMUNES, FAMILLES, "  DÈN ", 1);
  const noms = resultats.map((r) => r.nom);
  assert.deepEqual(
    noms,
    ["Denain", "Coudenise", "Saint-Denis", "Saint-Denis (La Réunion)"],
  );
});

test("rechercher — pastille hex/famille selon l'algo demandé", () => {
  const [r] = rechercher(COMMUNES, FAMILLES, "nimes", 1);
  assert.equal(r.code_insee, "30189");
  assert.equal(r.hex, "#222222"); // iAlgo 1
  assert.equal(r.famille, "gauche");
  const [rBlocs] = rechercher(COMMUNES, FAMILLES, "nimes", 2);
  assert.equal(rBlocs.hex, "#333333");
  assert.equal(rBlocs.famille, "extreme_droite");
});

test("rechercher — famille nulle quand l'index n'en porte pas", () => {
  const communes = [indexerEntree(entree("00001", "Sans-Famille", { fam: null }))];
  const [r] = rechercher(communes, FAMILLES, "sans", 1);
  assert.equal(r.famille, null);
});

test("rechercher — requête vide, hors index ou limite nulle", () => {
  assert.deepEqual(rechercher(COMMUNES, FAMILLES, "   ", 0), []);
  assert.deepEqual(rechercher(COMMUNES, FAMILLES, "zzzz", 0), []);
  assert.deepEqual(rechercher(COMMUNES, FAMILLES, "saint", 0, 0), []);
});

test("rechercher — limite respectée", () => {
  assert.equal(rechercher(COMMUNES, FAMILLES, "e", 0, 2).length, 2);
});

test("rechercher — la sélection bornée garde le début du classement complet", () => {
  // Plus de matchs que `limite`, fournis dans le désordre : le top-k doit
  // rendre exactement le début de l'ordre alphabétique global (et pas
  // simplement les k premiers rencontrés).
  const communes = ["Zuytpeene", "Arles", "Bram", "Ypres", "Anduze", "Brens"].map(
    (nom, i) => indexerEntree(entree(String(10000 + i), nom)),
  );
  const noms = rechercher(communes, FAMILLES, "r", 0, 3).map((r) => r.nom);
  // Tous contiennent « r » en infixe (aucun préfixe) : alphabétique strict.
  assert.deepEqual(noms, ["Arles", "Bram", "Brens"]);
});

test("rechercher — un préfixe passe avant un infixe alphabétiquement antérieur", () => {
  const communes = ["Denain", "Ardennes-Ville"].map((nom, i) =>
    indexerEntree(entree(String(20000 + i), nom)),
  );
  // « den » : Denain en préfixe, Ardennes-Ville en infixe pourtant premier
  // à l'alphabet — la règle préfixes-d'abord de l'API doit primer.
  const noms = rechercher(communes, FAMILLES, "den", 0).map((r) => r.nom);
  assert.deepEqual(noms, ["Denain", "Ardennes-Ville"]);
});

test("distanceM — ordre de grandeur connu (Paris → Marseille ≈ 660 km)", () => {
  const d = distanceM(48.8566, 2.3522, 43.2965, 5.3698);
  assert.ok(d > 630_000 && d < 690_000, `distance inattendue : ${d}`);
});

test("plusProche — la plus proche dans le rayon, null au-delà", () => {
  const communes = [
    indexerEntree(entree("93066", "Saint-Denis", { lat: 48.936, lon: 2.357 })),
    indexerEntree(entree("75056", "Paris", { lat: 48.857, lon: 2.352 })),
    indexerEntree(entree("00001", "Sans-Coordonnées")),
  ];
  // Point à ~1 km au sud de Saint-Denis.
  const proche = plusProche(communes, 48.927, 2.357, 5000);
  assert.equal(proche?.code_insee, "93066");
  // Rayon trop petit : rien.
  assert.equal(plusProche(communes, 48.5, 2.0, 1000), null);
});
