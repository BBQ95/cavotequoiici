# CaVoteQuoiIci

> Application mobile **gratuite et open source (AGPL v3)** qui donne à voir la **couleur politique**
> d'une commune française : un **indice synthétique** calculé sur l'ensemble des scrutins récents
> (présidentielle, législatives, européennes, municipales…), modulé par la participation.
> Du **rouge vif** (extrême gauche) au **bleu marine** (extrême droite), avec le **vert** pour les
> écologistes. Repères : **Saint-Denis → rouge**, **Nice → bleu marine**.

## Le contrat d'honnêteté

- La couleur reflète **les suffrages exprimés sur l'ensemble des scrutins récents**, pas une seule élection.
- L'**abstention entre dans le calcul** : moins une commune vote, plus sa couleur est pâle.
- Elle ne décrit **pas « les habitants »** et n'est **pas un jugement**.
- Le **taux de participation** est toujours affiché au même niveau que la couleur.
- L'encart « comment cette couleur est calculée » liste les scrutins inclus et leur poids :
  la synthèse n'est **jamais une boîte noire**.

## Architecture (monorepo)

| Dossier | Rôle |
|---------|------|
| `pipeline/` | Ingestion & calcul (Python + Polars), export des artefacts statiques (fiches, index de recherche, nuances, glyphes) |
| `mobile/` | Application React Native / Expo (TypeScript) |
| `tiles/` | Génération des tuiles vectorielles (tippecanoe → PMTiles) |
| `docs/` | Documentation complémentaire |

```
┌─────────────────────────────────────────────────┐
│  MOBILE (React Native / Expo — TypeScript)       │
│  ┌─────────┐ ┌──────┐ ┌────────┐                 │
│  │ Maison  │ │ Carte│ │Méthode │                 │
│  └─────────┘ └──────┘ └────────┘                 │
│  Components: ColorHero, RepartitionBar,          │
│  ScrutinDetail, TransparenceEncart               │
│  Data: TanStack Query → client.ts                │
└──────────────────┬──────────────────────────────┘
                   │ HTTPS (fichiers statiques + Range pmtiles://)
┌──────────────────▼──────────────────────────────┐
│  ARTEFACTS STATIQUES (CDN data.cavotequoiici.fr)│
│  • communes/{insee}.json (3 algos + scrutins)   │
│  • index/communes.json (recherche/géoloc)       │
│  • nuances.json · meta/version.json             │
│  • fonts/… (glyphes) · tiles/communes.pmtiles   │
│  Publiés par make export-statique (+ rclone)    │
└──────────────────┬──────────────────────────────┘
                   │ pipeline/export_communes.py
┌──────────────────▼──────────────────────────────┐
│  BASE DE DONNÉES (PostgreSQL)                   │
│  • communes (code_insee, nom, geom)             │
│  • scrutins (id, type, date, poids)             │
│  • resultats_scrutin (insee, scrutin_id,         │
│    nuance, voix, exprimes, inscrits)             │
│  • couleurs_ville (insee, hex, famille_dominante,│
│    scrutins_inclus JSON)                         │
│  • couleurs_scrutin (insee, scrutin_id, L,C,H)  │
└──────────────────┬──────────────────────────────┘
                   │ pipeline Python
┌──────────────────▼──────────────────────────────┐
│  PIPELINE DE DONNÉES (Python — Polars)          │
│                                                  │
│  Ingestion:                  Config:             │
│  • presidentielle_2022.py    • nuances/*.csv     │
│  • legislatives_2024.py        (nuance→famille)  │
│  • europeennes_2024.py       • poids.toml (S1+S4) │
│  • municipales_2026.py                           │
│      ↓ data.gouv.fr CSV                          │
│                                                  │
│  Calcul:                                          │
│  • couleur.py (OKLCH: clamp, poids_recence,     │
│    poids_scrutin, couleur_ville, hex↔oklch)      │
│  • compute_couleurs.py → couleurs_ville/         │
│    couleurs_scrutin                              │
│  • synthese.py → synthèse pondérée              │
│  • run_all.py → orchestration                    │
│  • export_tiles.py → tuiles vectorielles (V1)   │
└─────────────────────────────────────────────────┘

Flux de données (bottom → top):
CSV data.gouv.fr → Ingest Polars → PostgreSQL →
Compute couleurs OKLCH → export statique → CDN → Mobile app
```

## Stack

- **Mobile** : React Native + Expo (TypeScript), MapLibre Native, TanStack Query
- **Backend** : Python, Pydantic (schémas des artefacts), SQLAlchemy + psycopg2
- **Base de données** : PostgreSQL + PostGIS (dev/pipeline uniquement — la prod est statique)
- **Pipeline** : Python, Polars, Alembic (migrations)
- **Cartographie** : tuiles vectorielles précalculées (tippecanoe → PMTiles)
- **Données** : data.gouv.fr (Ministère de l'Intérieur)

## Méthodologie

Le modèle de couleur (familles politiques, palette, pondération des scrutins, demi-vie de récence,
désaturation par l'abstention, algorithme complet) est **public et discutable** : il est décrit
dans [`docs/methodologie.md`](docs/methodologie.md).

Paramètres versionnés :
- `pipeline/config/poids.toml` — poids des scrutins (barème « S1 ») et modulation par le taux de couverture (« S4 »)
- `pipeline/config/nuances/` — correspondance nuance officielle → famille politique (un CSV par scrutin)
- `pipeline/config/familles.csv` — familles politiques et couleurs canoniques

## Démarrage rapide

Prérequis : Docker (utilisateur dans le groupe `docker`), [`uv`](https://docs.astral.sh/uv/), Node 20+.

```bash
cp .env.example .env          # DATABASE_URL (défaut = base docker locale)
make venv                     # crée .venv (uv) + dépendances Python
make fresh                    # db PostGIS + migrations + pipeline complet (contours, 4 scrutins, couleurs)
make export-statique          # artefacts statiques (fiches, index, nuances, glyphes) → export/
make data-serve               # sert export/ + tuiles comme le CDN de prod (http://127.0.0.1:8400)
make test                     # suite de tests (les tests BDD supposent la base de make fresh démarrée)
```

`make help` liste toutes les cibles (`db-up`, `migrate`, `data`, `couleurs`, `tiles`,
`data-serve-lan`…).

> La base est un conteneur `cavote-db` (PostGIS). `make db-up` le crée/redémarre via `docker run`.

État des données après `make fresh` : ~35 000 communes, 4 scrutins (présidentielle 2022,
législatives 2024, européennes 2024, municipales 2026), couleurs synthétiques calculées
(repères validés : Saint-Denis rouge, Nice marine).

> **Base de dev sans pipeline** : si vous ne touchez pas à l'ingestion, un dump prêt à l'emploi
> (~27 Mo) est publié dans les [releases GitHub](https://github.com/BBQ95/cavotequoiici/releases)
> (la révision Alembic correspondante est notée dans chaque release). Restauration :
>
> ```bash
> make db-up && make migrate
> make db-restore DUMP=chemin/vers/cavote-<ts>.dump
> ```
>
> `make db-dump` fait l'opération inverse (export vers `backups/`, hors git).

## Artefacts statiques (CDN)

L'app de production ne contacte **que** `https://data.cavotequoiici.fr` (recherche et
géolocalisation sont **locales**, sur l'index embarqué) :

| Chemin | Rôle |
|--------|------|
| `communes/{insee}.json` | Fiche : métadonnées + couleur par algo + scrutins embarqués |
| `index/communes.json` | Index compact de recherche/géolocalisation (offline) |
| `nuances.json` | Grilles nuance → famille (écran « D'où viennent les familles ? ») |
| `meta/version.json` | Version du jeu de données (cache-busting) |
| `fonts/{fontstack}/{range}.pbf` | Glyphes MapLibre (étiquettes de la carte) |
| `tiles/communes.pmtiles` | Tuiles vectorielles, lues en `pmtiles://` (requêtes Range) |

Publication : `make export-statique` puis synchronisation vers le bucket R2 (runbook interne).
En local, `make data-serve` sert exactement ce contrat. Les types TypeScript du client mobile
(`mobile/src/api/types.ts`) sont **manuels**, miroir des schémas `pipeline/schemas/*.py`.

## Mobile

```bash
cd mobile && npm install && npx expo start
```

Pour tester sur un téléphone (Expo Go SDK 56, export local servi sur le LAN, limites
d'Expo Go, APK de QA) : voir [`mobile/README.md`](mobile/README.md).

## État d'avancement (MVP)

**Étapes 0→6 faites** : fondations, contours, ingestion des scrutins, calcul des couleurs,
application mobile, tuiles vectorielles (`make tiles`, voir [`tiles/README.md`](tiles/README.md))
**et carte MapLibre intégrée** (onglet Carte : choroplèthe des ~35 000 communes, tap → fiche).

**Étape 7** : hébergement de production **statique** en place (CDN `data.cavotequoiici.fr`) —
l'API FastAPI historique a été décommissionnée. CI/CD : `ci.yml` (garde-fou de PR : tests,
migrations, typecheck + bundle mobile), `integration.yml` (nocturne, pipeline complet sur
données réelles + communes repères + export statique), `android-test.yml` (APK de QA +
distribution Firebase). Reste : la publication sur les stores.

## Licence

[GNU AGPL v3](LICENSE). Tout fork déployé doit republier ses modifications — pas de dérivé opaque.
