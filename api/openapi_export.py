"""Exporte le schéma OpenAPI de l'API vers un fichier JSON.

Sert à générer les types TypeScript du mobile sans serveur en marche :
    python -m api.openapi_export [chemin_sortie]
    npx openapi-typescript openapi.json -o mobile/src/api/types.ts
"""

from __future__ import annotations

import json
import sys

from api.main import app


def main() -> None:
    sortie = sys.argv[1] if len(sys.argv) > 1 else "openapi.json"
    with open(sortie, "w", encoding="utf-8") as f:
        json.dump(app.openapi(), f, ensure_ascii=False, indent=2)
    print(f"OpenAPI exporté → {sortie}")


if __name__ == "__main__":
    main()
