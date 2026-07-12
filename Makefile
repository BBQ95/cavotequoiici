PY := .venv/bin/python

# Charge le .env s'il existe (DATABASE_URL, REFERENCE_DATE…) et exporte les
# variables aux recettes : le README fait copier .env.example, ce fichier doit
# être effectif quand on passe par make.
-include .env
export

.PHONY: help venv db-up db-down migrate data couleurs tiles \
	test fresh export-statique data-serve data-serve-lan \
	mobile-dev-android mobile-dev-ios site-serve

help:  ## Affiche cette aide
	@grep -hE '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

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
	$(PY) -m alembic upgrade head

# PYTHONUNBUFFERED : les tracebacks du pipeline sortent immédiatement quand la
# sortie est redirigée (tee, CI) au lieu d'être noyées par le buffering stdout.
data:  ## Pipeline complet : contours + 4 scrutins + couleurs
	PYTHONUNBUFFERED=1 $(PY) -m pipeline.run_all

couleurs:  ## Recalcule uniquement les couleurs
	PYTHONUNBUFFERED=1 $(PY) -m pipeline.compute_couleurs

tiles:  ## Génère les tuiles vectorielles PMTiles (Étape 6 ; nécessite tippecanoe)
	PYTHONUNBUFFERED=1 $(PY) -m pipeline.export_tiles

export-statique:  ## Exporte les artefacts statiques (fiches JSON, nuances, version, glyphes) vers export/
	PYTHONUNBUFFERED=1 $(PY) -m pipeline.export_communes

# Miroir local du CDN de prod : sert export/ + tiles/ (alias /tiles/) avec
# Range (obligatoire pour pmtiles://) et CORS. Côté app, pointer
# EXPO_PUBLIC_DATA_URL=http://<IP LAN>:8400 (inlinée au build Expo).
data-serve:  ## Sert export/ + tuiles comme le CDN de prod sur 127.0.0.1:8400
	@test -d export || { echo "export/ absent — lancer : make export-statique" >&2; exit 1; }
	$(PY) scripts/serve_export.py --dossier export --tiles tiles --port 8400

data-serve-lan:  ## Comme data-serve, accessible depuis le LAN (test sur device — réseau de confiance uniquement)
	@test -d export || { echo "export/ absent — lancer : make export-statique" >&2; exit 1; }
	$(PY) scripts/serve_export.py --dossier export --tiles tiles --port 8400 --hote 0.0.0.0

test:  ## Lance la suite de tests
	$(PY) -m pytest -q

# Pages HTML simples, sans Range ni CORS : http.server suffit (contrairement
# aux données pmtiles servies par data-serve).
site-serve:  ## Prévisualise le site vitrine (site/) sur 127.0.0.1:8500
	$(PY) -m http.server 8500 --bind 127.0.0.1 --directory site

fresh: db-up migrate data  ## De zéro à base peuplée (db + migrations + pipeline)
	@echo "Base prête. Exporter les artefacts : make export-statique"

# Expo Go n'embarque pas les modules natifs (MapLibre, view-shot) : ces
# cibles compilent un dev client local qui les inclut, seul moyen de tester
# la Carte. Nécessite un appareil/émulateur Android ou un simulateur iOS.
# JAVA_HOME forcé sur un JDK 17 : Gradle/AGP plantent sur un JDK trop récent
# (JvmVendorSpec ne connaît plus certains vendors attendus par le toolchain).
# Chemin détecté par wildcard : le nom du dossier varie selon la distro
# (Arch/Fedora : java-17-openjdk ; Debian/Ubuntu : java-17-openjdk-amd64).
JAVA17_HOME := $(firstword $(wildcard /usr/lib/jvm/java-17-openjdk /usr/lib/jvm/java-17-openjdk-amd64 /usr/lib/jvm/temurin-17-jdk-amd64))

# Démarre data-serve-lan en tâche de fond si le port 8400 est libre (test
# portable en Python pur — fonctionne aussi sous macOS pour mobile-dev-ios,
# contrairement à `ss`), et l'arrête à la sortie (trap). Si le port est déjà
# occupé (serveur lancé à la main dans un autre terminal), on ne touche à
# rien : évite un double-serveur qui échouerait sur le bind du port.
define LANCER_AVEC_DATA_SERVE
@test -d export || { echo "export/ absent — lancer : make export-statique" >&2; exit 1; }
@if $(PY) -c "import socket,sys; sys.exit(0 if socket.socket().connect_ex(('127.0.0.1',8400))==0 else 1)"; then \
	echo "Serveur de données déjà actif sur :8400 — réutilisation."; \
	$(1); \
else \
	$(PY) scripts/serve_export.py --dossier export --tiles tiles --port 8400 --hote 0.0.0.0 & \
	SERVER_PID=$$!; \
	trap "kill $$SERVER_PID 2>/dev/null" EXIT INT TERM; \
	$(1); \
fi
endef

mobile-dev-android:  ## Build + lance un dev client Android + le serveur de données local (data-serve-lan)
	@test -n "$(JAVA17_HOME)" || { echo "JDK 17 introuvable dans /usr/lib/jvm — installez-le (ex : jdk17-openjdk / openjdk-17-jdk) ou exportez JAVA_HOME manuellement" >&2; exit 1; }
	$(call LANCER_AVEC_DATA_SERVE,cd mobile && JAVA_HOME=$(JAVA17_HOME) npx expo run:android)

mobile-dev-ios:  ## Build + lance un dev client iOS + le serveur de données local (data-serve-lan)
	$(call LANCER_AVEC_DATA_SERVE,cd mobile && npx expo run:ios)
