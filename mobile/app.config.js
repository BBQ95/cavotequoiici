// Config dynamique Expo : étend app.json (source statique : nom, slug, icônes,
// versionName sémantique) en injectant un NUMÉRO DE BUILD monotone.
//
// `versionCode` (Android) et `buildNumber` (iOS) — le « (N) » affiché — doivent
// s'incrémenter à chaque build : le Play Store refuse un upload dont le
// versionCode n'est pas strictement supérieur au précédent. On le prend dans
// EXPO_BUILD_NUMBER, alimenté par la CI avec github.run_number (séquentiel, jamais
// réinitialisé). En local (variable absente) → 1, pour un prebuild reproductible.
//
// ⚠️ Ne vaut que pour les builds Gradle directs (QA android-test.yml, dev local) :
// les builds EAS destinés au store ignorent cette valeur — eas.json déclare
// `appVersionSource: "remote"` + `autoIncrement`, EAS tient son propre compteur.
//
// La version sémantique (versionName, ex. 1.0.0) reste dans app.json : on la bump
// à la main pour une vraie release (`expo.version`).
module.exports = ({ config }) => {
  const buildNumber = Number(process.env.EXPO_BUILD_NUMBER) || 1;
  return {
    ...config,
    android: { ...config.android, versionCode: buildNumber },
    ios: { ...config.ios, buildNumber: String(buildNumber) },
  };
};
