/**
 * 지도 화면 (웹)
 * - 카카오맵으로 초기 표시, config 기준 중심/줌, pin 표시, 마커 클릭 → MapPostPreviewCard
 * - 스타일: map.js + 웹 전용 레이아웃
 * 플랜 문서: doc/map_implementation_plan.md §4 요구사항 2, 6, 8, 9
 */
import React, { useEffect, useState } from "react";
import { View, Text, StyleSheet, Platform } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { Map, MapMarker, useKakaoLoader } from "react-kakao-maps-sdk";

import { DEFAULT_LOCATION } from "../config/map";
import { getMapMarkers } from "../api/mapApi";
import mapScreenStyles from "../styles/map";
import MapPostPreviewCard from "../components/map/MapPostPreviewCard";
import { colors } from "../theme";

const appkey = process.env.EXPO_PUBLIC_KAKAO_MAPS_JAVASCRIPT_KEY || "";

/** react-kakao-maps-sdk는 height에 픽셀/calc 등 명시적 값 필요 (100%는 부모 높이 없으면 0됨) */
const MAP_HEIGHT = Platform.OS === "web" ? "calc(100vh - 180px)" : "100%";

export default function MapScreen() {
  const navigation = useNavigation();
  const [pins, setPins] = useState([]);
  const [selectedPin, setSelectedPin] = useState(null);

  const [loading, error] = useKakaoLoader({ appkey });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    const { lat, lng } = DEFAULT_LOCATION;
    const markers = await getMapMarkers({ lat, lng });
    setPins(markers);
  };

  const handlePinPress = (pin) => setSelectedPin(pin);

  const handleViewPost = () => {
    if (!selectedPin) return;
    navigation.navigate("PostDetail", { postId: selectedPin.postId });
    setSelectedPin(null);
  };

  const containerStyle = [
    mapScreenStyles.container,
    Platform.OS === "web" && { minHeight: "calc(100vh - 180px)" },
  ];

  if (error) {
    const errMsg =
      error?.message ||
      (typeof error === "string" ? error : "API 키 또는 도메인 등록을 확인해 주세요.");
    return (
      <View style={containerStyle}>
        <View style={[webStyles.mapArea, webStyles.centerContent, webStyles.fallbackPadding]}>
          <Text style={webStyles.errorText}>
            지도를 불러올 수 없습니다.{"\n\n"}
            {errMsg}
          </Text>
          <Text style={[webStyles.mapPlaceholderText, { marginTop: 16 }]}>
            [카카오 개발자 콘솔]{"\n"}
            developers.kakao.com → 앱 선택 → 플랫폼 → Web{"\n"}
            → 사이트 도메인에 {"localhost"} 또는 {"localhost:8082"} 추가
          </Text>
        </View>
      </View>
    );
  }

  if (loading || !appkey) {
    return (
      <View style={containerStyle}>
        <View style={[webStyles.mapArea, webStyles.centerContent]}>
          <Text style={webStyles.mapPlaceholderText}>
            {appkey ? "지도 로딩 중..." : "카카오맵 API 키를 설정해 주세요 (.env: EXPO_PUBLIC_KAKAO_MAPS_JAVASCRIPT_KEY)"}
          </Text>
        </View>
      </View>
    );
  }

  return (
    <View style={containerStyle}>
      <View style={webStyles.mapArea}>
        <Map
          center={{ lat: DEFAULT_LOCATION.lat, lng: DEFAULT_LOCATION.lng }}
          style={{ width: "100%", height: MAP_HEIGHT, minHeight: 400 }}
          level={14}
        >
          {pins.map((pin) => (
            <MapMarker
              key={pin.id}
              position={{ lat: pin.lat, lng: pin.lng }}
              onClick={() => handlePinPress(pin)}
            />
          ))}
        </Map>
      </View>

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

const webStyles = StyleSheet.create({
  mapArea: { flex: 1, width: "100%", minHeight: 400 },
  centerContent: { alignItems: "center", justifyContent: "center" },
  fallbackPadding: { padding: 24 },
  mapPlaceholderText: {
    color: colors.gray[500],
    textAlign: "center",
    fontSize: 14,
  },
  errorText: {
    color: colors.destructive,
    textAlign: "center",
    fontSize: 14,
  },
});
