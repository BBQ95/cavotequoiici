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

Les types des données sont **manuels** : `src/api/types.ts` est le miroir des
schémas Pydantic du backend (`pipeline/schemas/*.py`) — toute évolution de forme
côté pipeline doit y être répercutée (et dans `types-statiques.ts`).

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
   local : `make export-statique` puis `make data-serve-lan` depuis la racine du dépôt
   backend, et pointer `http://<IP LAN>:8400`. Ne pas remplacer par un serveur statique
   quelconque : sans support des requêtes `Range` (ce que `python -m http.server` ne fait
   pas), la carte `pmtiles://` casse en silence.

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

Pour tester la carte, il faut un **build natif** — soit un dev client local (ci-dessous),
soit l'APK de QA généré par CI (plus bas).

## Tester la carte en local : dev client

Depuis la racine du dépôt (pas `mobile/`) :

```bash
make mobile-dev-android   # ou mobile-dev-ios
```

Build et installe un dev client (inclut MapLibre et view-shot) sur un émulateur/simulateur
ou un appareil connecté, puis démarre Metro — rechargement à chaud conservé, contrairement
à l'APK de QA. Nécessite Android Studio (SDK, `ANDROID_HOME`, un AVD ou un appareil en
débogage USB) ; la cible Android force `JAVA_HOME` sur un JDK 17, Gradle/AGP étant
incompatibles avec un JDK trop récent (`JvmVendorSpec` sans certains vendors attendus).

**`make mobile-dev-android` est la voie recommandée** : `npm run android` (= `expo run:android`)
ne force pas `JAVA_HOME` et retombera sur cette même erreur si votre JDK par défaut est trop
récent — dans ce cas, exportez `JAVA_HOME` vers un JDK 17 avant de lancer la commande npm.

### Checklist : tester sur un appareil Android physique (pas l'émulateur)

L'émulateur consomme plusieurs Go de RAM (souvent la moitié d'une machine de dev) : tester
directement sur un téléphone en USB évite ce coût. `adb devices` doit lister l'appareil avec
le statut `device` avant de lancer `make mobile-dev-android` — sinon `expo run:android` bascule
sur l'émulateur par défaut. Quatre prérequis indépendants, chacun silencieux s'il manque :

1. **Permissions udev (Linux)** : sans règles udev pour Android, `adb` ne voit jamais
   l'appareil en USB. Sur Arch : `sudo pacman -S android-udev`, puis
   `sudo gpasswd -a $USER adbusers` — une **déconnexion/reconnexion de session** est
   nécessaire pour que l'appartenance au groupe prenne effet (pas juste un nouveau terminal).
2. **Câble et mode USB** : un câble « charge seule » (sans fils de données) ne suffit pas.
   Une fois branché, choisir **« Transfert de fichiers » (MTP)** dans la notification USB du
   téléphone plutôt que « Charge uniquement ».
3. **Débogage USB actif** : Réglages → Options pour développeurs → Débogage USB (menu
   développeur à activer via Réglages → À propos → 7 taps sur « Numéro de build » s'il est
   masqué). Accepter la popup d'autorisation RSA qui apparaît sur le téléphone au branchement.
4. **Même réseau Wi-Fi que le PC** : le branchement USB ne sert qu'au débogage/`adb`, il
   n'active aucune route réseau. Pour joindre `EXPO_PUBLIC_DATA_URL` (export local servi par
   `make data-serve-lan`), le téléphone doit être sur le **même Wi-Fi** que la machine de dev,
   pas seulement branché en USB.

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
