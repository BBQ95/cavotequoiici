/**
 * Tests Node (`npm test`) des transformations pures du client statique.
 */
import assert from "node:assert/strict";
import { test } from "node:test";

import "./test-globals";
import { versScrutins } from "./client";
import type { FicheStatique } from "./types-statiques";

/** Fiche minimale : seuls `code_insee` et `scrutins` comptent ici. */
function fiche(scrutins: { scrutin_id: string; date: string }[]): FicheStatique {
  return {
    code_insee: "30189",
    scrutins: scrutins.map((s) => ({
      ...s,
      type: s.scrutin_id.replace(/_\d+$/, ""),
      poids_relatif: 0.25,
      detail: null,
    })),
  } as unknown as FicheStatique;
}

test("versScrutins — ordre chronologique inverse (le plus récent en premier)", () => {
  // Ordre réel constaté dans les fiches publiées : ni chronologique ni stable.
  const resultat = versScrutins(
    fiche([
      { scrutin_id: "leg_t1_2024", date: "2024-06-30" },
      { scrutin_id: "euro_2024", date: "2024-06-09" },
      { scrutin_id: "mun_t1_2026", date: "2026-03-15" },
      { scrutin_id: "pres_t1_2022", date: "2022-04-10" },
    ]),
  );
  assert.deepEqual(
    resultat.scrutins.map((s) => s.scrutin_id),
    ["mun_t1_2026", "leg_t1_2024", "euro_2024", "pres_t1_2022"],
  );
});

test("versScrutins — départage stable par scrutin_id à date égale", () => {
  const resultat = versScrutins(
    fiche([
      { scrutin_id: "reg_t1_2021", date: "2021-06-20" },
      { scrutin_id: "dep_t1_2021", date: "2021-06-20" },
    ]),
  );
  assert.deepEqual(
    resultat.scrutins.map((s) => s.scrutin_id),
    ["dep_t1_2021", "reg_t1_2021"],
  );
});

test("versScrutins — la fiche source n'est pas mutée", () => {
  const source = fiche([
    { scrutin_id: "pres_t1_2022", date: "2022-04-10" },
    { scrutin_id: "mun_t1_2026", date: "2026-03-15" },
  ]);
  versScrutins(source);
  assert.deepEqual(
    source.scrutins.map((s) => s.scrutin_id),
    ["pres_t1_2022", "mun_t1_2026"],
  );
});

test("versScrutins — liste vide", () => {
  assert.deepEqual(versScrutins(fiche([])).scrutins, []);
});
