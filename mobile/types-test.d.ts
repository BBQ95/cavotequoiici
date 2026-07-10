// Contexte tsconfig.test.json uniquement : `types: ["node"]` écarte les types
// ambiants React Native/Expo, mais le test suit l'import de src/api/client.ts
// qui référence la globale RN `__DEV__` — on la redéclare pour le typecheck.
declare const __DEV__: boolean;
