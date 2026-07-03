# Glyphes MapLibre (étiquettes de la carte)

Glyphes SDF pré-générés au format PBF, servis par l'API sous
`/fonts/{fontstack}/{range}.pbf` (mount StaticFiles dans `api/main.py`).
La carte mobile les référence via la clé `glyphs` de son style MapLibre pour
rendre les noms de communes (couche `etiquettes` des tuiles) — MapLibre ne
sait pas rendre de texte sans cet endpoint.

## Provenance et licence

- Police : **Noto Sans Medium** (The Noto Project Authors), licence
  **SIL Open Font License 1.1** — voir [`OFL.txt`](OFL.txt) (en `.txt` : le
  `.dockerignore` exclut `*.md`, la licence doit voyager dans l'image API).
- Fichiers récupérés le 2026-07-03 depuis le dépôt public
  [protomaps/basemaps-assets](https://github.com/protomaps/basemaps-assets)
  (`fonts/Noto Sans Medium/`), qui distribue ces ranges pré-générés.

## Pourquoi seulement 2 ranges ?

MapLibre demande les glyphes par plages de 256 codepoints. Vérifié en base :
**aucun des 35 012 noms de communes n'utilise de codepoint > 511** (seuls
`Œ`/`œ`, U+0152/U+0153, dépassent Latin-1). Les plages `0-255` et `256-511`
couvrent donc tout le corpus (~200 Ko).

Si un futur ré-import (COG, renommage de commune) introduit un caractère
au-delà : le range manquant répond 404 et le nom concerné ne s'affiche pas —
télécharger alors le range correspondant depuis le même dépôt et le committer
ici.
