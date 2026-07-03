# Méthodologie — comment la couleur d'une commune est calculée

> Ce document est l'engagement du [contrat d'honnêteté](../README.md#le-contrat-dhonnêteté) :
> la couleur n'est **jamais une boîte noire**. Tout ce qui suit est implémenté dans le code
> public de ce dépôt ; les paramètres cités vivent dans des fichiers de configuration
> versionnés, listés [en fin de document](#où-sont-les-paramètres).

## Ce que la couleur dit — et ce qu'elle ne dit pas

La couleur d'une commune est un **indice synthétique** : une moyenne pondérée de **tous les
scrutins récents** (présidentielle, législatives, européennes, municipales), pas la photographie
d'une seule élection. Une élection isolée est un instantané biaisé par sa conjoncture ; la
synthèse lisse ce bruit et capture la tendance de fond — ce qu'on entend intuitivement par
« Saint-Denis est rouge » ou « Nice est bleu marine ».

Elle décrit **les électeurs qui se sont exprimés**, jamais « les habitants » : on dit
« les électeurs de X ont voté… », jamais « X est une ville de droite ou de gauche ».
Ce n'est pas un jugement. L'abstention entre dans le calcul (voir plus bas) et le taux de
participation est **toujours affiché au même niveau que la couleur**.

## Les familles politiques

Les candidats et listes sont regroupés en **7 familles**, à partir des « nuances politiques »
officielles attribuées par le Ministère de l'Intérieur (codes type `LFI`, `RN`, `LR`, `ECO`,
`UG`, `ENS`…). Chaque famille a une couleur canonique, point de départ du calcul :

| Famille | Exemples de nuances | Couleur canonique |
|---------|---------------------|-------------------|
| Extrême gauche | LO, NPA, LFI | Rouge vif `#D60B0B` |
| Gauche | PS, PCF, DVG, Union de la gauche | Rose-rouge `#E84E6B` |
| Écologistes | EELV, DVE | Vert `#46A302` |
| Centre | Renaissance, MoDem, Horizons, UDI | Jaune-orangé `#FFB300` |
| Droite | LR, DVD | Bleu `#2D6FCB` |
| Extrême droite | RN, Reconquête, DVED | Bleu marine `#16243F` |
| Divers / régionalistes | REG, DIV, sans étiquette | Gris `#9AA0A6` |

Cette table est un **paramètre de configuration, pas une vérité absolue**. Le mapping
nuance → famille est maintenu **par scrutin** — un CSV daté par élection dans
[`pipeline/config/nuances/`](../pipeline/config/nuances/) — car les nuances officielles
évoluent d'un scrutin à l'autre ; la liste canonique famille → couleur vit dans
[`pipeline/config/familles.csv`](../pipeline/config/familles.csv).

> Nuance d'affichage : dans l'app, les barres de répartition et les légendes utilisent une
> palette propre (`mobile/src/lib/familles.ts`), légèrement ajustée pour la lisibilité sur fond
> sombre. La couleur « hero » d'une commune, elle, vient du calcul ci-dessous — désaturée par la
> participation, elle diffère donc volontairement de la teinte de famille brute.

## La pondération des scrutins

Chaque scrutin contribue à la synthèse avec un poids = **poids du type × poids de récence**.

**Poids par type** (extrait de [`pipeline/config/poids_scrutins.yaml`](../pipeline/config/poids_scrutins.yaml),
qui fait foi) :

| Scrutin | Poids | Justification |
|---------|-------|---------------|
| Présidentielle, 1ᵉʳ tour | 1,0 | Le vote le plus sincère et le mieux étiqueté nationalement |
| Législatives, 1ᵉʳ tour | 0,8 | Bon signal national, légère prime aux sortants locaux |
| Européennes | 0,7 | Proportionnelle expressive, mais abstention structurellement forte |
| Régionales / départementales, 1ᵉʳ tour | 0,6 | Signal correct, étiquetage parfois composite |
| Municipales, 1ᵉʳ tour | 0,5 | Très local mais bruité : personnalités, listes sans étiquette |
| **Seconds tours** | **0 — exclus** | Duels stratégiques : ils mesurent un report, pas une préférence |

**Poids de récence** : décroissance exponentielle avec une **demi-vie de 6 ans**
(≈ un cycle électoral) :

```
poids_récence = 0,5 ^ (âge_en_années / 6)
```

Un scrutin d'il y a 6 ans pèse moitié moins qu'un scrutin de cette année. La couleur « vit » :
elle se déplace si la commune change durablement, sans sur-réagir au dernier scrutin.

**Agrégation** : pour chaque famille, sa part synthétique est la moyenne pondérée de ses parts
des suffrages exprimés sur tous les scrutins inclus :

```
part_famille = Σ (poids_scrutin × part_famille_scrutin) / Σ poids_scrutin
```

La participation synthétique est la même moyenne pondérée des taux de participation.
Le panier actuel : présidentielle 2022, législatives 2024, européennes 2024, municipales 2026
(1ᵉʳˢ tours).

## L'abstention pâlit la couleur — jamais elle ne change la teinte

Décision de conception importante : **l'abstention joue sur l'intensité, pas sur la teinte.**
On ne mélange pas de gris dans la couleur — ce serait prétendre que les abstentionnistes sont
« neutres », alors qu'on ignore simplement leur opinion. À la place, la participation module la
**saturation**, relativement à la participation médiane nationale du panier de scrutins :

```
facteur_participation = clamp(participation_commune / participation_médiane_nationale, 0,55, 1,0)
```

Une commune qui vote comme la médiane garde sa pleine intensité ; une commune qui vote nettement
moins est désaturée, avec un plancher de lisibilité (0,55). Une seconde modulation, la **marge**
entre la famille en tête et la deuxième, pâlit de la même façon les communes politiquement
partagées. Une couleur vive signifie donc : « résultat net **et** participation normale ».

Le calcul se fait en espace **OKLCH** (perceptuellement uniforme) : la désaturation reste
visuellement cohérente d'une famille à l'autre. Implémentation : `pipeline/couleur.py`.

Concrètement : Saint-Denis, où gauche et extrême gauche dominent tous les scrutins mais où
l'abstention est élevée, apparaît **rouge, légèrement adouci**. Nice, droite et extrême droite
dominantes avec une participation proche de la médiane, apparaît **bleu marine, franc**.

## La transparence dans l'app

La fiche d'une commune affiche d'abord la couleur synthétique, puis le **détail scrutin par
scrutin** (chacun avec sa mini-couleur et sa répartition) : on voit d'où vient la synthèse, et
quand les scrutins divergent. L'encart « comment cette couleur est calculée » liste les scrutins
inclus et leur poids effectif — cette liste vient de la réponse de l'API, pas d'un texte statique.

## Communes repères (tests automatisés)

Des communes au profil connu servent de tests de non-régression : toute évolution du mapping ou
des poids doit les laisser cohérentes. Elles sont vérifiées par la suite d'intégration
(`tests/test_reperes.py`, exécutée sur données réelles) :

| Commune | Attendu |
|---------|---------|
| Saint-Denis (93) | Rouge, adouci par l'abstention |
| Nice (06) | Bleu marine, franc |

## Limites connues et assumées

- **Blocs divisés** : une gauche éclatée en trois familles peut perdre la « famille dominante »
  face à une extrême droite unifiée, alors que le bloc de gauche est majoritaire. Vraie limite de
  l'approche catégorielle — la répartition complète est toujours affichée pour la rendre visible.
- **Listes « sans étiquette »** (municipales, surtout petites communes) → famille « Divers » ;
  leur influence est bornée par le poids 0,5 des municipales.
- **Couverture inégale** : toutes les communes n'ont pas le même panier de scrutins exploitables ;
  la synthèse se calcule sur les scrutins disponibles et l'encart de transparence liste ce qui
  est inclus.

## Où sont les paramètres

Tous les choix méthodologiques ci-dessus sont des **paramètres versionnés, publics et
discutables** — ouvrez une issue pour les contester ou proposer mieux :

- [`pipeline/config/poids_scrutins.yaml`](../pipeline/config/poids_scrutins.yaml) — poids par
  type de scrutin, demi-vie de récence, plancher de désaturation, panier de scrutins.
- [`pipeline/config/nuances/`](../pipeline/config/nuances/) — correspondance nuance
  officielle → famille, un CSV par scrutin (voir son
  [README](../pipeline/config/nuances/README.md) pour les choix de classification).
- [`pipeline/config/familles.csv`](../pipeline/config/familles.csv) — familles politiques
  et couleurs canoniques.
- `pipeline/couleur.py` — l'algorithme complet (OKLCH, marge, participation).
