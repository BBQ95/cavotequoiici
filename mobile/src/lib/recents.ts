/** Communes récemment consultées (persistées localement). */
import AsyncStorage from "@react-native-async-storage/async-storage";

const KEY = "communes_recentes";
const MAX = 8;

export type Recent = { code_insee: string; nom: string };

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
    const sans = actuels.filter((c) => c.code_insee !== commune.code_insee);
    const maj = [commune, ...sans].slice(0, MAX);
    await AsyncStorage.setItem(KEY, JSON.stringify(maj));
  } catch {
    // best-effort : l'historique local n'est pas critique
  }
}
