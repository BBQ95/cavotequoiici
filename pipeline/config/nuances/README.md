# Mapping nuances → familles (un fichier par scrutin)

Chaque scrutin a sa propre grille de nuances, **fixée par une circulaire/instruction datée
du ministère de l'Intérieur** (le Conseil d'État tranche les recours). On versionne donc
**un fichier CSV par scrutin**, nommé d'après son `scrutin_id` (cf. `poids_scrutins.yaml`) :

```
pipeline/config/nuances/<scrutin_id>.csv      ex. presidentielle_2022_t1.csv
```

## Schéma (colonnes)

```
nuance,famille,scrutin_type,annee,date_classification,date_debut,date_fin,source
```

| Colonne | Sens |
|---------|------|
| `nuance` | Code officiel de nuance (ou code parti/candidat pour la présidentielle) |
| `famille` | Famille de l'app (cf. `../familles.csv`) : extreme_gauche, gauche, ecologistes, centre, droite, extreme_droite, divers |
| `scrutin_type` | Type de scrutin (cf. `poids_type` dans `poids_scrutins.yaml`) |
| `annee` | Année du scrutin |
| `date_classification` | Date de la circulaire/instruction MI (ou décision CE) établissant cette grille |
| `date_debut` / `date_fin` | Intervalle de validité de la classification de cette nuance (vide = ouvert) |
| `source` | Référence officielle (Légifrance, n° décision CE, data.gouv.fr) — **audit public** |

> Pas de ligne de commentaire (`#`) dans les CSV : la doc vit ici. Le fichier est lu par
> `pipeline.ingest.common.charger_nuances`, qui valide que chaque `famille` existe dans `familles.csv`.

## Sources officielles datées (grilles de nuances)

| Scrutin | Document | Date | Référence |
|---------|----------|------|-----------|
| Présidentielle 2022 T1 | candidats nationaux (nuance = parti du candidat) | 2022-04-10 | data.gouv.fr |
| Législatives 2022 | circulaire « attribution des nuances » (18 nuances) | 2022-05-13 | Légifrance id/45336 (+ injonction CE NUPES, juin 2022) |
| Européennes 2024 | listes (nuance = parti/tête de liste) | 2024-06-09 | data.gouv.fr |
| Législatives 2024 | instruction « attribution des nuances » (24 nuances) | 2024-06-11 | Légifrance id/45565 |
| Municipales 2026 | circulaire « attribution des nuances » | 2026 | data.gouv.fr (classification à confirmer) |
| Précédent CE | circulaire municipales 2020 partiellement suspendue (seuil 9000 hab. ; « Debout la France » mal classé extrême droite) | 2020-01-31 | CE n° 437675 |

## Remarques de classification

- **LFI / FI** : classée « extrême gauche » dans certaines grilles récentes — point contesté
  (cf. contrôle du Conseil d'État). À documenter via `source` ligne par ligne.
- **Debout la France (DLF)** : le CE a jugé (2020) que la classer à l'extrême droite était une
  erreur manifeste → famille `droite`.
- **NUPES (2022)** : le CE a enjoint au MI d'ajouter la nuance ; les candidats restaient sinon
  ventilés en FI/SOC/VEC/COM.

### Municipales 2026 : agrégation des petites communes (< 1000 hab.)

Les communes de moins de 1 000 habitants (≈ 25 000 communes sur ~35 000 au total)
ont des candidats **nominatifs sans nuance officielle** : dans le fichier source
data.gouv.fr, les colonnes « Nuance liste N » sont vides pour ces communes.
Seul le nom du candidat et son nombre de voix sont renseignés.

**Décision éditoriale assumée** : toutes les voix nominatives des communes
< 1000 hab. sont agrégées sous la nuance `LUD` (sans étiquette) → famille `divers`.

**Impact** :
- La famille `divers` est **gonflée** dans tout le rural — elle agrège indistinctement
  des candidats de toutes obédiences (depuis l'ultra-gauche jusqu'à l'extrême droite)
  dès lors que la commune ne publie pas de nuance officielle.
- Cette agrégation n'affecte **que les municipales** (la présidentielle et les
  législatives publient toujours une nuance par candidat/liste).
- C'est un **choix conforme à la spec** : la spec exige que les communes
  < 1000 hab. soient *incluses* dans l'analyse (pas exclues), et la nuance `LUD`
  → `divers` est la seule option disponible dans la grille du MI pour les
  candidats sans étiquette. L'alternative (classifier manuellement ~25 000 candidats
  nominatifs) est hors périmètre de cette ingestion.

Voir aussi le commentaire dans `pipeline/ingest/municipales_2026.py` → `main()`,
étape 4, et la docstring de `parse_resultats_commune`.
