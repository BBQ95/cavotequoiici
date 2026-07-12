/**
 * Tests Node (`npm test`) des types statiques du client.
 *
 * La parité de `ALGOS` avec `pipeline/couleur.py::ALGOS` est verrouillée par
 * la fixture partagée (`tests/fixtures/algos_parite.json`, gardée à jour par
 * un test Python) : un algo ajouté d'un seul côté casse l'un des deux dépôts.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { test } from "node:test";

import { ALGOS } from "./types";

const FIXTURES = join(__dirname, "../../../tests/fixtures/algos_parite.json");

test("ALGOS — parité avec pipeline.couleur.ALGOS (fixture backend)", () => {
  const { algos } = JSON.parse(readFileSync(FIXTURES, "utf-8")) as {
    algos: string[];
  };
  assert.deepStrictEqual([...ALGOS], algos);
});
