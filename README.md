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
| `pipeline/` | Ingestion & calcul (Python + Polars), génère les couleurs précalculées |
| `api/` | Backend de lecture (FastAPI + PostgreSQL/PostGIS) |
| `mobile/` | Application React Native / Expo (TypeScript) |
| `tiles/` | Génération des tuiles vectorielles (tippecanoe → PMTiles) — V1 |
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
                   │ REST API
┌──────────────────▼──────────────────────────────┐
│  BACKEND API (FastAPI — Python)                 │
│  Routers:                                       │
│  • communes.py → GET /communes/{insee}          │
│    GET /communes/{insee}/couleur                │
│  • scrutins.py → GET /communes/{insee}/scrutins │
│    GET /communes/{insee}/scrutins/{id}          │
│  Pydantic schemas · SQLAlchemy + psycopg2       │
└──────────────────┬──────────────────────────────┘
                   │ SQL queries
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
│  • europeennes_2024.py       • poids_scrutins.yaml│
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
Compute couleurs OKLCH → API FastAPI → Mobile app
```

## Stack

- **Mobile** : React Native + Expo (TypeScript), MapLibre Native, TanStack Query
- **Backend** : Python + FastAPI, Pydantic, SQLAlchemy + psycopg2
- **Base de données** : PostgreSQL + PostGIS
- **Pipeline** : Python, Polars, Alembic (migrations)
- **Cartographie** : tuiles vectorielles précalculées (tippecanoe → PMTiles)
- **Données** : data.gouv.fr (Ministère de l'Intérieur)

## Méthodologie

Le modèle de couleur (familles politiques, palette, pondération des scrutins, demi-vie de récence,
désaturation par l'abstention, algorithme complet) est **public et discutable**. Documentation
canonique dans la collection Outline *CaVoteQuoiIci*.

Paramètres versionnés :
- `pipeline/config/poids_scrutins.yaml` — poids des scrutins, demi-vie, plancher de désaturation
- `pipeline/config/nuances_familles.csv` — correspondance nuance officielle → famille politique

## Démarrage rapide

Prérequis : Docker (utilisateur dans le groupe `docker`), [`uv`](https://docs.astral.sh/uv/), Node 20+.

```bash
cp .env.example .env          # DATABASE_URL (défaut = base docker locale)
make venv                     # crée .venv (uv) + dépendances Python
make fresh                    # db PostGIS + migrations + pipeline complet (contours, 4 scrutins, couleurs)
make api                      # API sur http://localhost:8200  (doc : /docs)
make test                     # suite de tests (les tests BDD supposent la base de make fresh démarrée)
```

`make help` liste toutes les cibles (`db-up`, `migrate`, `data`, `couleurs`, `types`…).

> La base est un conteneur `cavote-db` (PostGIS). `make db-up` le crée/redémarre via `docker run` ;
> un `docker-compose.yml` équivalent est fourni pour les environnements disposant du plugin Compose.

État des données après `make fresh` : ~35 000 communes, 4 scrutins (présidentielle 2022,
législatives 2024, européennes 2024, municipales 2026), couleurs synthétiques calculées
(repères validés : Saint-Denis rouge, Nice marine).

## API (lecture seule)

| Méthode | Route | Rôle |
|---------|-------|------|
| GET | `/communes/search?q=` | Autocomplétion par nom |
| GET | `/communes/{insee}` | Fiche : métadonnées + couleur synthétique |
| GET | `/communes/{insee}/couleur` | Couleur OKLCH + hex + participation + scrutins inclus |
| GET | `/communes/{insee}/scrutins` | Scrutins inclus + poids relatif |
| GET | `/communes/{insee}/scrutins/{scrutin_id}` | Détail par famille + couleur du scrutin |
| GET | `/communes/proximite?lat=&lon=&rayon_m=` | Communes voisines (PostGIS) |
| GET | `/healthz` | Sonde de vivacité |

Les types TypeScript du client mobile sont générés depuis l'OpenAPI : `make types`
(→ `mobile/src/api/types.ts`).

## Mobile

```bash
cd mobile && npm install && npx expo start
```

Pour tester sur un téléphone (Expo Go SDK 56, backend sur le LAN, limites d'Expo Go,
APK de QA) : voir [`mobile/README.md`](mobile/README.md).

## État d'avancement (MVP)

Étapes 0→5 faites (fondations, contours, ingestion des scrutins, calcul des couleurs,
API, application mobile). **Étape 6 — tuiles vectorielles** : génération des PMTiles
opérationnelle (`make tiles`, voir [`tiles/README.md`](tiles/README.md)).
Reste de l'Étape 6 : intégration MapLibre dans l'app + hébergement CDN. Étape 7 : CI/CD + stores.

## Licence

[GNU AGPL v3](LICENSE). Tout fork déployé doit republier ses modifications — pas de dérivé opaque.
