PY := .venv/bin/python

# Charge le .env s'il existe (DATABASE_URL, REFERENCE_DATE…) et exporte les
# variables aux recettes : le README fait copier .env.example, ce fichier doit
# être effectif quand on passe par make. NB : `export` couvre toutes les
# variables make — si docker-compose.yml substitue un jour `${DATABASE_URL}`,
# le DSN localhost du .env fuirait vers la cible prod.
-include .env
export

.PHONY: help venv db-up db-down migrate data couleurs tiles api types test fresh \
	compose-up compose-migrate compose-down

help:  ## Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

venv:  ## Crée le venv (uv) et installe les dépendances
	uv venv .venv
	uv pip install --python $(PY) -r requirements.txt

db-up:  ## Démarre PostGIS (conteneur docker ; réutilise cavote-db s'il existe) et attend qu'il soit prêt
	@docker start cavote-db 2>/dev/null || docker run -d --name cavote-db \
		-e POSTGRES_PASSWORD=cavote -p 5432:5432 \
		-v cavote_pgdata:/var/lib/postgresql/data --restart unless-stopped \
		postgis/postgis:16-3.4
	@# -h localhost force un test en TCP : au premier démarrage (volume vierge),
	@# l'image lance un serveur d'init temporaire qui n'écoute que sur la socket
	@# unix — ce test ne passe donc qu'une fois le serveur définitif démarré.
	@for i in $$(seq 1 60); do \
		docker exec cavote-db pg_isready -h localhost -U postgres -q 2>/dev/null && exit 0; \
		sleep 1; \
	done; \
	echo "PostGIS toujours injoignable après 60 s (voir : docker logs cavote-db)" >&2; exit 1

db-down:  ## Arrête PostGIS
	docker stop cavote-db

.PHONY: db-dump db-restore
db-dump:  ## Exporte la base (pg_dump -Fc) vers backups/cavote-<horodatage>.dump
	@mkdir -p backups
	docker exec cavote-db pg_dump -U postgres -Fc -d postgres > backups/cavote-$$(date +%Y%m%d-%H%M%S).dump
	@ls -lh backups/ | tail -1

# --clean --if-exists : les objets existants sont remplacés — restauration
# rejouable sur une base déjà peuplée. Les 3 warnings « schema tiger/topology
# already exists » sont bénins (schémas créés par l'image PostGIS).
db-restore:  ## Restaure un dump : make db-restore DUMP=backups/cavote-<ts>.dump
	@test -n "$(DUMP)" || { echo "Usage : make db-restore DUMP=chemin/vers/fichier.dump" >&2; exit 1; }
	@test -f "$(DUMP)" || { echo "Fichier introuvable : $(DUMP)" >&2; exit 1; }
	docker exec -i cavote-db pg_restore -U postgres --clean --if-exists --no-owner -d postgres < $(DUMP)

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
