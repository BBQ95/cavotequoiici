PY := .venv/bin/python

.PHONY: help venv db-up db-down migrate data couleurs tiles api types test fresh \
	compose-up compose-migrate compose-down

help:  ## Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

venv:  ## Crée le venv (uv) et installe les dépendances
	uv venv .venv
	uv pip install --python $(PY) -r requirements.txt

db-up:  ## Démarre PostGIS (conteneur docker ; réutilise cavote-db s'il existe)
	@docker start cavote-db 2>/dev/null || docker run -d --name cavote-db \
		-e POSTGRES_PASSWORD=cavote -p 5432:5432 \
		-v cavote_pgdata:/var/lib/postgresql/data --restart unless-stopped \
		postgis/postgis:16-3.4

db-down:  ## Arrête PostGIS
	docker stop cavote-db

migrate:  ## Applique les migrations Alembic
	cd api && ../$(PY) -m alembic upgrade head

data:  ## Pipeline complet : contours + 4 scrutins + couleurs
	$(PY) -m pipeline.run_all

couleurs:  ## Recalcule uniquement les couleurs
	$(PY) -m pipeline.compute_couleurs

tiles:  ## Génère les tuiles vectorielles PMTiles (Étape 6 ; nécessite tippecanoe)
	$(PY) -m pipeline.export_tiles

# NB : port 8200 — le 8000 est RÉSERVÉ à workspace-mcp (intégration Google de Boss), ne pas l'utiliser.
api:  ## Lance l'API en développement (rechargement auto)
	$(PY) -m uvicorn api.main:app --reload --port 8200

types:  ## Régénère les types TypeScript du mobile depuis l'OpenAPI
	$(PY) -m api.openapi_export openapi.json
	npx --yes openapi-typescript@7.13.0 openapi.json -o mobile/src/api/types.ts

test:  ## Lance la suite de tests
	$(PY) -m pytest -q

fresh: db-up migrate data  ## De zéro à base peuplée (db + migrations + pipeline)
	@echo "Base prête. Lancer l'API : make api"

# --- Stack conteneurisée (db + api) : cible de l'hébergement prod ------------
compose-up:  ## Build + démarre la stack backend en conteneurs (db + api)
	docker compose up -d --build

compose-migrate:  ## Applique les migrations Alembic dans le conteneur api
	docker compose run --rm api sh -c "cd api && python -m alembic upgrade head"

compose-down:  ## Arrête la stack conteneurisée (conserve le volume de données)
	docker compose down
