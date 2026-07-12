#!/usr/bin/env bash
# Déploie le site vitrine (site/) sur Cloudflare Pages, servi sur l'apex
# https://cavotequoiici.fr (+ politique de confidentialité /confidentialite).
#
# Prérequis (une seule fois, à la main) :
#   1. wrangler installé (https://developers.cloudflare.com/workers/wrangler/) ;
#   2. secrets dans ~/.config/cloudflare.env (chmod 600, hors Syncthing) :
#      CLOUDFLARE_API_TOKEN (permission « Cloudflare Pages: Edit » requise)
#      et CLOUDFLARE_ACCOUNT_ID ;
#   3. projet Pages créé :
#        wrangler pages project create cavotequoiici-site --production-branch main
#   4. domaine apex rattaché au projet (Dashboard → Workers & Pages →
#      cavotequoiici-site → Custom domains → cavotequoiici.fr). La zone DNS
#      est déjà chez Cloudflare (cf. runbook « Hébergement statique »).
#
# Usage : infra/deploy-site.sh
# Le déploiement en production est une action délibérée, à lancer par un humain
# (même règle que le dispatch de data-release.yml).

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SITE_DIR="$REPO_DIR/site"
PROJET="cavotequoiici-site"
ENV_FILE="${CLOUDFLARE_ENV_FILE:-$HOME/.config/cloudflare.env}"

[ -d "$SITE_DIR" ] || { echo "Dossier introuvable : $SITE_DIR" >&2; exit 1; }
command -v wrangler >/dev/null || { echo "wrangler introuvable dans le PATH" >&2; exit 1; }

if [ -f "$ENV_FILE" ]; then
    # shellcheck disable=SC1090
    set -a; . "$ENV_FILE"; set +a
fi
: "${CLOUDFLARE_API_TOKEN:?CLOUDFLARE_API_TOKEN absent (attendu dans $ENV_FILE)}"
: "${CLOUDFLARE_ACCOUNT_ID:?CLOUDFLARE_ACCOUNT_ID absent (attendu dans $ENV_FILE)}"

# Garde-fou : les tests du site verrouillent la politique de confidentialité
# (engagements, liens internes, absence de traceurs) — ne rien publier qui ne
# les passe pas.
"$REPO_DIR/.venv/bin/python" -m pytest -q "$REPO_DIR/tests/test_site.py"

wrangler pages deploy "$SITE_DIR" \
    --project-name "$PROJET" \
    --commit-dirty=true

echo
echo "Déployé. Vérifier : https://cavotequoiici.fr et https://cavotequoiici.fr/confidentialite"
