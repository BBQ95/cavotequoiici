/** Communes récemment consultées (persistées localement). */
import AsyncStorage from "@react-native-async-storage/async-storage";

const KEY = "communes_recentes";
const MAX = 8;

export type Recent = {
  code_insee: string;
  nom: string;
  /** Métadonnées enrichies par la fiche commune (pour la pastille + le sous-titre). */
  departement?: string | null;
  /** Couleur synthétique de la commune (hero), pour la pastille de l'accueil. */
  hex?: string | null;
  /** Famille dominante (ex. « Gauche »), pour le sous-titre « tendance ». */
  tendance?: string | null;
};

export async function getRecents(): Promise<Recent[]> {
  try {
    const raw = await AsyncStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as Recent[]) : [];
  } catch {
    return [];
  }
}

export async function addRecent(commune: Recent): Promise<void> {
  try {
    const actuels = await getRecents();
    const ancien = actuels.find((c) => c.code_insee === commune.code_insee);
    const sans = actuels.filter((c) => c.code_insee !== commune.code_insee);
    // Fusionne avec l'entrée existante : un ajout minimal (depuis la recherche)
    // ne doit pas effacer la couleur enregistrée par une visite de fiche.
    const fusion: Recent = { ...ancien, ...commune };
    const maj = [fusion, ...sans].slice(0, MAX);
    await AsyncStorage.setItem(KEY, JSON.stringify(maj));
  } catch {
    // best-effort : l'historique local n'est pas critique
  }
}
