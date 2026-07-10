"""Tests du serveur statique de dev (scripts/serve_export.py) — TDD, sans BDD.

Ce serveur reproduit en local le contrat du CDN de prod : fichiers statiques
d'`export/` + tuiles sous `/tiles/`, avec support des requêtes Range
(obligatoire pour la lecture `pmtiles://` de MapLibre) et CORS. Les tests
n'utilisent que la stdlib : serveur réel sur un port éphémère + urllib.
"""

import threading
import urllib.error
import urllib.request

import pytest

from scripts.serve_export import creer_serveur, interpreter_range


class TestInterpreterRange:
    def test_plage_explicite(self):
        assert interpreter_range("bytes=2-5", 10) == (2, 5)

    def test_plage_ouverte_jusqu_a_la_fin(self):
        assert interpreter_range("bytes=4-", 10) == (4, 9)

    def test_suffixe_n_derniers_octets(self):
        """Forme `bytes=-n` : certains lecteurs pmtiles lisent l'en-tête en
        fin de fichier ainsi."""
        assert interpreter_range("bytes=-4", 10) == (6, 9)

    def test_fin_bornee_a_la_taille(self):
        assert interpreter_range("bytes=8-1000", 10) == (8, 9)

    def test_absent_ou_malformes_renvoient_none(self):
        """None = servir le fichier entier en 200 (pas d'erreur)."""
        assert interpreter_range(None, 10) is None
        assert interpreter_range("octets=0-1", 10) is None
        assert interpreter_range("bytes=abc-def", 10) is None
        assert interpreter_range("bytes=5-2", 10) is None
        assert interpreter_range("bytes=-", 10) is None
        # Plusieurs plages : non géré (MapLibre/pmtiles n'en émet qu'une).
        assert interpreter_range("bytes=0-1,4-5", 10) is None

    def test_insatisfaisable_renvoie_la_sentinelle_416(self):
        """Début au-delà du fichier (ou suffixe nul) : ValueError → 416."""
        with pytest.raises(ValueError):
            interpreter_range("bytes=10-", 10)
        with pytest.raises(ValueError):
            interpreter_range("bytes=-0", 10)


CONTENU = b"0123456789"
PMTILES = b"PMTiles-simulacre"


@pytest.fixture(scope="module")
def base_url(tmp_path_factory):
    """Serveur réel : export/ + tiles/ factices, port éphémère, thread démon."""
    racine = tmp_path_factory.mktemp("serve")
    export = racine / "export"
    (export / "meta").mkdir(parents=True)
    (export / "donnee.bin").write_bytes(CONTENU)
    (export / "meta" / "version.json").write_text('{"schema": 1}', "utf-8")
    tiles = racine / "tiles"
    tiles.mkdir()
    (tiles / "communes.pmtiles").write_bytes(PMTILES)

    serveur = creer_serveur(export, tiles, hote="127.0.0.1", port=0)
    thread = threading.Thread(target=serveur.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{serveur.server_address[1]}"
    serveur.shutdown()


def _get(url: str, **entetes) -> tuple[int, dict, bytes]:
    req = urllib.request.Request(url, headers=entetes)
    try:
        with urllib.request.urlopen(req) as rep:
            return rep.status, dict(rep.headers), rep.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


class TestServeurStatique:
    def test_get_complet_200_avec_cors_et_accept_ranges(self, base_url):
        statut, entetes, corps = _get(f"{base_url}/donnee.bin")
        assert statut == 200
        assert corps == CONTENU
        assert entetes["Accept-Ranges"] == "bytes"
        assert entetes["Access-Control-Allow-Origin"] == "*"

    def test_sous_dossier_export_servi(self, base_url):
        statut, _, corps = _get(f"{base_url}/meta/version.json")
        assert statut == 200
        assert b'"schema"' in corps

    def test_range_partiel_206(self, base_url):
        statut, entetes, corps = _get(f"{base_url}/donnee.bin", Range="bytes=2-5")
        assert statut == 206
        assert corps == CONTENU[2:6]
        assert entetes["Content-Range"] == f"bytes 2-5/{len(CONTENU)}"
        assert entetes["Content-Length"] == "4"

    def test_range_suffixe_206(self, base_url):
        statut, entetes, corps = _get(f"{base_url}/donnee.bin", Range="bytes=-4")
        assert statut == 206
        assert corps == CONTENU[-4:]
        assert entetes["Content-Range"] == f"bytes 6-9/{len(CONTENU)}"

    def test_range_insatisfaisable_416(self, base_url):
        statut, entetes, _ = _get(f"{base_url}/donnee.bin", Range="bytes=100-")
        assert statut == 416
        assert entetes["Content-Range"] == f"bytes */{len(CONTENU)}"

    def test_range_malforme_degrade_en_200(self, base_url):
        statut, _, corps = _get(f"{base_url}/donnee.bin", Range="bytes=zz")
        assert statut == 200
        assert corps == CONTENU

    def test_tiles_alias_vers_le_dossier_tuiles(self, base_url):
        """L'app lit `${DATA_URL}/tiles/communes.pmtiles` mais export/ ne
        contient pas les tuiles : /tiles/ est un alias vers tiles/ du dépôt."""
        statut, _, corps = _get(f"{base_url}/tiles/communes.pmtiles")
        assert statut == 200
        assert corps == PMTILES

    def test_tiles_avec_range(self, base_url):
        statut, entetes, corps = _get(
            f"{base_url}/tiles/communes.pmtiles", Range="bytes=0-6"
        )
        assert statut == 206
        assert corps == PMTILES[:7]
        assert entetes["Content-Range"] == f"bytes 0-6/{len(PMTILES)}"

    def test_chemin_inconnu_404(self, base_url):
        assert _get(f"{base_url}/inexistant.json")[0] == 404
        assert _get(f"{base_url}/tiles/inexistant.pmtiles")[0] == 404

    def test_pas_d_evasion_hors_des_dossiers(self, base_url):
        """`..` ne doit pas sortir d'export/ (SimpleHTTPRequestHandler
        neutralise déjà les traversées ; on le verrouille ici)."""
        statut, _, _ = _get(f"{base_url}/tiles/../donnee.bin")
        # urllib normalise déjà le chemin ; quel que soit le vainqueur,
        # on ne doit JAMAIS servir un fichier hors des deux dossiers.
        assert statut in (200, 404)
        statut, _, _ = _get(f"{base_url}/%2e%2e/secret.txt")
        assert statut == 404
