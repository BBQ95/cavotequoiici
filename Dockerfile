# Image de l'API CaVoteQuoiIci (FastAPI, lecture seule).
#
# Ne contient que le service HTTP : le code de l'API, les modules pipeline légers
# qu'elle importe et leurs CSV de configuration (nuances / familles, ~8 Ko sous
# pipeline/config/). Le pipeline d'ingestion lourd (geopandas, tippecanoe, gros
# fichiers data/) reste hors image — c'est un travail de build, pas un service.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Dépendances runtime uniquement. psycopg2-binary + wheels → pas de compilateur.
COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

# Code servi : l'API et les modules pipeline (dont pipeline/config/*.csv) qu'elle
# importe au runtime. Le reste du dépôt (data/, tiles/, mobile/) est hors contexte
# grâce au .dockerignore.
COPY api/ api/
COPY pipeline/ pipeline/

EXPOSE 8200

# 0.0.0.0 à l'intérieur du conteneur ; l'exposition réseau est gérée en amont
# (compose, reverse-proxy). DATABASE_URL est fourni par l'environnement.
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8200"]
