import React from "react";
import { View, Dimensions } from "react-native";
import { KakaoMapView } from "@jiggag/react-native-kakao-maps";

import { DEFAULT_LOCATION } from "../../config/map";
import mapScreenStyles from "../../styles/map";

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get("window");

/**
 * 네이티브용 카카오맵 컴포넌트
 * - pins 배열을 markerList로 매핑해서 KakaoMapView에 전달
 * - 마커 클릭 이벤트는 현재 패키지 제약으로 지원하지 않음
 */
export default function KakaoMapNative({ pins }) {
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

