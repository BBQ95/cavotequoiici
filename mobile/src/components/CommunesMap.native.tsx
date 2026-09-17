import { useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Pressable,
  StyleSheet,
  View,
} from "react-native";
import { router } from "expo-router";
import { MaterialIcons } from "@expo/vector-icons";
import * as Location from "expo-location";
import type { StyleSpecification } from "@maplibre/maplibre-gl-style-spec";
import {
  Camera,
  type CameraRef,
  Layer,
  Map,
  type MapRef,
  type PressEvent,
  VectorSource,
} from "@maplibre/maplibre-react-native";

import { memoriserCadrage, sessionCarte } from "../lib/cadrage";
import type { CommunesMapProps } from "./CommunesMap";
import { colors, radius, space } from "../theme/tokens";
import { DATA_BASE } from "../api/client";
import { CENTRE_FRANCE, ZOOM_METROPOLE } from "../lib/territoires";
import {
  FONTSTACK_ETIQUETTES,
  SOURCE_LAYER_COMMUNES,
  SOURCE_LAYER_ETIQUETTES,
  TUILES_COMMUNES_URL,
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

// Glyphes des étiquettes (rendu texte MapLibre), servis par le CDN statique.
// Sans EXPO_PUBLIC_DATA_URL, on omet la clé `glyphs` ET la couche symbol :
// carte colorée sans noms, plutôt que des erreurs de fetch natives.
const GLYPHS_URL = DATA_BASE ? `${DATA_BASE}/fonts/{fontstack}/{range}.pbf` : null;

// Fond sombre sans basemap externe : seules les communes sont dessinées.
const FOND_SOMBRE: StyleSpecification = {
  version: 8,
  ...(GLYPHS_URL ? { glyphs: GLYPHS_URL } : {}),
  sources: {},
  layers: [
    { id: "fond", type: "background", paint: { "background-color": colors.bgFull } },
  ],
};

// Vue initiale : France métropolitaine (source partagée avec le sélecteur).
const ZOOM_INITIAL = ZOOM_METROPOLE;
// Durée de l'animation flyTo vers la commune (ms).
const DUREE_FLYTO = 1500;
// Zoom appliqué lors du recentrage sur la position GPS de l'utilisateur.
const ZOOM_GEOLOC = 11;
// Zoom minimal : empêche de dézoomer au point de « perdre » la carte —
// la France reste toujours visible et remplit l'écran.
const ZOOM_MIN = 4;

// Teinte des communes sans donnée pour la couche choisie (scrutin non disputé
// dans la commune → pas de propriété `hex_<scrutin_id>` dans la tuile).
const COULEUR_SANS_DONNEE = colors.surface;

export function CommunesMap({
  couleurProperty = "hex",
  cible,
}: CommunesMapProps) {
  const cameraRef = useRef<CameraRef>(null);
  const mapRef = useRef<MapRef>(null);
  const selectionEnCours = useRef(false);
  // Snapshot stable au montage : les événements ne pilotent pas la caméra.
  const [vueInitiale] = useState(() => sessionCarte.cadrage ?? {
    center: CENTRE_FRANCE, zoom: ZOOM_INITIAL,
  });
  const [geoloc, setGeoloc] = useState(false);

  /** Interroge le rendu au toucher, sans la zone élargie des sources. */
  async function selectionner({ point, lngLat }: PressEvent) {
    const map = mapRef.current;
    if (!map || selectionEnCours.current) return;
    selectionEnCours.current = true;
    try {
      const inseeUniques = (features: GeoJSON.Feature[]) => [
        ...new Set(features.flatMap((feature) => {
          const insee = feature.properties?.insee;
          return typeof insee === "string" && insee.length > 0 ? [insee] : [];
        })),
      ];
      // Une étiquette débordant sur sa voisine désigne la commune nommée.
      let communes = GLYPHS_URL
        ? inseeUniques(await map.queryRenderedFeatures(point, {
            layers: ["communes-etiquettes"],
          }))
        : [];
      if (communes.length === 0) {
        communes = inseeUniques(await map.queryRenderedFeatures(point, {
          layers: ["communes-fill"],
        }));
      }
      if (mapRef.current !== map) return;
      if (communes.length === 1) {
        router.push(`/commune/${communes[0]}`);
      } else if (communes.length > 1) {
        // Frontière ou géométries superposées : laisser l'utilisateur préciser.
        // Le zoom d'affichage peut dépasser le zoom maximal des tuiles.
        const { zoom } = await map.getViewState();
        if (mapRef.current !== map) return;
        cameraRef.current?.flyTo({
          center: lngLat,
          zoom: Math.min(zoom + 2, 22),
          duration: 500,
        });
      }
    } catch {
      // Aucune fiche si l'interrogation native échoue ; un nouveau tap réessaie.
    } finally {
      selectionEnCours.current = false;
    }
  }

  // Une commande explicite n'est jouée qu'une fois, même après remontage.
  useEffect(() => {
    if (cible && cible.cle > sessionCarte.cleAppliquee && cameraRef.current) {
      cameraRef.current.flyTo({
        center: cible.centre,
        zoom: cible.zoom,
        duration: DUREE_FLYTO,
      });
      sessionCarte.cleAppliquee = cible.cle;
    }
  }, [cible?.cle]);

  /** Demande la permission GPS, obtient la position et vole vers elle. */
  async function localiser() {
    try {
      setGeoloc(true);
      const perm = await Location.requestForegroundPermissionsAsync();
      if (perm.status !== "granted") {
        Alert.alert(
          "Localisation refusée",
          "Autorisez la localisation pour vous repérer sur la carte.",
        );
        return;
      }
      const pos = await Location.getCurrentPositionAsync({});
      cameraRef.current?.flyTo({
        center: [pos.coords.longitude, pos.coords.latitude],
        zoom: ZOOM_GEOLOC,
        duration: DUREE_FLYTO,
      });
    } catch {
      Alert.alert(
        "Localisation indisponible",
        "Réessayez ou naviguez manuellement sur la carte.",
      );
    } finally {
      setGeoloc(false);
    }
  }

  return (
    <View style={styles.plein}>
      <Map
        ref={mapRef}
        style={styles.plein}
        mapStyle={FOND_SOMBRE}
        onPress={(event) => selectionner(event.nativeEvent)}
        onRegionIsChanging={(event) => memoriserCadrage(event.nativeEvent)}
        onRegionDidChange={(event) => memoriserCadrage(event.nativeEvent)}
      >
        <Camera
          ref={cameraRef}
          initialViewState={vueInitiale}
          minZoom={ZOOM_MIN}
        />
        <VectorSource
          id="communes"
          // Archive PMTiles lue en direct depuis le CDN (protocole natif
          // MapLibre, requêtes Range) — plus de serveur XYZ intermédiaire.
          url={TUILES_COMMUNES_URL}
          minzoom={TUILES_MINZOOM}
          maxzoom={TUILES_MAXZOOM}
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
              "line-color": "#FFFFFF",
              "line-width": 0.3,
              "line-opacity": 0.15,
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
      <Pressable
        onPress={localiser}
        style={styles.geoBtn}
        accessibilityRole="button"
        accessibilityLabel="Me localiser sur la carte"
        disabled={geoloc}
      >
        {geoloc ? (
          <ActivityIndicator color={colors.text} />
        ) : (
          <MaterialIcons name="my-location" size={22} color={colors.text} />
        )}
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  plein: { flex: 1 },
  geoBtn: {
    position: "absolute",
    bottom: space.xl,
    right: space.xl,
    width: 48,
    height: 48,
    borderRadius: radius.pill,
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
  },
});
