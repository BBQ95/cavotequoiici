"""Pipeline complet, ordonné, de la base vide aux couleurs (Étapes 1→3).

Suppose la base migrée (`alembic upgrade head`). Enchaîne :
  1. contours des communes (télécharge si absent) ;
  2. ingestion des 4 scrutins du panier (chaque module télécharge sa source) ;
  3. calcul des couleurs (couleurs_scrutin + couleurs_ville).

Idempotent : chaque étape remplace ses données.

Usage :
    DATABASE_URL=... python -m pipeline.run_all
"""

from __future__ import annotations

import gzip
import shutil
import urllib.request
from pathlib import Path

from pipeline import compute_couleurs, load_communes
from pipeline.ingest import (
    europeennes_2024,
    legislatives_2024,
    municipales_2026,
    presidentielle_2022,
)

COMMUNES_GZ_URL = (
    "https://etalab-datasets.geo.data.gouv.fr/contours-administratifs/"
    "2024/geojson/communes-100m.geojson.gz"
)
COMMUNES_GEOJSON = "data/communes-100m.geojson"


def _assurer_contours() -> None:
    """Télécharge et décompresse les contours communes s'ils sont absents."""
    cible = Path(COMMUNES_GEOJSON)
    if cible.exists():
        return
    cible.parent.mkdir(parents=True, exist_ok=True)
    gz = cible.with_suffix(cible.suffix + ".gz")
    print(f"Téléchargement des contours → {gz} …")
    urllib.request.urlretrieve(COMMUNES_GZ_URL, gz)
    print(f"Décompression → {cible} …")
    with gzip.open(gz, "rb") as fin, open(cible, "wb") as fout:
        shutil.copyfileobj(fin, fout)


def main() -> None:
    etapes = [
        ("Contours communes", _then(_assurer_contours, load_communes.main)),
        ("Présidentielle 2022 T1", presidentielle_2022.main),
        ("Législatives 2024 T1", legislatives_2024.main),
        ("Européennes 2024", europeennes_2024.main),
        ("Municipales 2026 T1", municipales_2026.main),
        ("Calcul des couleurs", compute_couleurs.main),
    ]
    for i, (nom, fn) in enumerate(etapes, start=1):
        print(f"\n===== [{i}/{len(etapes)}] {nom} =====")
        fn()
    print("\n✅ Pipeline complet terminé.")


def _then(*fns):
    """Compose plusieurs fonctions sans argument en une seule."""

    def run():
        for f in fns:
            f()

    return run


if __name__ == "__main__":
    main()
