# Contribuer à CaVoteQuoiIci

Merci de votre intérêt ! Ce projet est open source (AGPL v3) et la transparence de sa méthodologie
est au cœur de sa mission.

## Principes

- **Neutralité absolue** : aucun jugement de valeur, des données officielles, une méthodologie publique.
- **Précision honnête** : on assume et on montre les limites (une couleur est une simplification).
- **Langage** : toujours « les électeurs de X ont voté… », jamais « X est une ville de droite/gauche ».

## Workflow

1. Travailler sur une **branche dédiée** (jamais directement sur `main`).
2. **TDD** : écrire les tests d'abord, puis l'implémentation.
3. Ouvrir une **Pull Request** ; elle doit être relue et approuvée avant merge.
4. `pytest` doit être **vert** avant toute demande de relecture.

## Conventions de code

- **Python** : PEP 8, typage (type hints), pas de secret en dur.
- **TypeScript** : configuration du projet `mobile/`.
- Tout changement de **méthodologie** (poids, mapping nuance→famille) doit laisser les **tests des
  communes repères** cohérents (Saint-Denis rouge, Nice bleu marine…).

## Secrets

Jamais de secret (clé API, mot de passe, token) dans le dépôt. Utiliser des fichiers `*.env`
hors versionnement et publier un `*.example` à la place.
