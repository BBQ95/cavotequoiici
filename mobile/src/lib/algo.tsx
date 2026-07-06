/**
 * Algorithme de dominance choisi par l'utilisateur (écran Paramètres).
 *
 * Trois algos précalculés par le pipeline (cf. `pipeline/couleur.py` et
 * `docs/methodologie.md`) : `complet` (pluralité sur les 7 familles, divers
 * inclus — le défaut de l'API), `tendance` (divers exclu de la course — le
 * défaut de l'app) et `blocs` (gauche/centre/droite agrégés). Le choix est
 * persisté localement (même pattern best-effort que `lib/recents.ts`) et
 * diffusé par contexte : les hooks API (`?algo=`) et la carte
 * (`hex_algo_*`) le lisent via `useAlgo()`.
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";

import type { Algo } from "../api/client";

const KEY = "algo_couleur";

/** Défaut de l'app : « tendance » (décision produit du 2026-07-06) — les
 * listes sans étiquette ne grisent plus la carte. L'API, elle, reste par
 * défaut sur « complet » pour ses autres clients : l'app demande toujours
 * explicitement son algo. */
export const ALGO_DEFAUT: Algo = "tendance";

export type AlgoInfo = {
  id: Algo;
  label: string;
  /** Une phrase d'explication, affichée sous l'option dans Paramètres. */
  description: string;
};

/** Ordre d'affichage du sélecteur : du plus brut au plus interprété. */
export const ALGOS = [
  {
    id: "complet",
    label: "Synthèse complète",
    description:
      "La famille en tête sur l'ensemble des suffrages exprimés, listes sans " +
      "étiquette comprises. Le plus fidèle aux données brutes — beaucoup de " +
      "petites communes ressortent grises.",
  },
  {
    id: "tendance",
    label: "Tendance politique",
    description:
      "Les listes sans étiquette ne colorent pas la commune : la teinte vient " +
      "de la première famille politique. Rien n'est caché — la répartition " +
      "complète reste affichée sur la fiche.",
  },
  {
    id: "blocs",
    label: "Par blocs",
    description:
      "Gauche, centre et droite sont regroupés avant de désigner la teinte : " +
      "un camp divisé en plusieurs familles ne perd plus la première place " +
      "face à un camp uni.",
  },
] as const satisfies readonly AlgoInfo[];

/**
 * Garde d'exhaustivité (remarque de revue #49) : si le contrat API gagne un
 * algo, `Record<Algo, string>` (tiles.ts) le signale déjà, mais rien ne
 * forçait le sélecteur à le proposer. tsc échoue ici tant que `ALGOS` ne
 * couvre pas toute l'union `Algo`.
 */
type Verifie<T extends never> = T;
type _AlgosTousProposes = Verifie<Exclude<Algo, (typeof ALGOS)[number]["id"]>>;

function estAlgo(v: unknown): v is Algo {
  return ALGOS.some((a) => a.id === v);
}

type AlgoContexte = {
  algo: Algo;
  setAlgo: (a: Algo) => void;
};

const Contexte = createContext<AlgoContexte>({
  algo: ALGO_DEFAUT,
  setAlgo: () => {},
});

/**
 * Fournit l'algo courant à l'app. Ne rend les enfants qu'une fois la
 * préférence relue du stockage : les premières requêtes partent directement
 * avec le bon algo (pas de rendu furtif dans le mauvais). La lecture est
 * quasi instantanée et l'app attend déjà ses polices au démarrage.
 */
export function AlgoProvider({ children }: { children: ReactNode }) {
  const [algo, setAlgoState] = useState<Algo | null>(null);

  useEffect(() => {
    AsyncStorage.getItem(KEY)
      .then((v) => setAlgoState(estAlgo(v) ? v : ALGO_DEFAUT))
      .catch(() => setAlgoState(ALGO_DEFAUT));
  }, []);

  const setAlgo = useCallback((a: Algo) => {
    setAlgoState(a);
    // best-effort : en cas d'échec d'écriture, le choix vaut pour la session.
    AsyncStorage.setItem(KEY, a).catch(() => {});
  }, []);

  if (algo === null) return null;

  return <Contexte.Provider value={{ algo, setAlgo }}>{children}</Contexte.Provider>;
}

/** Algo de dominance courant + setter (persisté). */
export function useAlgo(): AlgoContexte {
  return useContext(Contexte);
}
