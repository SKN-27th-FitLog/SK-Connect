/**
 * 지도 화면 (네이티브)
 * - UX 정의: 이 파일에서 처리 (상태, 핸들러, 표시 조건)
 * - 스타일: front/src/styles/map.js
 * - 하위 컴포넌트: front/src/components/map
 * - 지도: @jiggag/react-native-kakao-maps (카카오맵)
 * - 참고: 현재 패키지는 마커 클릭 이벤트 미지원 → 하단 목록으로 선택
 */
import React, { useEffect, useState } from "react";
import { View, Dimensions, ScrollView, TouchableOpacity, Text } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { KakaoMapView } from "@jiggag/react-native-kakao-maps";

import { DEFAULT_LOCATION } from "../config/map";
import { getMapMarkers } from "../api/mapApi";
import mapScreenStyles from "../styles/map";
import MapPostPreviewCard from "../components/map/MapPostPreviewCard";

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get("window");

/** 지도 영역 + 마커 렌더링. pins는 MapScreen에서 props로 전달 */
function MapPlaceholder({ pins }) {
  const markerList = pins.map((pin) => ({
    lat: pin.lat,
    lng: pin.lng,
    markerName: String(pin.id),
  }));

  return (
    <View style={mapScreenStyles.container}>
      <KakaoMapView
        style={mapScreenStyles.mapArea}
        width={SCREEN_WIDTH}
        height={SCREEN_HEIGHT}
        centerPoint={{
          lat: DEFAULT_LOCATION.lat,
          lng: DEFAULT_LOCATION.lng,
        }}
        markerList={markerList}
        onChange={() => {}}
      />
    </View>
  );
}

//지도화면 함수 정의 {navigation, pins, selectedPin 상태 관리} 
export default function MapScreen() {
  const navigation = useNavigation();
  const [pins, setPins] = useState([]);
  const [selectedPin, setSelectedPin] = useState(null);

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

  return (
    <View style={mapScreenStyles.container}>
      <MapPlaceholder pins={pins} />

      {/* 주변 게시글 목록 - 마커 클릭 미지원 대체 UX */}
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

      {/* 선택된 핀이 있을 경우 MapPostPreviewCard로 팝업 표시 */}
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
