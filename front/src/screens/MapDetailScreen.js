import React, { useEffect, useState, useCallback, useRef } from "react";
import { View, ScrollView, TouchableOpacity, Text, Alert } from "react-native";
import { useNavigation } from "@react-navigation/native";
import * as Location from "expo-location";

import { DEFAULT_LOCATION, MAP_DEFAULT_LEVEL, PIN_STYLES } from "../config/map";
import { getMapMarkers } from "../api/remapApi";
import mapScreenStyles from "../styles/map";

import MapPostPreviewCard from "../components/map/MapPostPreviewCard";
import KakaoMapWebView from "../components/map/KakaoMapWebView";
import MapMapControls from "../components/map/MapMapControls";

export default function MapScreen() {
  const navigation = useNavigation();
  const mapRef = useRef(null);
  const [pins, setPins] = useState([]);
  const [selectedPin, setSelectedPin] = useState(null);
  const [locationLoading, setLocationLoading] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const markers = await getMapMarkers();
      setPins(markers || []);
    } catch (error) {
      console.error(error);
    }
  };

  const getMarkerKey = (pin) => {
    if (pin.type === "post") {
      return `post-${pin.map_id}-${pin.post_id}`;
    }
    return `restaurant-${pin.map_id}`;
  };

  const handlePinPress = (pin) => {
    setSelectedPin(pin);
    if (mapRef.current) {
      mapRef.current.setCenter(pin.latitude, pin.longitude);
    }
  };

  const handleMarkerPress = useCallback(
    (markerKey) => {
      const pin = pins.find((p) => getMarkerKey(p) === markerKey);
      if (pin) {
        setSelectedPin(pin);
      }
    },
    [pins]
  );

  const handleViewPost = () => {
    if (!selectedPin?.post_id) return;
    navigation.navigate("PostDetail", { postId: selectedPin.post_id });
    setSelectedPin(null);
  };

  const handleMyLocation = useCallback(async () => {
    setLocationLoading(true);
    try {
      const { lat, lng } = DEFAULT_LOCATION;
      mapRef.current?.setCenter(lat, lng);
    } catch (e) {
      Alert.alert("위치", "현재 위치를 가져오지 못했습니다.");
    } finally {
      setLocationLoading(false);
    }
  }, []);

  return (
    <View style={mapScreenStyles.container}>
      <View style={mapScreenStyles.mapArea}>
        <KakaoMapWebView
          ref={mapRef}
          center={{ lat: DEFAULT_LOCATION.lat, lng: DEFAULT_LOCATION.lng }}
          mapLevel={MAP_DEFAULT_LEVEL}
          pins={pins}
          onMarkerPress={handleMarkerPress}
          pinStyles={PIN_STYLES}
        />

        <MapMapControls
          onPressMyLocation={handleMyLocation}
          onPressZoomIn={() => mapRef.current?.zoomIn()}
          onPressZoomOut={() => mapRef.current?.zoomOut()}
          locationLoading={locationLoading}
        />
      </View>

      {pins.length > 0 && (
        <ScrollView
          horizontal
          contentContainerStyle={mapScreenStyles.pinListContent}
          showsHorizontalScrollIndicator={false}
        >
          {pins.map((pin) => {
            const pinStyle = PIN_STYLES[pin.type] || PIN_STYLES["post"];
            const markerKey = getMarkerKey(pin);

            return (
              <TouchableOpacity
                key={markerKey}
                style={[
                  mapScreenStyles.pinListItem,
                  selectedPin && getMarkerKey(selectedPin) === markerKey
                    ? mapScreenStyles.pinListItemSelected
                    : null,
                ]}
                onPress={() => handlePinPress(pin)}
              >
                <Text style={mapScreenStyles.pinListTitle} numberOfLines={1}>
                  {pin.title || pin.name}
                </Text>
                <Text style={mapScreenStyles.pinListCategory}>
                  {pinStyle.emoji} {pin.category}
                </Text>
              </TouchableOpacity>
            );
          })}
        </ScrollView>
      )}

      {selectedPin && (
        <View style={mapScreenStyles.popupOverlay}>
          <MapPostPreviewCard
            post={{ ...selectedPin, location: selectedPin.address_detail }}
            onClose={() => setSelectedPin(null)}
            onPressViewPost={handleViewPost}
          />
        </View>
      )}
    </View>
  );
}