# Tuiles vectorielles — `communes.pmtiles`

Choroplèthe des ~35 000 communes (couleur de synthèse + couleurs par scrutin)
**et** étiquettes de noms de villes, au format **PMTiles** (archive
mono-fichier lisible par MapLibre GL via le protocole `pmtiles://`). C'est la
source de l'onglet Carte de l'app (étape 6 du MVP — cf. « État d'avancement »
du [README racine](../README.md)).

## Génération

```bash
make tiles          # = python -m pipeline.export_tiles
```

Prérequis : la base `couleurs_ville` peuplée (`make fresh`) et le binaire
**tippecanoe** (qui fournit aussi `tile-join`) — `apt install tippecanoe`
(Debian 13+ / Ubuntu 24.04+), `brew install tippecanoe` (macOS), paquet AUR
(Arch), ou compilation depuis
[felt/tippecanoe](https://github.com/felt/tippecanoe). Le script :

1. joint `communes` × `couleurs_ville` (+ `couleurs_scrutin`) et écrit
   `tiles/communes.geojson` ; extrait les points d'étiquette
   (`ST_PointOnSurface`, rang national par `MAX(inscrits)`) dans
   `tiles/etiquettes.geojson` ;
2. précalcule les couleurs **sRGB `#RRGGBB`** depuis l'OKLCH
   (`pipeline.couleur.oklch_to_hex`) — MapLibre n'interpole pas en OKLCH, et
   figer le hex garantit que la carte montre **exactement** la couleur de la
   fiche commune ;
3. lance tippecanoe : une archive de polygones, puis **une archive
   d'étiquettes par niveau de zoom** (tranches), fusionnées par `tile-join`
   → `tiles/communes.pmtiles`.

> Pourquoi des tranches ? Le minzoom par feature de tippecanoe
> (`"tippecanoe": {"minzoom": N}`) réactive, en 2.49.0, un dot-dropping qui
> ignore `-r1` : une seule ville survivait par tuile. Les tranches mono-zoom
> avec `-r1` garantissent qu'aucune étiquette éligible n'est supprimée.

Les fichiers produits sont **volumineux et regénérables** → non versionnés
(voir `.gitignore`).

## Caractéristiques

| Propriété | Valeur |
|-----------|--------|
| Couches (`source-layer`) | `communes` (polygones), `etiquettes` (points) |
| Zooms | 4 (France entière) → 11 (rue) |
| Couverture | les ~35 000 communes présentes au zoom max (`--coalesce-densest-as-needed` — fusion, pas suppression : le drop laissait des trous dans les zones denses aux zooms bas — et `--extend-zooms-if-still-dropping`) |
| Taille | ~31 Mo |

### Propriétés par commune (couche `communes`)

| Clé | Exemple | Usage côté app |
|-----|---------|----------------|
| `insee` | `"93066"` | navigation `commune/[insee]` au tap |
| `nom` | `"Saint-Denis"` | libellé |
| `hex` | `"#AB564B"` | `fill-color` du polygone (synthèse, algo « complet ») |
| `hex_<scrutin_id>` | `"#5A6FA3"` | `fill-color` de la couche d'un scrutin (absent si scrutin non disputé) |
| `hex_algo_<algo>` | `"#1C2535"` | `fill-color` selon l'algo de dominance (`tendance`, `blocs` ; « complet » = clé `hex`) — cf. `pipeline.couleur.ALGOS` |
| `famille` | `"extreme_gauche"` | légende / filtres (famille dominante) |
| `participation` | `0.507` | infobulle / désaturation déjà intégrée au hex |

### Propriétés par étiquette (couche `etiquettes`)

| Clé | Exemple | Usage côté app |
|-----|---------|----------------|
| `nom` | `"Marseille"` | texte du libellé (`text-field`) |
| `insee` | `"13055"` | tap sur un nom → fiche commune |
| `rang` | `2` | priorité de collision (`symbol-sort-key`) |

Zoom d'apparition par rang national (`SEUILS_MINZOOM` du pipeline) :

| Rang ≤ | 10 | 40 | 120 | 400 | 1200 | 4000 | 12000 | au-delà |
|--------|----|----|-----|-----|------|------|-------|---------|
| Zoom   | 4  | 5  | 6   | 7   | 8    | 9    | 10    | 11 |

Le **rendu du texte** côté app exige un endpoint de glyphes : `/fonts` sur
`EXPO_PUBLIC_DATA_URL` (cf. `pipeline/fonts/README.md` — embarqués dans l'export
statique). Sans glyphes, la carte s'affiche sans noms.

## Servir les tuiles

L'app lit l'archive **directement en `pmtiles://`** (requêtes `Range` sur
`${EXPO_PUBLIC_DATA_URL}/tiles/communes.pmtiles`) — aucun serveur de tuiles
dédié.

- **Dev local** : `make data-serve` (ou `data-serve-lan` pour un device) sert
  `export/` et monte ce dossier `tiles/` sous `/tiles/`, avec le support
  `Range` + CORS requis.
- **Production** : `communes.pmtiles` est déposé sur le CDN
  (Cloudflare R2, `data.cavotequoiici.fr`) avec en-têtes CORS + `Range`.

## Suite (non couvert ici)
- **Intégration MapLibre** dans `mobile/` (`@maplibre/maplibre-react-native`),
  couche `fill` colorée par la propriété `hex`, tap → fiche commune.
