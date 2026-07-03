# Tuiles vectorielles — `communes.pmtiles`

Choroplèthe des ~35 000 communes, une couleur de synthèse par commune, au format
**PMTiles** (archive mono-fichier lisible par MapLibre GL via le protocole
`pmtiles://`). C'est la source de l'onglet Carte de l'app (étape 6 du MVP —
cf. « État d'avancement » du [README racine](../README.md)).

## Génération

```bash
make tiles          # = python -m pipeline.export_tiles
```

Prérequis : la base `couleurs_ville` peuplée (`make fresh`) et le binaire
**tippecanoe** — `apt install tippecanoe` (Debian 13+ / Ubuntu 24.04+),
`brew install tippecanoe` (macOS), paquet AUR (Arch), ou compilation depuis
[felt/tippecanoe](https://github.com/felt/tippecanoe). Le script :

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
| Couverture | les ~35 000 communes présentes au zoom max (`--coalesce-densest-as-needed` — fusion, pas suppression : le drop laissait des trous dans les zones denses aux zooms bas — et `--extend-zooms-if-still-dropping`) |
| Taille | ~27 Mo |

### Propriétés par commune (feature)

| Clé | Exemple | Usage côté app |
|-----|---------|----------------|
| `insee` | `"93066"` | navigation `commune/[insee]` au tap |
| `nom` | `"Saint-Denis"` | libellé |
| `hex` | `"#AB564B"` | `fill-color` du polygone |
| `famille` | `"extreme_gauche"` | légende / filtres (famille dominante) |
| `participation` | `0.507` | infobulle / désaturation déjà intégrée au hex |

## Servir les tuiles

- **Dev local** : `make tiles-serve` (binaire [go-pmtiles](https://github.com/protomaps/go-pmtiles))
  sert l'archive en `{z}/{x}/{y}.mvt` sur `:8300` — le schéma attendu par l'app.
  À défaut, n'importe quel serveur statique gérant les requêtes `Range` convient.
- **Production (à venir)** : déposer `communes.pmtiles` sur un CDN (Cloudflare R2…)
  avec en-têtes CORS + `Range`.

## Suite (non couvert ici)
- **Intégration MapLibre** dans `mobile/` (`@maplibre/maplibre-react-native`),
  couche `fill` colorée par la propriété `hex`, tap → fiche commune.
