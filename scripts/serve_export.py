"""Serveur statique de développement — miroir local du CDN de prod.

Sert `export/` (fiches, index, nuances, version, glyphes) et monte le dossier
`tiles/` du dépôt sous `/tiles/` (l'app lit `${EXPO_PUBLIC_DATA_URL}/tiles/
communes.pmtiles`, mais l'export ne contient pas les tuiles — et ne doit pas
les contenir : `export/` est synchronisé tel quel vers R2).

Deux exigences du contrat CDN que `python -m http.server` ne remplit pas :
- les requêtes **Range** (206) — indispensables à la lecture `pmtiles://`
  de MapLibre ; sans elles la carte est cassée en silence ;
- **CORS** (`expo export --platform web`, débogage navigateur).

Stdlib uniquement : ce script doit survivre au retrait des dépendances de
l'API (uvicorn/starlette). Usage : `make data-serve` / `make data-serve-lan`.
"""

from __future__ import annotations

import argparse
import os
import re
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

_RANGE = re.compile(r"^bytes=(\d*)-(\d*)$")


def interpreter_range(entete: str | None, taille: int) -> tuple[int, int] | None:
    """Interprète un en-tête `Range` pour un fichier de `taille` octets.

    Renvoie `(debut, fin)` inclusifs, `None` si l'en-tête est absent ou
    illisible (→ répondre 200 avec le fichier entier, comme le veut la RFC
    9110 pour un Range invalide), et lève `ValueError` si la plage est
    syntaxiquement valide mais insatisfaisable (→ 416). Une seule plage est
    gérée : les lecteurs pmtiles n'en émettent jamais plusieurs.
    """
    if entete is None:
        return None
    m = _RANGE.match(entete.strip())
    if m is None:
        return None
    debut_s, fin_s = m.groups()
    if not debut_s and not fin_s:  # « bytes=- »
        return None
    if not debut_s:  # suffixe « bytes=-n » : les n derniers octets
        n = int(fin_s)
        if n == 0 or taille == 0:
            raise ValueError(f"plage insatisfaisable : {entete} (taille {taille})")
        return max(taille - n, 0), taille - 1
    debut = int(debut_s)
    if debut >= taille:
        raise ValueError(f"plage insatisfaisable : {entete} (taille {taille})")
    fin = min(int(fin_s), taille - 1) if fin_s else taille - 1
    if fin < debut:
        return None
    return debut, fin


class ServeurExportHandler(SimpleHTTPRequestHandler):
    """`SimpleHTTPRequestHandler` + Range, CORS et alias `/tiles/`."""

    protocol_version = "HTTP/1.1"  # keep-alive : MapLibre enchaîne les Range

    def __init__(self, *args, dossier_tiles: str, **kwargs):
        self.dossier_tiles = dossier_tiles
        super().__init__(*args, **kwargs)

    def translate_path(self, path: str) -> str:
        """Résolution standard (neutralise `..` et `%xx`) puis remap de la
        première composante `tiles/` vers le dossier des tuiles du dépôt."""
        chemin = super().translate_path(path)
        rel = os.path.relpath(chemin, self.directory)
        if rel == "tiles" or rel.startswith("tiles" + os.sep):
            return os.path.join(self.dossier_tiles, rel[len("tiles") :].lstrip(os.sep))
        return chemin

    def end_headers(self):
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def do_GET(self):
        self._repondre(envoyer_corps=True)

    def do_HEAD(self):
        self._repondre(envoyer_corps=False)

    def _repondre(self, envoyer_corps: bool):
        chemin = self.translate_path(self.path)
        if os.path.isdir(chemin):
            # Le CDN ne liste pas les dossiers : pas d'index HTML ici non plus.
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            f = open(chemin, "rb")
        except OSError:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        with f:
            taille = os.fstat(f.fileno()).st_size
            try:
                plage = interpreter_range(self.headers.get("Range"), taille)
            except ValueError:
                self.send_response(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
                self.send_header("Content-Range", f"bytes */{taille}")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            self.send_response(HTTPStatus.PARTIAL_CONTENT if plage else HTTPStatus.OK)
            self.send_header("Content-Type", self.guess_type(chemin))
            if plage is None:
                debut, longueur = 0, taille
            else:
                debut, fin = plage
                longueur = fin - debut + 1
                self.send_header("Content-Range", f"bytes {debut}-{fin}/{taille}")
            self.send_header("Content-Length", str(longueur))
            self.end_headers()
            if envoyer_corps:
                f.seek(debut)
                restant = longueur
                while restant > 0:
                    bloc = f.read(min(64 * 1024, restant))
                    if not bloc:
                        break
                    self.wfile.write(bloc)
                    restant -= len(bloc)

    def copyfile(self, source, outputfile):  # pragma: no cover — plus utilisé
        raise NotImplementedError("passer par _repondre")


def creer_serveur(
    dossier_export: Path, dossier_tiles: Path, hote: str = "127.0.0.1", port: int = 8400
) -> ThreadingHTTPServer:
    """Serveur threadé prêt à `serve_forever()` (port 0 = éphémère, tests)."""
    handler = partial(
        ServeurExportHandler,
        directory=str(dossier_export),
        dossier_tiles=str(dossier_tiles),
    )
    return ThreadingHTTPServer((hote, port), handler)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--dossier", type=Path, default=Path("export"), help="racine servie")
    p.add_argument("--tiles", type=Path, default=Path("tiles"), help="alias /tiles/")
    p.add_argument("--hote", default="127.0.0.1", help="0.0.0.0 pour le LAN (device)")
    p.add_argument("--port", type=int, default=8400)
    args = p.parse_args()
    serveur = creer_serveur(args.dossier, args.tiles, args.hote, args.port)
    print(
        f"Données statiques : http://{args.hote}:{args.port} "
        f"(export : {args.dossier}/, tuiles : {args.tiles}/ sous /tiles/) — Ctrl-C pour arrêter"
    )
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
