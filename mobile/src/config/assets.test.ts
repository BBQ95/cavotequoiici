/**
 * Tests Node (`npm test`) des assets d'icône de l'app (`mobile/assets/`).
 *
 * Verrouille la déclinaison de l'icône définitive (kit Play Store, validée le
 * 2026-07-14) : dimensions attendues par Expo, et surtout **plus aucun
 * placeholder Expo par défaut** (le chevron bleu livré par create-expo-app,
 * découvert le 13/07) — l'icône installée doit correspondre à la fiche store.
 * Le favicon du site vitrine partage le même design (source unique).
 */
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { test } from "node:test";

const ASSETS = join(__dirname, "../../assets");
const SITE = join(__dirname, "../../../site");

/** Dimensions et type de couleur lus dans l'en-tête IHDR d'un PNG. */
function enTetePng(chemin: string) {
  const png = readFileSync(chemin);
  assert.equal(png.readUInt32BE(12), 0x49484452, `${chemin} : IHDR attendu`);
  return {
    largeur: png.readUInt32BE(16),
    hauteur: png.readUInt32BE(20),
    // 6 = RGBA, 2 = RGB (Truecolour), 3 = palette.
    typeCouleur: png.readUInt8(25),
    sha256: createHash("sha256").update(png).digest("hex"),
  };
}

// SHA256 des placeholders Expo par défaut (create-expo-app), relevés avant
// remplacement — aucun asset ne doit plus y correspondre.
const PLACEHOLDERS = new Set([
  "119462bb78eb240a65c869fc067ee599639b3cb5a41953f25c07b17d2a8c7e0f", // icon.png
  "9e3d0315a33c6799de601dd34cd8bf8cc3a8d16f3bf75592baec2ceb7240b391", // android-icon-foreground.png
  "fb139c2dee362ebf2070e23b96da6fc0d43f8492de38b8af1fd7223e19b5861d", // android-icon-background.png
  "6371fc2c12e33ad2215a86c281db3d682a81bebe7c957a842c13b8bf00cceb83", // android-icon-monochrome.png
  "5f4c0a732b6325bf4071d9124d2ae67e037cb24fcc9c482ef82bea742109a3b8", // splash-icon.png
  "a4e030697a7571b3e95d31860e4da55d2f98e5e861e2b55e414f45a8556828ba", // favicon.png (app ET site)
]);

const ATTENDUS: Array<{ fichier: string; taille: number; alpha?: boolean }> = [
  { fichier: "icon.png", taille: 1024 },
  { fichier: "android-icon-foreground.png", taille: 1024, alpha: true },
  { fichier: "android-icon-background.png", taille: 1024 },
  { fichier: "android-icon-monochrome.png", taille: 1024, alpha: true },
  { fichier: "splash-icon.png", taille: 1024, alpha: true },
  { fichier: "favicon.png", taille: 48 },
];

for (const { fichier, taille, alpha } of ATTENDUS) {
  test(`assets — ${fichier} : ${taille}×${taille}, plus le placeholder Expo`, () => {
    const png = enTetePng(join(ASSETS, fichier));
    assert.equal(png.largeur, taille);
    assert.equal(png.hauteur, taille);
    if (alpha) {
      assert.equal(png.typeCouleur, 6, "couche alpha requise (RGBA)");
    }
    assert.ok(
      !PLACEHOLDERS.has(png.sha256),
      `${fichier} est encore un placeholder Expo par défaut`,
    );
  });
}

test("site — favicon.png appliqué (même design, plus le placeholder)", () => {
  const png = enTetePng(join(SITE, "favicon.png"));
  assert.ok(png.largeur >= 64, "au moins 64px (affiché en 64×64 sur le site)");
  assert.equal(png.largeur, png.hauteur);
  assert.ok(
    !PLACEHOLDERS.has(png.sha256),
    "site/favicon.png est encore un placeholder Expo par défaut",
  );
});
