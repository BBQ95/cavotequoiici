import { View, Text, StyleSheet } from "react-native";

import { ScrutinDetail } from "./ScrutinDetail";
import { colors, space, type } from "../theme/tokens";
import type { ScrutinInclus } from "../api/client";

/** Encart « comment cette couleur est calculée » : jamais une boîte noire. */
export function TransparenceEncart({
  insee,
  scrutins,
}: {
  insee: string;
  scrutins: ScrutinInclus[];
}) {
  return (
    <View style={styles.encart}>
      <Text style={styles.titre}>Comment cette couleur est calculée</Text>
      <Text style={styles.intro}>
        Une synthèse pondérée des scrutins récents : les plus récents et les plus
        structurants pèsent davantage. Touchez un scrutin pour voir le détail.
      </Text>
      {scrutins.map((s) => (
        <ScrutinDetail key={s.scrutin_id} insee={insee} scrutin={s} />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  encart: { marginTop: space.sm },
  titre: { fontSize: 18, color: colors.text, ...type.heading },
  intro: { fontSize: 14, color: colors.textSecondary, marginTop: space.sm, lineHeight: 20 },
});
