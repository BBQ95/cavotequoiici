"""Tests du site vitrine statique (site/) publié sur l'apex cavotequoiici.fr.

Le site est un prérequis des stores : la politique de confidentialité doit
être en ligne sur https://cavotequoiici.fr/confidentialite (déclarée dans la
Play Console). Ces tests verrouillent les engagements du texte (aucune
collecte, rétention 10 jours, contact) et l'absence de tout traceur : le site
doit rester aussi statique et sobre que l'app.
"""

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

import pytest

SITE = Path(__file__).resolve().parents[1] / "site"
PAGES = {
    "index": SITE / "index.html",
    "confidentialite": SITE / "confidentialite" / "index.html",
}

# Seules origines externes tolérées dans les liens (aucune ressource — CSS,
# image, script — ne doit être chargée depuis un domaine tiers).
DOMAINES_LIENS_AUTORISES = {
    "github.com",
    "www.data.gouv.fr",
    "www.cnil.fr",
    "geoservices.ign.fr",
    "data.cavotequoiici.fr",
}


class _Collecteur(HTMLParser):
    """Collecte les balises, attributs href/src et le texte d'une page."""

    def __init__(self) -> None:
        super().__init__()
        self.balises: list[str] = []
        self.liens: list[str] = []  # valeurs href
        self.ressources: list[str] = []  # valeurs src + <link href>
        self.attrs_html: dict[str, str] = {}
        self.texte: list[str] = []

    def handle_starttag(self, tag, attrs):
        self.balises.append(tag)
        d = dict(attrs)
        if tag == "html":
            self.attrs_html = d
        if tag == "link" and d.get("href"):
            self.ressources.append(d["href"])
        elif d.get("href"):
            self.liens.append(d["href"])
        if d.get("src"):
            self.ressources.append(d["src"])

    def handle_data(self, data):
        self.texte.append(data)


def _page(nom: str) -> tuple[_Collecteur, str]:
    brut = PAGES[nom].read_text(encoding="utf-8")
    p = _Collecteur()
    p.feed(brut)
    return p, brut


@pytest.mark.parametrize("nom", sorted(PAGES))
def test_page_existe_et_est_en_francais(nom):
    assert PAGES[nom].is_file(), f"page manquante : {PAGES[nom]}"
    p, brut = _page(nom)
    assert p.attrs_html.get("lang") == "fr"
    assert "title" in p.balises
    assert '<meta charset="utf-8"' in brut.lower()
    assert 'name="viewport"' in brut


@pytest.mark.parametrize("nom", sorted(PAGES))
def test_aucun_script_ni_traceur(nom):
    """Engagement de la politique : pas de traceurs. Le site n'a aucun JS."""
    p, _ = _page(nom)
    assert "script" not in p.balises
    assert "iframe" not in p.balises


@pytest.mark.parametrize("nom", sorted(PAGES))
def test_ressources_locales_et_liens_maitrises(nom):
    p, _ = _page(nom)
    for res in p.ressources:
        assert not urlparse(res).netloc, f"ressource externe interdite : {res}"
    for lien in p.liens:
        u = urlparse(lien)
        if u.scheme == "mailto":
            continue
        if u.netloc:
            assert u.scheme == "https", f"lien externe non https : {lien}"
            assert u.netloc in DOMAINES_LIENS_AUTORISES, (
                f"domaine externe non listé : {lien}"
            )


@pytest.mark.parametrize("nom", sorted(PAGES))
def test_liens_et_ressources_internes_resolvent(nom):
    """Tout href/src relatif doit pointer un fichier existant du site."""
    p, _ = _page(nom)
    for cible in p.liens + p.ressources:
        u = urlparse(cible)
        if u.scheme or u.netloc or cible.startswith("#"):
            continue
        chemin = u.path
        base = SITE if chemin.startswith("/") else PAGES[nom].parent
        fichier = base / chemin.lstrip("/")
        if chemin.endswith("/") or fichier.is_dir():
            fichier = fichier / "index.html"
        assert fichier.is_file(), f"lien interne cassé dans {nom} : {cible}"


def test_index_contenu_essentiel():
    p, brut = _page("index")
    texte = " ".join(p.texte)
    assert "CaVoteQuoiIci" in texte
    assert "AGPL" in texte
    assert "https://github.com/BBQ95/cavotequoiici" in p.liens
    assert "mailto:contact@cavotequoiici.fr" in p.liens
    # L'accueil doit mener à la politique de confidentialité.
    assert any(
        "confidentialite" in lien for lien in p.liens
    ), "l'accueil ne pointe pas vers /confidentialite"


@pytest.mark.parametrize("nom", sorted(PAGES))
def test_emails_proteges_des_reecritures_cloudflare(nom):
    """L'obfuscation d'emails Cloudflare injecte un script de décodage que
    notre CSP (aucun script) bloque — les adresses resteraient masquées.
    Chaque occurrence de l'adresse doit être entre <!--email_off--> et
    <!--/email_off--> pour que Cloudflare la laisse intacte, sans désactiver
    la fonctionnalité sur le reste de la zone."""
    brut = PAGES[nom].read_text(encoding="utf-8")
    email = "contact@cavotequoiici.fr"
    assert email in brut
    zones = []
    debut = 0
    while (ouv := brut.find("<!--email_off-->", debut)) != -1:
        fer = brut.find("<!--/email_off-->", ouv)
        assert fer != -1, "marqueur email_off ouvert mais jamais fermé"
        zones.append((ouv, fer))
        debut = fer + 1
    pos = 0
    while (i := brut.find(email, pos)) != -1:
        assert any(o < i < f for o, f in zones), (
            f"occurrence de {email} hors marqueurs email_off (offset {i})"
        )
        pos = i + 1


def test_headers_pages_csp():
    """_headers (Cloudflare Pages) : la CSP est un point sensible vie privée —
    verrouiller sa présence et l'absence d'unsafe-inline (remarque Fred #79)."""
    contenu = (SITE / "_headers").read_text(encoding="utf-8")
    assert "Content-Security-Policy:" in contenu
    assert "default-src 'none'" in contenu
    assert "unsafe-inline" not in contenu
    assert "X-Content-Type-Options: nosniff" in contenu


def test_politique_engagements():
    """Le texte publié doit porter les engagements actés (doc Outline)."""
    p, brut = _page("confidentialite")
    texte = " ".join(p.texte)
    assert "ne collecte aucune donnée personnelle" in texte
    assert "10 jours" in texte
    assert "contact@cavotequoiici.fr" in texte
    assert "data.cavotequoiici.fr" in texte
    assert "Data Privacy Framework" in texte
    assert "cnil" in texte.lower()
    assert "AGPL" in texte
    # La date de publication doit être renseignée (pas de placeholder).
    assert "⚠️" not in brut and "[date" not in brut
    assert "Dernière mise à jour" in texte
