/**
 * 지도 화면 — 지도 관련 화면 로직은 이 파일에 모음
 * - 스타일: styles/map.js
 * - 지도 WebView: components/map/KakaoMapWebView
 * - 우측 컨트롤: components/map/MapMapControls
 */
import React, { useEffect, useState, useCallback, useRef } from "react";
import { View, ScrollView, TouchableOpacity, Text, Alert } from "react-native";
import { useNavigation } from "@react-navigation/native";
import * as Location from "expo-location";

import {
  DEFAULT_LOCATION,
  MAP_DEFAULT_LEVEL,
} from "../config/map";
import { getMapMarkers } from "../api/mapApi";
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
    const { lat, lng } = DEFAULT_LOCATION;
    const markers = await getMapMarkers({ lat, lng });
    setPins(markers);
  };

  const handlePinPress = (pin) => setSelectedPin(pin);

  const handleMarkerPress = useCallback(
    (pinId) => {
      const pin = pins.find((p) => p.id === pinId);
      if (pin) setSelectedPin(pin);
    },
    [pins]
  );

  const handleViewPost = () => {
    if (!selectedPin) return;
    navigation.navigate("PostDetail", { postId: selectedPin.postId });
    setSelectedPin(null);
  };

  const handleMyLocation = useCallback(async () => {
    setLocationLoading(true);
    try {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== "granted") {
        Alert.alert("위치 권한", "내 위치로 이동하려면 위치 권한을 허용해 주세요.");
        return;
      }
      const { coords } = await Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.Balanced,
      });
      mapRef.current?.setCenter(coords.latitude, coords.longitude);
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
          pins={pins}
          mapLevel={MAP_DEFAULT_LEVEL}
          onMarkerPress={handleMarkerPress}
        />
        <MapMapControls
          onZoomIn={() => mapRef.current?.zoomIn()}
          onZoomOut={() => mapRef.current?.zoomOut()}
          onMyLocation={handleMyLocation}
          locationLoading={locationLoading}
        />
      </View>

      {pins.length > 0 && !selectedPin && (
        <ScrollView
          horizontal
          style={mapScreenStyles.pinListScroll}
          contentContainerStyle={mapScreenStyles.pinListContent}
          showsHorizontalScrollIndicator={false}
        >
          {pins.map((pin) => (
            <TouchableOpacity
              key={pin.id}
              style={[
                mapScreenStyles.pinListItem,
                selectedPin?.id === pin.id && mapScreenStyles.pinListItemSelected,
              ]}
              onPress={() => handlePinPress(pin)}
            >
              <Text style={mapScreenStyles.pinListTitle} numberOfLines={1}>
                {pin.title}
              </Text>
              <Text style={mapScreenStyles.pinListCategory}>{pin.category}</Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
      )}

      {selectedPin && (
        <View style={mapScreenStyles.popupOverlay}>
          <MapPostPreviewCard
            post={{ ...selectedPin, location: selectedPin.location_name }}
            onClose={() => setSelectedPin(null)}
            onPressViewPost={handleViewPost}
          />
        </View>
      )}
    </View>
  );
}
