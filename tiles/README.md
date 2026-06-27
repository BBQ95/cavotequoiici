# Tuiles vectorielles — `communes.pmtiles`

Étape 6.1 du [guide d'implémentation](../README.md). Choroplèthe des ~35 000
communes, une couleur de synthèse par commune, au format **PMTiles** (archive
mono-fichier lisible par MapLibre GL via le protocole `pmtiles://`).

## Génération

```bash
make tiles          # = python -m pipeline.export_tiles
```

Prérequis : la base `couleurs_ville` peuplée (`make fresh`) et le binaire
**tippecanoe** (`apt install tippecanoe`). Le script :

1. joint `communes` × `couleurs_ville` et écrit `tiles/communes.geojson` ;
2. précalcule la couleur **sRGB `#RRGGBB`** depuis l'OKLCH de synthèse
   (`pipeline.couleur.oklch_to_hex`) — MapLibre n'interpole pas en OKLCH, et
   figer le hex garantit que la carte montre **exactement** la couleur de la
   fiche commune ;
3. lance tippecanoe → `tiles/communes.pmtiles`.

Les deux fichiers produits sont **volumineux et regénérables** → non versionnés
(voir `.gitignore`).

## Caractéristiques

| Propriété | Valeur |
|-----------|--------|
| Couche (`source-layer`) | `communes` |
| Zooms | 4 (France entière) → 11 (rue) |
| Couverture | les ~35 000 communes présentes au zoom max (`--drop-densest-as-needed` aux zooms bas seulement, `--extend-zooms-if-still-dropping`) |
| Taille | ~27 Mo |

### Propriétés par commune (feature)

| Clé | Exemple | Usage côté app |
|-----|---------|----------------|
| `insee` | `"93066"` | navigation `commune/[insee]` au tap |
| `nom` | `"Saint-Denis"` | libellé |
| `hex` | `"#AB564B"` | `fill-color` du polygone |
| `famille` | `"extreme_gauche"` | légende / filtres (famille dominante) |
| `participation` | `0.507` | infobulle / désaturation déjà intégrée au hex |

## Suite (non couvert ici)

- **Hébergement** : déposer `communes.pmtiles` sur un CDN (Cloudflare R2…) avec
  en-têtes CORS + `Range`. En dev local, n'importe quel serveur statique gérant
  les requêtes `Range` convient.
- **Intégration MapLibre** dans `mobile/` (`@maplibre/maplibre-react-native`),
  couche `fill` colorée par la propriété `hex`, tap → fiche commune.
