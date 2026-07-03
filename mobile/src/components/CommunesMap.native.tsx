import { StyleSheet, View } from "react-native";
import { router } from "expo-router";
import type { StyleSpecification } from "@maplibre/maplibre-gl-style-spec";
import { Camera, Layer, Map, VectorSource } from "@maplibre/maplibre-react-native";

import { colors } from "../theme/tokens";
import {
  SOURCE_LAYER_COMMUNES,
  TUILES_COMMUNES,
  TUILES_MAXZOOM,
  TUILES_MINZOOM,
} from "../lib/tiles";

/**
 * Carte choroplèthe des 35 012 communes (Étape 6). Tuiles vectorielles servies
 * en XYZ/MVT ; chaque commune est remplie par la propriété `couleurProperty`
 * (`hex` = synthèse, `hex_<scrutin_id>` = couleur d'un scrutin — carte v2,
 * cf. `lib/tiles.ts` COUCHES_COULEUR). Tap sur une commune → fiche
 * `commune/[insee]`.
 *
 * Implémentation NATIVE uniquement (module natif MapLibre). La variante
 * `CommunesMap.web.tsx` reste un placeholder pour que `expo export web` — et
 * donc le job CI `mobile` — n'importe jamais MapLibre et reste vert.
 */

// Fond sombre sans basemap externe : seules les communes sont dessinées.
const FOND_SOMBRE: StyleSpecification = {
  version: 8,
  sources: {},
  layers: [
    { id: "fond", type: "background", paint: { "background-color": colors.bgFull } },
  ],
};

// Vue initiale : France métropolitaine.
const CENTRE_FRANCE: [number, number] = [2.4, 46.6];
const ZOOM_INITIAL = 4.4;
// Zoom minimal : empêche de dézoomer au point de « perdre » la carte —
// la France reste toujours visible et remplit l'écran.
const ZOOM_MIN = 4;

// Teinte des communes sans donnée pour la couche choisie (scrutin non disputé
// dans la commune → pas de propriété `hex_<scrutin_id>` dans la tuile).
const COULEUR_SANS_DONNEE = colors.surface;

export function CommunesMap({ couleurProperty = "hex" }: { couleurProperty?: string }) {
  return (
    <View style={styles.plein}>
      <Map style={styles.plein} mapStyle={FOND_SOMBRE}>
        <Camera
          initialViewState={{ center: CENTRE_FRANCE, zoom: ZOOM_INITIAL }}
          minZoom={ZOOM_MIN}
        />
        <VectorSource
          id="communes"
          tiles={TUILES_COMMUNES}
          minzoom={TUILES_MINZOOM}
          maxzoom={TUILES_MAXZOOM}
          onPress={(event) => {
            const insee = event.nativeEvent.features?.[0]?.properties?.insee as
              | string
              | undefined;
            if (insee) {
              router.push(`/commune/${insee}`);
            }
          }}
        >
          <Layer
            id="communes-fill"
            type="fill"
            source="communes"
            source-layer={SOURCE_LAYER_COMMUNES}
            paint={{
              "fill-color": ["coalesce", ["get", couleurProperty], COULEUR_SANS_DONNEE],
              "fill-opacity": 0.92,
            }}
          />
          <Layer
            id="communes-line"
            type="line"
            source="communes"
            source-layer={SOURCE_LAYER_COMMUNES}
            paint={{
              "line-color": colors.bgFull,
              "line-width": 0.2,
              "line-opacity": 0.5,
            }}
          />
        </VectorSource>
      </Map>
    </View>
  );
}

const styles = StyleSheet.create({
  plein: { flex: 1 },
});
