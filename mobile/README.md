# CaVoteQuoiIci — app mobile (Expo / React Native)

Application **Expo SDK 56** (managed / CNG : pas de dossiers natifs versionnés — `android/`
est régénéré par `expo prebuild`). Onglets : **Rechercher · Carte · Méthode**.

## Démarrage

```bash
cd mobile
npm install
npx expo start        # serveur de dev Metro (QR code Expo Go)
```

Vérifications sans device :

```bash
npx tsc --noEmit                    # typecheck strict
npx expo export --platform web     # valide le bundle Metro
npm test                            # tests Node (parité recherche locale)
```

Les types du client API sont générés depuis l'OpenAPI du backend : `make types`
(depuis la racine du dépôt, régénère `src/api/types.ts` — ne pas l'éditer à la main).

## Tester sur un téléphone (Expo Go)

L'app ne contacte **qu'un endpoint** : le CDN des données statiques (fiches avec scrutins
embarqués, index de recherche, nuances, glyphes, tuiles — publiés par `make export-statique`
côté backend).

1. **Variable d'environnement** : copier [`.env.example`](.env.example) en `mobile/.env`
   (ignoré par git) :

   ```
   EXPO_PUBLIC_DATA_URL=https://data.cavotequoiici.fr
   ```

   La valeur de prod convient au développement (données publiques). Pour tester un export
   local : servir `export/` depuis la racine du dépôt backend (ex.
   `python -m http.server 8400`) et pointer `http://<IP LAN>:8400`.

   Cette variable est **inlinée dans le bundle JS** : rechargement complet de l'app (ou
   redémarrage d'`expo start`) après modification. Sans elle, l'app démarre mais affiche
   « Données non configurées » au premier appel.

2. **Recherche et géolocalisation hors ligne** : au premier usage, l'app télécharge l'index
   des communes (~1 Mo compressé) et le met en cache sur disque, invalidé par
   `meta/version.json` — les recherches suivantes fonctionnent sans réseau.

3. **Expo Go — attention à la version** : le projet est en **SDK 56**, or le Play Store
   distribue Expo Go pour le SDK courant (57+), qui refuse le projet (« incompatible SDK
   version »). Télécharger l'Expo Go **SDK 56** sur <https://expo.dev/go>.

### Limite assumée d'Expo Go : la Carte ne fonctionne pas

`@maplibre/maplibre-react-native` (carte) et `react-native-view-shot` (export d'image de la
carte de partage) sont des **modules natifs, absents d'Expo Go** : l'onglet **Carte** plante
(exception « MLRN module cannot be found », qui peut se fermer) et l'export d'image est
indisponible. **Rechercher, les fiches communes et Méthode fonctionnent normalement.**

Pour tester la carte, il faut un **build natif** — voir ci-dessous.

## QA réelle : APK de build natif

Le workflow [`android-test.yml`](../.github/workflows/android-test.yml) construit un APK
release (signature debug, arm64-v8a) à chaque push/PR sur `main` :

- **Artefact de run** : onglet *Actions* → run → artefact `cavotequoiici-release-apk`,
  téléchargeable et installable directement (autoriser les sources inconnues).
- **Firebase App Distribution** : les testeurs du groupe `testeurs-bbq95` reçoivent chaque
  build dans l'app *App Tester* (distribution réservée à l'instance du mainteneur).

L'APK embarque l'URL du CDN de données définie dans la variable de dépôt (`QA_DATA_URL`)
— un fork met la sienne dans *Settings → Variables*.

## Versioning

`versionName` sémantique dans `app.json` (bump manuel) ; `versionCode`/`buildNumber` injectés
par `app.config.js` depuis `EXPO_BUILD_NUMBER` (= numéro de run CI) — auto-incrémentés à
chaque build, sans commit.
