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
[`pipeline/config/familles.csv`](../pipeline/config/familles.csv). Ces grilles sont
exposées telles quelles par l'API (`GET /nuances`, avec la source officielle de chaque
ligne) et consultables dans l'app (Méthode → « D'où viennent les familles ? »).

### Contrôle du Conseil d'État

Les grilles de nuances sont fixées par circulaire ou instruction du ministère de
l'Intérieur ; en cas de recours, le **Conseil d'État** tranche, et il a déjà corrigé
plusieurs classements :

- **2020** (décision CE n° 437675) : circulaire des municipales partiellement suspendue —
  seuil des 9 000 habitants, et classer « Debout la France » à l'extrême droite était une
  erreur manifeste (→ famille « droite ») ;
- **2022** : injonction faite au ministère d'ajouter la nuance **NUPES** aux législatives
  (sans elle, les candidats de l'union restaient ventilés par parti) ;
- la classification de **La France insoumise** en « extrême gauche » dans les grilles
  récentes reste débattue (contrôle CE) — la mention figure ligne par ligne dans la
  colonne `source` des CSV concernés.

Détail et références : [`pipeline/config/nuances/README.md`](../pipeline/config/nuances/README.md).

> Nuance d'affichage : dans l'app, les barres de répartition et les légendes utilisent une
> palette propre (`mobile/src/lib/familles.ts`), légèrement ajustée pour la lisibilité sur fond
> sombre. La couleur « hero » d'une commune, elle, vient du calcul ci-dessous — désaturée par la
> participation, elle diffère donc volontairement de la teinte de famille brute.

## La pondération des scrutins

Chaque scrutin contribue à la synthèse avec un poids =
**poids du type × poids de récence × taux de couverture**. Les poids sont versionnés dans
[`pipeline/config/poids.toml`](../pipeline/config/poids.toml), **seule source de vérité** lue par
le calcul (`pipeline/couleur.py`) — aucun poids n'est codé en dur dans le code.

### Pourquoi ces poids ? (barème « S1 »)

Tous les scrutins ne disent pas la même chose de l'orientation politique d'une commune ; leur
poids de base le reflète :

| Scrutin | Poids | Justification |
|---------|-------|---------------|
| Présidentielle, 1ᵉʳ tour | 1,0 | Participation la plus élevée, offre identique partout, vote le plus directement politique |
| Législatives, 1ᵉʳ tour | 0,8 | Scrutin national aussi, mais offre variable d'une circonscription à l'autre, participation plus faible |
| Européennes | 0,5 | Proportionnelle expressive (listes nationales), mais participation la plus basse, vote plus souvent d'expression |
| Municipales, 1ᵉʳ tour | 0,35 | Le plus local : on vote pour une équipe et un maire, pas seulement pour un courant national — signal le moins comparable d'une commune à l'autre |
| **Seconds tours** | **0 — exclus** | Duels stratégiques : ils mesurent un report, pas une préférence |

**Poids de récence** : décroissance exponentielle avec une **demi-vie de 6 ans**
(≈ un cycle électoral) :

```
poids_récence = 0,5 ^ (âge_en_années / 6)
```

Un scrutin d'il y a 6 ans pèse moitié moins qu'un scrutin de cette année. Ce qui compte est
l'**écart d'âge entre** les scrutins : la règle s'applique automatiquement, sans intervention
humaine, et les poids relatifs ne dérivent pas avec le temps — ils ne changent que lorsqu'une
nouvelle élection remplace l'ancienne.

### Le taux de couverture des municipales (« S4 »)

Dans la majorité des petites communes, les candidats municipaux se présentent **sans étiquette**
politique (nuance « LUD » → famille « divers »). Le poids des municipales est donc **en outre**
multiplié par le **taux de couverture** de la commune — la part des suffrages exprimés portant
une nuance politiquement classable (hors « divers ») :

```
poids_effectif(municipales) = 0,35 × poids_récence × couverture
couverture = voix classables / exprimés          (0 si 100 % sans étiquette)
```

Une commune dont les municipales sont **100 % sans étiquette** voit leur poids tomber à **0** : sa
couleur ne vient alors que des scrutins nationaux. Sans cette règle, des milliers de communes
rurales apparaîtraient grises alors que leurs habitants expriment une orientation claire aux
scrutins nationaux (repère : Saint-Urcize, cf. plus bas).

**Agrégation** : pour chaque famille, sa part synthétique est la moyenne pondérée de ses parts
des suffrages exprimés sur tous les scrutins inclus :

```
part_famille = Σ (poids_scrutin × part_famille_scrutin) / Σ poids_scrutin
```

La participation synthétique est la même moyenne pondérée des taux de participation.
Le panier actuel : présidentielle 2022, législatives 2024, européennes 2024, municipales 2026
(1ᵉʳˢ tours).

Ces poids sont des **choix, pas des vérités** : d'autres pondérations sont défendables. C'est
pourquoi ils sont documentés ici, versionnés dans un fichier de configuration public, et le code
qui les applique est ouvert (AGPL) — chacun peut vérifier le calcul, personne ne peut le modifier
discrètement.

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

## Trois algorithmes pour désigner la famille dominante

La teinte d'une commune vient de sa **famille dominante**. Or « dominante » se définit de
plusieurs façons, chacune honnête mais racontant autre chose. Plutôt que d'en imposer une,
les trois sont **précalculées** (`pipeline/couleur.py`, table `couleurs_ville_algo`, propriétés
`hex_algo_*` des tuiles) et l'app propose le choix dans son écran **Paramètres** :

| Algo | Principe | Ce qu'il raconte |
|------|----------|------------------|
| **Synthèse complète** (`complet`) | Pluralité sur les 7 familles, « divers » inclus | Le plus fidèle aux données brutes. Grâce au taux de couverture (« S4 » ci-dessus), les municipales sans étiquette ne pèsent plus rien : même dans les communes rurales, la teinte vient des scrutins nationaux et le gris a quasiment disparu. |
| **Tendance politique** (`tendance`) | « Divers » est exclu de la course à la dominance ; les parts sont renormalisées sur les 6 familles politiques | La teinte vient du vote **politiquement classé** (présidentielle, législatives, européennes…). Une commune ne reste grise que sans aucune voix classée. C'est le **défaut de l'app**. |
| **Par blocs** (`blocs`) | Gauche (extrême gauche + gauche + écologistes), centre, droite (droite + extrême droite) sont agrégés avant la dominance | Répond à la limite « blocs divisés » ci-dessous : un camp éclaté en plusieurs familles ne perd plus la première place face à un camp uni. |

Quel que soit l'algo, **rien n'est caché** : la répartition complète des familles — divers
compris — reste affichée sur chaque fiche, et seuls la teinte et son libellé de dominante
changent. L'API sert `?algo=` (défaut : `complet`, le comportement historique) ; l'app demande
explicitement sa préférence.

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
| Saint-Urcize (15) | Bleu marine dès l'algo complet : municipales 100 % sans étiquette (couverture 0), la teinte vient des scrutins nationaux |

## Limites connues et assumées

- **Blocs divisés** : une gauche éclatée en trois familles peut perdre la « famille dominante »
  face à une extrême droite unifiée, alors que le bloc de gauche est majoritaire. Vraie limite de
  l'approche catégorielle — la répartition complète est toujours affichée pour la rendre visible,
  et l'algo « par blocs » (ci-dessus) offre la lecture agrégée.
- **Listes « sans étiquette »** (municipales, surtout petites communes) → famille « Divers » ;
  leur influence est bornée par le poids 0,35 des municipales **et annulée en proportion par le
  taux de couverture** (« S4 » ci-dessus) ; l'algo « tendance » les retire en outre de la course
  à la teinte.
- **Couverture inégale** : toutes les communes n'ont pas le même panier de scrutins exploitables ;
  la synthèse se calcule sur les scrutins disponibles et l'encart de transparence liste ce qui
  est inclus.

## Où sont les paramètres

Tous les choix méthodologiques ci-dessus sont des **paramètres versionnés, publics et
discutables** — ouvrez une issue pour les contester ou proposer mieux :

- [`pipeline/config/poids.toml`](../pipeline/config/poids.toml) — poids par type de scrutin
  (barème « S1 »), scrutins modulés par le taux de couverture (« S4 »), **demi-vie de récence**
  (`[recence]`) et **plancher de désaturation** (`[desaturation]`). **Seule source de vérité**
  des paramètres du modèle, lue par `pipeline/couleur.py`.
- [`pipeline/config/nuances/`](../pipeline/config/nuances/) — correspondance nuance
  officielle → famille, un CSV par scrutin (voir son
  [README](../pipeline/config/nuances/README.md) pour les choix de classification).
- [`pipeline/config/familles.csv`](../pipeline/config/familles.csv) — familles politiques
  et couleurs canoniques.
- `pipeline/couleur.py` — l'algorithme complet (OKLCH, marge, participation).
