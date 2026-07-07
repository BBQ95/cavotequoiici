import { useEffect, useRef } from "react";
import { StyleSheet, View } from "react-native";
import { router } from "expo-router";
import type { StyleSpecification } from "@maplibre/maplibre-gl-style-spec";
import {
  Camera,
  type CameraRef,
  Layer,
  Map,
  VectorSource,
} from "@maplibre/maplibre-react-native";

import { colors } from "../theme/tokens";
import { API_BASE } from "../api/client";
import {
  FONTSTACK_ETIQUETTES,
  SOURCE_LAYER_COMMUNES,
  SOURCE_LAYER_ETIQUETTES,
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

// Glyphes des étiquettes (rendu texte MapLibre), servis par l'API. Sans
// EXPO_PUBLIC_API_URL, on omet la clé `glyphs` ET la couche symbol : carte
// colorée sans noms, plutôt que des erreurs de fetch natives.
const GLYPHS_URL = API_BASE ? `${API_BASE}/fonts/{fontstack}/{range}.pbf` : null;

// Fond sombre sans basemap externe : seules les communes sont dessinées.
const FOND_SOMBRE: StyleSpecification = {
  version: 8,
  ...(GLYPHS_URL ? { glyphs: GLYPHS_URL } : {}),
  sources: {},
  layers: [
    { id: "fond", type: "background", paint: { "background-color": colors.bgFull } },
  ],
};

// Vue initiale : France métropolitaine.
const CENTRE_FRANCE: [number, number] = [2.4, 46.6];
const ZOOM_INITIAL = 4.4;
// Zoom appliqué lors du recentrage sur une commune visitée.
const ZOOM_COMMUNE = 11;
// Durée de l'animation flyTo vers la commune (ms).
const DUREE_FLYTO = 1500;
// Zoom minimal : empêche de dézoomer au point de « perdre » la carte —
// la France reste toujours visible et remplit l'écran.
const ZOOM_MIN = 4;

// Teinte des communes sans donnée pour la couche choisie (scrutin non disputé
// dans la commune → pas de propriété `hex_<scrutin_id>` dans la tuile).
const COULEUR_SANS_DONNEE = colors.surface;

export function CommunesMap({
  couleurProperty = "hex",
  center,
}: {
  couleurProperty?: string;
  center?: [number, number];
}) {
  const cameraRef = useRef<CameraRef>(null);
  const centreInitial: [number, number] = center ?? CENTRE_FRANCE;

  // Recentre la caméra (flyTo) quand `center` change.
  useEffect(() => {
    if (center) {
      cameraRef.current?.flyTo({
        center: center,
        zoom: ZOOM_COMMUNE,
        duration: DUREE_FLYTO,
      });
    }
  }, [center]);

  return (
    <View style={styles.plein}>
      <Map style={styles.plein} mapStyle={FOND_SOMBRE}>
        <Camera
          ref={cameraRef}
          initialViewState={{ center: centreInitial, zoom: ZOOM_INITIAL }}
          minZoom={ZOOM_MIN}
        />
        <VectorSource
          id="communes"
          tiles={TUILES_COMMUNES}
          minzoom={TUILES_MINZOOM}
          maxzoom={TUILES_MAXZOOM}
          onPress={(event) => {
            // Le tap remonte les features de TOUTES les couches de la source
            // (polygones ET points d'étiquette) : on prend la première qui
            // porte un insee — taper un nom de ville ouvre aussi sa fiche.
            const insee = event.nativeEvent.features?.find(
              (f) => f?.properties?.insee,
            )?.properties?.insee as string | undefined;
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
          {GLYPHS_URL != null && (
            <Layer
              id="communes-etiquettes"
              type="symbol"
              source="communes"
              source-layer={SOURCE_LAYER_ETIQUETTES}
              layout={{
                "text-field": ["get", "nom"],
                "text-font": [FONTSTACK_ETIQUETTES],
                // Priorité de placement à la collision : rang national
                // croissant (valeur basse = placée en premier) — la grande
                // ville gagne toujours sur ses voisines.
                "symbol-sort-key": ["get", "rang"],
                "text-size": ["interpolate", ["linear"], ["zoom"], 4, 10.5, 7, 12, 11, 15],
                "text-max-width": 8,
                "text-padding": 2,
              }}
              paint={{
                // Texte clair + halo de la couleur du fond : lisible quelle
                // que soit la teinte de la commune, sans couleur par feature.
                "text-color": colors.text,
                "text-halo-color": colors.bgFull,
                "text-halo-width": 1.2,
                "text-halo-blur": 0.4,
              }}
            />
          )}
        </VectorSource>
      </Map>
    </View>
  );
}

const styles = StyleSheet.create({
  plein: { flex: 1 },
});
