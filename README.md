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

## Stack

- **Mobile** : React Native + Expo (TypeScript), MapLibre Native, TanStack Query
- **Backend** : Python + FastAPI, PostgreSQL + PostGIS
- **Données** : pipeline Python (Polars) ingérant les CSV du Ministère de l'Intérieur (data.gouv.fr)
- **Cartographie** : tuiles vectorielles précalculées (tippecanoe → PMTiles)

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
make api                      # API sur http://localhost:8000  (doc : /docs)
make test                     # suite de tests
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

## État d'avancement (MVP)

Étapes 0→4 faites (fondations, contours, ingestion des scrutins, calcul des couleurs, API).
Prochaine étape : application mobile (écrans Accueil / Fiche commune / Méthodologie).

## Licence

[GNU AGPL v3](LICENSE). Tout fork déployé doit republier ses modifications — pas de dérivé opaque.
