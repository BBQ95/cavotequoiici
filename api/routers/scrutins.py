"""Routeur scrutins : liste des scrutins inclus + détail par scrutin d'une commune.

À implémenter (piste Richard). Ce module est déjà enregistré dans api/main.py —
y ajouter les routes sans toucher à main.py ni aux autres fichiers partagés.

Routes attendues :
  GET /communes/{insee}/scrutins                  -> scrutins inclus + poids relatif
  GET /communes/{insee}/scrutins/{scrutin_id}     -> détail par famille + couleur du scrutin
"""

from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from api.db import get_conn
from api.schemas.scrutins import (
    CouleurScrutin,
    DetailScrutinResponse,
    FamilleVoix,
    ListeScrutinsResponse,
    ScrutinInclus,
)
from pipeline.ingest.common import charger_nuances
from pipeline.synthese import TYPE_VERS_POIDS

router = APIRouter(prefix="/communes", tags=["scrutins"])


# ---------------------------------------------------------------------------
# GET /communes/{insee}/scrutins
# ---------------------------------------------------------------------------

@router.get("/{insee}/scrutins", response_model=ListeScrutinsResponse)
def liste_scrutins(insee: str, conn=Depends(get_conn)):
    """Liste des scrutins inclus dans la synthèse de la commune avec leur poids relatif.

    Source : couleurs_ville.scrutins_inclus (JSON, liste de paires [type, poids_relatif])
    jointe à la table scrutins (id, type, date) pour la date.
    """
    row = conn.execute(
        text("SELECT scrutins_inclus FROM couleurs_ville WHERE code_insee = :insee"),
        {"insee": insee},
    ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Commune non trouvée")

    scrutins_inclus_raw = row[0]  # liste de paires [type_court, poids_relatif]

    # Récupérer la table scrutins pour faire la jointure type_court -> id + date
    scrutins_db = conn.execute(
        text("SELECT id, type, date FROM scrutins")
    ).fetchall()
    # Index : type_court -> (id, date)
    type_to_scrutin = {}
    for sid, type_long, d in scrutins_db:
        type_court = TYPE_VERS_POIDS.get(type_long)
        if type_court:
            type_to_scrutin[type_court] = (sid, str(d) if d else None)

    scrutins_list = []
    for pair in scrutins_inclus_raw:
        type_court, poids_relatif = pair[0], pair[1]
        info = type_to_scrutin.get(type_court)
        if info:
            sid, date_str = info
            scrutins_list.append(ScrutinInclus(
                scrutin_id=sid,
                type=type_court,
                date=date_str,
                poids_relatif=poids_relatif,
            ))

    return ListeScrutinsResponse(insee=insee, scrutins=scrutins_list)


# ---------------------------------------------------------------------------
# GET /communes/{insee}/scrutins/{scrutin_id}
# ---------------------------------------------------------------------------

@router.get("/{insee}/scrutins/{scrutin_id}", response_model=DetailScrutinResponse)
def detail_scrutin(insee: str, scrutin_id: str, conn=Depends(get_conn)):
    """Détail d'un scrutin pour la commune :
    - Répartition par famille politique (voix et pourcentage des exprimés)
    - Participation
    - Couleur du scrutin (l, c, h depuis couleurs_scrutin)
    """
    # Vérifier que la commune existe dans couleurs_ville
    commune = conn.execute(
        text("SELECT code_insee FROM couleurs_ville WHERE code_insee = :insee"),
        {"insee": insee},
    ).fetchone()
    if commune is None:
        raise HTTPException(status_code=404, detail="Commune non trouvée")

    # Couleur + participation du scrutin pour cette commune
    couleur_row = conn.execute(
        text(
            "SELECT l, c, h, participation FROM couleurs_scrutin "
            "WHERE code_insee = :insee AND scrutin_id = :sid"
        ),
        {"insee": insee, "sid": scrutin_id},
    ).fetchone()

    # Récupérer les résultats agrégés par nuance
    resultats = conn.execute(
        text(
            "SELECT nuance, voix, exprimes, inscrits "
            "FROM resultats_scrutin "
            "WHERE code_insee = :insee AND scrutin_id = :sid"
        ),
        {"insee": insee, "sid": scrutin_id},
    ).fetchall()

    if not resultats:
        # Pas de résultats pour ce couple (insee, scrutin_id)
        raise HTTPException(status_code=404, detail="Scrutin non trouvé pour cette commune")

    # couleurs_scrutin n'est écrite que pour exprimes > 0 ; une commune sans
    # suffrages exprimés a des résultats mais pas de couleur -> 404 maîtrisé
    # (évite un TypeError 500 en déréférençant couleur_row None).
    if couleur_row is None:
        raise HTTPException(
            status_code=404,
            detail="Aucune couleur pour ce scrutin (participation nulle)",
        )

    # Charger le mapping nuance -> famille (CSV daté du scrutin)
    try:
        mapping = charger_nuances(scrutin_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404, detail="Scrutin inconnu (mapping de nuances absent)"
        )

    # Agréger les voix par famille
    voix_par_famille: dict[str, int] = defaultdict(int)
    exprimes = resultats[0][2]  # exprimes est constant pour (insee, scrutin_id)

    for nuance, voix, _expr, _insc in resultats:
        famille = mapping.get(nuance)
        if famille:
            voix_par_famille[famille] += voix

    # Calculer les pourcentages
    familles_list = []
    for famille, voix in sorted(voix_par_famille.items(), key=lambda x: x[1], reverse=True):
        pourcentage = voix / exprimes if exprimes > 0 else 0.0
        familles_list.append(FamilleVoix(
            famille=famille,
            voix=voix,
            pourcentage=round(pourcentage, 6),
        ))

    # Couleur et participation
    couleur = CouleurScrutin(
        l=couleur_row[0],
        c=couleur_row[1],
        h=couleur_row[2],
    )
    participation = couleur_row[3]

    return DetailScrutinResponse(
        insee=insee,
        scrutin_id=scrutin_id,
        familles=familles_list,
        participation=participation,
        couleur=couleur,
    )
