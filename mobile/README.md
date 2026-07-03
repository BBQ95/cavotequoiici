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
```

Les types du client API sont générés depuis l'OpenAPI du backend : `make types`
(depuis la racine du dépôt, régénère `src/api/types.ts` — ne pas l'éditer à la main).

## Tester sur un téléphone (Expo Go)

L'app a besoin d'un backend joignable **depuis le téléphone**. En local :

1. **Backend sur le LAN** (depuis la racine du dépôt, téléphone et machine sur le même réseau) :

   ```bash
   make api-lan                  # API sur 0.0.0.0:8200
   make tiles && make tiles-serve   # tuiles sur :8300 (binaire pmtiles requis)
   ```

2. **Variables d'environnement** : copier [`.env.example`](.env.example) en `mobile/.env`
   (ignoré par git) et y mettre l'IP LAN de la machine :

   ```
   EXPO_PUBLIC_API_URL=http://192.168.1.20:8200
   EXPO_PUBLIC_TILES_URL=http://192.168.1.20:8300
   ```

   Ces variables sont **inlinées dans le bundle JS** : rechargement complet de l'app (ou
   redémarrage d'`expo start`) après modification. Sans elles, l'app démarre mais affiche
   « API non configurée » au premier appel.

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

L'APK embarque les URLs backend définies dans les variables du dépôt (`QA_API_URL`,
`QA_TILES_URL`) — un fork met les siennes dans *Settings → Variables*.

## Versioning

`versionName` sémantique dans `app.json` (bump manuel) ; `versionCode`/`buildNumber` injectés
par `app.config.js` depuis `EXPO_BUILD_NUMBER` (= numéro de run CI) — auto-incrémentés à
chaque build, sans commit.
