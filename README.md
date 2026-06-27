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

## Développement

```bash
# Pipeline + API (Python 3.12)
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt        # ou : pip install fastapi uvicorn polars psycopg2-binary sqlalchemy alembic geopandas pytest
pytest pipeline/tests

# Base de données (Docker)
docker run -d --name cavote-db -e POSTGRES_PASSWORD=cavote -p 5432:5432 postgis/postgis:16-3.4
cd api && alembic upgrade head

# Mobile
cd mobile && npm install && npx expo start
```

## Licence

[GNU AGPL v3](LICENSE). Tout fork déployé doit republier ses modifications — pas de dérivé opaque.
