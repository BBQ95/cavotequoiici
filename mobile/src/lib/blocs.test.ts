/**
 * Tests Node (`npm test`) de l'agrégation par blocs de la fiche commune.
 *
 * La parité de `BLOCS` avec `pipeline/couleur.py::BLOCS` est verrouillée par
 * la fixture partagée (`tests/fixtures/blocs_parite.json`, gardée à jour par
 * un test Python) : si le mapping évolue d'un côté, l'un des deux dépôts casse.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { test } from "node:test";

import { BLOCS, agregerParBlocs } from "./blocs";

const FIXTURES = join(__dirname, "../../../tests/fixtures/blocs_parite.json");

test("BLOCS — parité avec pipeline.couleur.BLOCS (fixture backend)", () => {
  const { blocs } = JSON.parse(readFileSync(FIXTURES, "utf-8")) as {
    blocs: Record<string, string>;
  };
  assert.deepEqual(BLOCS, blocs);
});

test("agregerParBlocs — somme les familles de chaque bloc, divers à part", () => {
  const segments = agregerParBlocs([
    { famille: "extreme_gauche", part: 0.1 },
    { famille: "gauche", part: 0.2 },
    { famille: "ecologistes", part: 0.05 },
    { famille: "centre", part: 0.15 },
    { famille: "droite", part: 0.2 },
    { famille: "extreme_droite", part: 0.1 },
    { famille: "divers", part: 0.2 },
  ]);
  const attendu = [
    { famille: "gauche", part: 0.35 },
    { famille: "centre", part: 0.15 },
    { famille: "droite", part: 0.3 },
    { famille: "divers", part: 0.2 },
  ];
  assert.deepEqual(
    segments.map((s) => s.famille),
    attendu.map((s) => s.famille),
  );
  // Sommes de flottants : comparaison à tolérance, pas d'égalité stricte.
  for (const [i, s] of segments.entries()) {
    assert.ok(
      Math.abs(s.part - attendu[i].part) < 1e-9,
      `${s.famille} : ${s.part} ≠ ${attendu[i].part}`,
    );
  }
});

test("agregerParBlocs — le total est conservé (rien n'est exclu de la barre)", () => {
  const repartition = [
    { famille: "gauche", part: 0.31 },
    { famille: "divers", part: 0.62 },
    { famille: "centre", part: 0.07 },
  ];
  const total = agregerParBlocs(repartition).reduce((s, b) => s + b.part, 0);
  assert.ok(Math.abs(total - 1) < 1e-9, `total inattendu : ${total}`);
});

test("agregerParBlocs — n'émet que les blocs présents, dans un ordre stable", () => {
  const segments = agregerParBlocs([
    { famille: "divers", part: 0.6 },
    { famille: "extreme_droite", part: 0.4 },
  ]);
  assert.deepEqual(segments, [
    { famille: "droite", part: 0.4 },
    { famille: "divers", part: 0.6 },
  ]);
});

test("agregerParBlocs — famille inconnue traitée comme divers (défensif)", () => {
  const segments = agregerParBlocs([
    { famille: "gauche", part: 0.5 },
    { famille: "famille_future", part: 0.5 },
  ]);
  assert.deepEqual(segments, [
    { famille: "gauche", part: 0.5 },
    { famille: "divers", part: 0.5 },
  ]);
});

test("agregerParBlocs — répartition vide", () => {
  assert.deepEqual(agregerParBlocs([]), []);
});
