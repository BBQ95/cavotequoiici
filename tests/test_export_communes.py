"""Tests unitaires pour pipeline/export_communes.py — export statique.

TDD strict : tests écrits avant l'implémentation. On couvre la logique pure
(construction des fiches, écriture des JSON, version, nuances, glyphes) ;
la requête PostGIS et l'écriture des ~35 000 fichiers réels sont des effets
de bord vérifiés à l'exécution réelle (`make export-statique`).
"""

import json
from pathlib import Path

import pytest

from pipeline.couleur import ALGOS, OKLCH, oklch_to_hex
from pipeline.export_communes import (
    SCHEMA_VERSION,
    construire_index,
    copier_glyphes,
    couleur_synthese,
    ecrire_fiches,
    entree_index,
    familles_depuis_resultats,
    fiche_statique,
    meta_version,
    scrutins_fiche,
)
from pipeline.normalisation import normaliser_nom

FONTS_SRC = Path(__file__).resolve().parent.parent / "pipeline" / "fonts"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _ligne(**overrides):
    """Une ligne type de la jointure communes × couleurs_ville (+ lat/lon)."""
    base = {
        "code_insee": "93066",
        "nom": "Saint-Denis",
        "departement": "Seine-Saint-Denis",
        "region": "Île-de-France",
        "population": 112091,
        "lat": 48.93,
        "lon": 2.35,
        "participation_mediane": 0.5123,
        "scrutins_inclus": [["presidentielle", 1.0], ["europeennes", 0.8]],
        "repartition": [
            {"famille": "gauche", "part": 0.41},
            {"famille": "extreme_gauche", "part": 0.22},
        ],
    }
    base.update(overrides)
    return base


def _lignes_algo(**overrides):
    """couleurs_ville_algo d'une commune : algo → {l, c, h, famille_dominante}."""
    base = {
        "complet": {"l": 0.72, "c": 0.10, "h": 28.8, "famille_dominante": "gauche"},
        "tendance": {"l": 0.70, "c": 0.12, "h": 30.0, "famille_dominante": "gauche"},
        "blocs": {"l": 0.68, "c": 0.14, "h": 25.0, "famille_dominante": "extreme_gauche"},
    }
    base.update(overrides)
    return base


class TestCouleurSynthese:
    def test_hex_depuis_oklch_de_l_algo(self):
        """Le hex servi est exactement l'OKLCH de l'algo converti — même
        source unique (`oklch_to_hex`) que l'endpoint fiche."""
        c = couleur_synthese(_ligne(), "tendance", _lignes_algo()["tendance"])
        assert c.hex == oklch_to_hex(OKLCH(L=0.70, C=0.12, H=30.0))
        assert (c.l, c.c, c.h) == (0.70, 0.12, 30.0)

    def test_algo_et_famille_dominante_de_l_algo(self):
        c = couleur_synthese(_ligne(), "blocs", _lignes_algo()["blocs"])
        assert c.algo == "blocs"
        assert c.famille_dominante == "extreme_gauche"

    def test_scrutins_inclus_et_participation_transmis(self):
        c = couleur_synthese(_ligne(), "complet", _lignes_algo()["complet"])
        assert c.scrutins_inclus == [("presidentielle", 1.0), ("europeennes", 0.8)]
        assert c.participation_mediane == 0.5123

    def test_repartition_en_chaine_json_est_decodee(self):
        """Selon le driver, les colonnes JSON lues via text() brut peuvent
        revenir en chaîne — même tolérance que l'API (pipeline.jsoncol)."""
        row = _ligne(
            repartition='[{"famille": "gauche", "part": 0.41}]',
            scrutins_inclus='[["presidentielle", 1.0]]',
        )
        c = couleur_synthese(row, "complet", _lignes_algo()["complet"])
        assert c.repartition[0].famille == "gauche"
        assert c.scrutins_inclus == [("presidentielle", 1.0)]


class TestFicheStatique:
    def test_metadonnees_transmises(self):
        fiche = fiche_statique(_ligne(), _lignes_algo())
        assert fiche["code_insee"] == "93066"
        assert fiche["nom"] == "Saint-Denis"
        assert fiche["departement"] == "Seine-Saint-Denis"
        assert fiche["region"] == "Île-de-France"
        assert fiche["population"] == 112091
        assert fiche["lat"] == 48.93
        assert fiche["lon"] == 2.35

    def test_une_couleur_par_algo(self):
        fiche = fiche_statique(_ligne(), _lignes_algo())
        assert set(fiche["couleurs"]) == set(ALGOS)

    def test_couleurs_differentes_selon_l_algo(self):
        fiche = fiche_statique(_ligne(), _lignes_algo())
        assert fiche["couleurs"]["tendance"]["hex"] != fiche["couleurs"]["blocs"]["hex"]
        assert fiche["couleurs"]["tendance"]["algo"] == "tendance"

    def test_algo_manquant_echoue_explicitement(self):
        """Une base pas recalculée (couleurs_ville_algo incomplète) doit faire
        échouer l'export, pas produire des fiches silencieusement partielles."""
        lignes = _lignes_algo()
        del lignes["blocs"]
        with pytest.raises(RuntimeError, match="compute_couleurs"):
            fiche_statique(_ligne(), lignes)

    def test_serialisable_en_json(self):
        fiche = fiche_statique(_ligne(), _lignes_algo())
        rechargee = json.loads(json.dumps(fiche, ensure_ascii=False))
        assert rechargee["couleurs"]["complet"]["famille_dominante"] == "gauche"


class TestEcrireFiches:
    def _fiches(self):
        return [
            fiche_statique(_ligne(), _lignes_algo()),
            fiche_statique(_ligne(code_insee="75056", nom="Paris"), _lignes_algo()),
        ]

    def test_un_fichier_json_par_commune(self, tmp_path):
        n = ecrire_fiches(iter(self._fiches()), tmp_path / "communes")
        assert n == 2
        assert (tmp_path / "communes" / "93066.json").exists()
        assert (tmp_path / "communes" / "75056.json").exists()

    def test_contenu_relisible_et_utf8(self, tmp_path):
        ecrire_fiches(iter(self._fiches()), tmp_path / "communes")
        fiche = json.loads((tmp_path / "communes" / "93066.json").read_text("utf-8"))
        assert fiche["region"] == "Île-de-France"
        assert fiche["couleurs"]["complet"]["hex"].startswith("#")

    def test_purge_les_fichiers_obsoletes(self, tmp_path):
        """Une commune disparue entre deux exports ne doit pas laisser un JSON
        périmé (rclone sync le republierait)."""
        dossier = tmp_path / "communes"
        dossier.mkdir(parents=True)
        (dossier / "99999.json").write_text("{}")
        ecrire_fiches(iter(self._fiches()), dossier)
        assert not (dossier / "99999.json").exists()

    def test_aucun_residu_temporaire(self, tmp_path):
        ecrire_fiches(iter(self._fiches()), tmp_path / "communes")
        assert list(tmp_path.rglob("*.tmp")) == []

    def test_echec_en_cours_laisse_le_dossier_precedent_intact(self, tmp_path):
        """Un crash au milieu des ~35 000 écritures (minutes) ne doit jamais
        laisser un dossier tronqué sous son nom final : l'export précédent
        reste servi tel quel jusqu'au swap."""
        dossier = tmp_path / "communes"
        dossier.mkdir(parents=True)
        (dossier / "93066.json").write_text('{"precedent":true}')

        def fiches_qui_cassent():
            yield fiche_statique(_ligne(), _lignes_algo())
            raise RuntimeError("BDD perdue en cours d'itération")

        with pytest.raises(RuntimeError, match="BDD perdue"):
            ecrire_fiches(fiches_qui_cassent(), dossier)
        assert json.loads((dossier / "93066.json").read_text()) == {"precedent": True}

    def test_nettoie_un_temporaire_preexistant(self, tmp_path):
        """Reliquat d'un crash précédent : le dossier tampon est reconstruit
        de zéro, pas fusionné."""
        dossier = tmp_path / "communes"
        tampon = tmp_path / "communes.tmp"
        tampon.mkdir(parents=True)
        (tampon / "99999.json").write_text("{}")
        ecrire_fiches(iter(self._fiches()), dossier)
        assert not tampon.exists()
        assert not (dossier / "99999.json").exists()


class TestMetaVersion:
    def test_champs(self):
        meta = meta_version(
            nb_communes=35012,
            scrutins=["europeennes_2024", "presidentielle_2022"],
            genere_le="2026-07-10T12:00:00+00:00",
            nb_index=35012,
        )
        assert meta["schema"] == SCHEMA_VERSION
        assert meta["genere_le"] == "2026-07-10T12:00:00+00:00"
        assert meta["nb_communes"] == 35012
        assert meta["algos"] == list(ALGOS)
        assert meta["scrutins"] == ["europeennes_2024", "presidentielle_2022"]
        assert meta["nb_index"] == 35012


class TestCopierGlyphes:
    def test_copie_pbf_et_licence(self, tmp_path):
        dest = tmp_path / "fonts"
        n = copier_glyphes(FONTS_SRC, dest)
        assert (dest / "Noto Sans Medium" / "0-255.pbf").exists()
        assert (dest / "Noto Sans Medium" / "256-511.pbf").exists()
        # La licence OFL doit accompagner les glyphes redistribués.
        assert (dest / "OFL.txt").exists()
        assert n == 2

    def test_n_embarque_pas_le_readme(self, tmp_path):
        """Le README du dossier est de la doc dépôt, pas un artefact à servir."""
        dest = tmp_path / "fonts"
        copier_glyphes(FONTS_SRC, dest)
        assert not (dest / "README.md").exists()


# --- Scrutins embarqués dans la fiche (bascule statique de l'encart Transparence) ---


def _scrutins_meta():
    """Table scrutins jointe TYPE_LONG_VERS_COURT : type court → (scrutin_id, date)."""
    return {
        "presidentielle": ("presidentielle_2022_t1", "2022-04-10"),
        "europeennes": ("europeennes_2024", "2024-06-09"),
    }


def _couleurs_scrutin_commune():
    """couleurs_scrutin de la commune : scrutin_id → l/c/h/participation."""
    return {
        "presidentielle_2022_t1": {"l": 0.62, "c": 0.11, "h": 22.0, "participation": 0.7512},
    }


def _familles_commune():
    """Familles agrégées de la commune : scrutin_id → liste FamilleVoix."""
    return {
        "presidentielle_2022_t1": [
            {"famille": "gauche", "voix": 1200, "pourcentage": 0.5},
            {"famille": "extreme_droite", "voix": 900, "pourcentage": 0.375},
        ],
    }


class TestFamillesDepuisResultats:
    def test_agrege_les_voix_par_famille(self):
        lignes = [("LFI", 800, 2400), ("PS", 400, 2400), ("RN", 900, 2400)]
        mapping = {"LFI": "gauche", "PS": "gauche", "RN": "extreme_droite"}
        familles = familles_depuis_resultats(lignes, mapping)
        assert familles[0] == {"famille": "gauche", "voix": 1200, "pourcentage": 0.5}
        assert familles[1] == {"famille": "extreme_droite", "voix": 900, "pourcentage": 0.375}

    def test_nuance_non_mappee_ignoree(self):
        """Parité routeur scrutins : une nuance absente du CSV n'émet rien."""
        familles = familles_depuis_resultats([("XYZ", 100, 200)], {})
        assert familles == []

    def test_pourcentage_arrondi_six_decimales(self):
        familles = familles_depuis_resultats([("LFI", 1, 3)], {"LFI": "gauche"})
        assert familles[0]["pourcentage"] == round(1 / 3, 6)

    def test_exprimes_nuls_pourcentage_zero(self):
        """Parité routeur : exprimes == 0 → pourcentage 0.0 (pas de division)."""
        familles = familles_depuis_resultats([("LFI", 0, 0)], {"LFI": "gauche"})
        assert familles[0]["pourcentage"] == 0.0

    def test_tri_voix_decroissantes_puis_famille(self):
        lignes = [("A", 100, 400), ("B", 200, 400), ("C", 100, 400)]
        mapping = {"A": "gauche", "B": "droite", "C": "centre"}
        familles = familles_depuis_resultats(lignes, mapping)
        assert [f["famille"] for f in familles] == ["droite", "centre", "gauche"]


class TestScrutinsFiche:
    def test_entree_parite_endpoint_scrutins(self):
        """Chaque entrée porte les champs de ScrutinInclus (mêmes valeurs que
        GET /communes/{insee}/scrutins) + le détail embarqué."""
        entrees = scrutins_fiche(
            _ligne(), _scrutins_meta(), _couleurs_scrutin_commune(), _familles_commune()
        )
        assert [e["scrutin_id"] for e in entrees] == [
            "presidentielle_2022_t1",
            "europeennes_2024",
        ]
        premier = entrees[0]
        assert premier["type"] == "presidentielle"
        assert premier["date"] == "2022-04-10"
        assert premier["poids_relatif"] == 1.0

    def test_detail_parite_endpoint_detail(self):
        """Le détail embarqué = la réponse de GET /communes/{insee}/scrutins/{id}."""
        entrees = scrutins_fiche(
            _ligne(), _scrutins_meta(), _couleurs_scrutin_commune(), _familles_commune()
        )
        detail = entrees[0]["detail"]
        assert detail["insee"] == "93066"
        assert detail["scrutin_id"] == "presidentielle_2022_t1"
        assert detail["participation"] == 0.7512
        assert detail["couleur"] == {"l": 0.62, "c": 0.11, "h": 22.0}
        assert detail["familles"][0]["famille"] == "gauche"

    def test_detail_null_sans_couleur(self):
        """Parité avec le 404 maîtrisé du routeur : pas de ligne couleurs_scrutin
        (participation nulle) → detail null, pas de fiche en erreur."""
        entrees = scrutins_fiche(
            _ligne(), _scrutins_meta(), _couleurs_scrutin_commune(), _familles_commune()
        )
        assert entrees[1]["scrutin_id"] == "europeennes_2024"
        assert entrees[1]["detail"] is None

    def test_type_hors_table_scrutins_ignore(self):
        """Parité routeur : un type de scrutins_inclus absent de la table
        scrutins n'émet pas d'entrée."""
        row = _ligne(scrutins_inclus=[["presidentielle", 1.0], ["cantonales", 0.4]])
        entrees = scrutins_fiche(
            row, _scrutins_meta(), _couleurs_scrutin_commune(), _familles_commune()
        )
        assert [e["type"] for e in entrees] == ["presidentielle"]

    def test_scrutins_inclus_en_chaine_json(self):
        """Colonne JSON revenue en chaîne selon le driver — même tolérance
        que le reste de l'export."""
        row = _ligne(scrutins_inclus='[["presidentielle", 1.0]]')
        entrees = scrutins_fiche(
            row, _scrutins_meta(), _couleurs_scrutin_commune(), _familles_commune()
        )
        assert len(entrees) == 1

    def test_fiche_statique_embarque_les_scrutins(self):
        entrees = scrutins_fiche(
            _ligne(), _scrutins_meta(), _couleurs_scrutin_commune(), _familles_commune()
        )
        fiche = fiche_statique(_ligne(), _lignes_algo(), scrutins=entrees)
        assert fiche["scrutins"] == entrees
        json.dumps(fiche, ensure_ascii=False)  # sérialisable

    def test_fiche_statique_sans_scrutins_liste_vide(self):
        """La clé existe toujours (contrat client statique), même vide."""
        assert fiche_statique(_ligne(), _lignes_algo())["scrutins"] == []


# --- Index de recherche statique (recherche + géolocalisation côté client) ---


class TestEntreeIndex:
    def test_format_compact(self):
        """[insee, nom, dpt, lat, lon, [hex×algos], [famille indexée×algos]]."""
        legende = {"gauche": 0, "extreme_gauche": 1}
        e = entree_index(_ligne(), _lignes_algo(), legende)
        assert e[0] == "93066"
        assert e[1] == "Saint-Denis"
        assert e[2] == "Seine-Saint-Denis"
        assert e[3] == 48.93
        assert e[4] == 2.35
        assert e[5] == [
            oklch_to_hex(OKLCH(L=0.72, C=0.10, H=28.8)),
            oklch_to_hex(OKLCH(L=0.70, C=0.12, H=30.0)),
            oklch_to_hex(OKLCH(L=0.68, C=0.14, H=25.0)),
        ]
        assert e[6] == [0, 0, 1]  # complet/tendance=gauche, blocs=extreme_gauche

    def test_lat_lon_arrondis_cinq_decimales(self):
        """~1 m de précision suffit pour la géoloc ; économise l'index."""
        e = entree_index(_ligne(lat=48.9312345678, lon=2.3512345678), _lignes_algo(), {})
        assert e[3] == 48.93123
        assert e[4] == 2.35123

    def test_famille_absente_nulle(self):
        lignes = _lignes_algo()
        lignes["blocs"] = {**lignes["blocs"], "famille_dominante": None}
        e = entree_index(_ligne(), lignes, {"gauche": 0})
        assert e[6][2] is None

    def test_algo_manquant_echoue(self):
        lignes = _lignes_algo()
        del lignes["tendance"]
        with pytest.raises(RuntimeError, match="compute_couleurs"):
            entree_index(_ligne(), lignes, {})


class TestConstruireIndex:
    def test_structure_et_legende(self):
        index = construire_index(
            [(_ligne(), _lignes_algo()), (_ligne(code_insee="75056", nom="Paris"), _lignes_algo())]
        )
        assert set(index) == {"algos", "familles", "communes"}
        assert index["algos"] == list(ALGOS)
        assert len(index["communes"]) == 2
        # Chaque indice de famille pointe dans la légende.
        for entree in index["communes"]:
            for i in entree[6]:
                assert i is None or 0 <= i < len(index["familles"])

    def test_legende_couvre_les_familles_dominantes(self):
        index = construire_index([(_ligne(), _lignes_algo())])
        familles = index["familles"]
        e = index["communes"][0]
        assert familles[e[6][0]] == "gauche"
        assert familles[e[6][2]] == "extreme_gauche"

    def test_serialisable_json(self):
        index = construire_index([(_ligne(), _lignes_algo())])
        json.loads(json.dumps(index, ensure_ascii=False))


class TestFixturesNormalisation:
    def test_fixtures_a_jour(self):
        """Le fichier de parité consommé par le test TS du mobile doit refléter
        normaliser_nom : s'il casse ici, régénérer les sorties attendues."""
        cas = json.loads((FIXTURES / "normalisation_parite.json").read_text("utf-8"))["cas"]
        assert len(cas) >= 10
        for c in cas:
            assert normaliser_nom(c["entree"]) == c["attendu"], c["entree"]


class TestFixtureOrdreRecherche:
    def test_fixtures_a_jour(self):
        """L'ordre d'affichage de la recherche n'a plus qu'une définition
        vivante : `comparerCommunes` côté mobile (l'ORDER BY de l'API a disparu
        avec elle). Ce test garde la fixture alignée sur la référence Python ;
        le test Node vérifie que `comparerCommunes` produit le même ordre.

        Comparaison BINAIRE (points de code), jamais de locale : identique à
        l'ordre UTF-16 de JS car tous les caractères des noms de communes
        français sont dans le BMP (aucune paire de substitution). Clé = nom
        normalisé, tiebreak = nom brut — le miroir exact de comparerCommunes.
        """
        noms = json.loads(
            (FIXTURES / "recherche_ordre_parite.json").read_text("utf-8")
        )["noms"]
        assert len(noms) >= 10
        assert sorted(noms, key=lambda n: (normaliser_nom(n), n)) == noms
