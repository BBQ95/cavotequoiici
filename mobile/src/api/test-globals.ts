/**
 * Globals React Native pour les tests Node : `client.ts` évalue `__DEV__` au
 * chargement du module. À importer AVANT `./client` (l'ordre des imports fait
 * foi). Le typecheck, lui, passe par `types-test.d.ts`.
 */
(globalThis as { __DEV__?: boolean }).__DEV__ = false;

export {};
