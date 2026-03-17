/**
 * 지도 화면 (웹)
 * - 카카오맵으로 초기 표시, config 기준 중심/줌, 우측 확대·축소·현재위치, pin 표시
 * 플랜 문서: doc/map_implementation_plan.md §4 요구사항 2, 6, 8, 9
 */
import React, { useEffect, useState } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Platform,
} from "react-native";
import { useNavigation } from "@react-navigation/native";
import { Map, MapMarker, useKakaoLoader } from "react-kakao-maps-sdk";
import { colors, radius, spacing } from "../theme";
import { DEFAULT_LOCATION } from "../config/map";
import { getMapMarkers } from "../api/mapApi";

const appkey = process.env.EXPO_PUBLIC_KAKAO_MAPS_JAVASCRIPT_KEY || "";

/** react-kakao-maps-sdk는 height에 픽셀/calc 등 명시적 값 필요 (100%는 부모 높이 없으면 0됨) */
const MAP_HEIGHT =
  Platform.OS === "web"
    ? "calc(100vh - 180px)"
    : "100%"; 

export default function MapScreen() {
  const navigation = useNavigation();
  const [pins, setPins] = useState([]);
  const [selectedPin, setSelectedPin] = useState(null);

  const [loading, error] = useKakaoLoader({ appkey });

  useEffect(() => {
    loadData();
  }, []);

  /** [작업 가이드] pin은 getMapMarkers(center)로만 조회. 현재 위치는 config(DEFAULT_LOCATION) 사용. 플랜: doc/map_implementation_plan.md §4 요구사항 4, 10 */
  const loadData = async () => {
    const { lat, lng } = DEFAULT_LOCATION;
    const markers = await getMapMarkers({ lat, lng });
    setPins(markers);
  };

  const handlePinPress = (pin) => {
    setSelectedPin(pin);
  };

  const handleViewPost = () => {
    if (!selectedPin) return;
    navigation.navigate("PostDetail", { postId: selectedPin.postId });
    setSelectedPin(null);
  };

  if (error) {
    const errMsg =
      error?.message ||
      (typeof error === "string" ? error : "API 키 또는 도메인 등록을 확인해 주세요.");
    return (
      <View style={styles.container}>
        <View style={[styles.mapArea, styles.centerContent]}>
          <Text style={styles.errorText}>
            지도를 불러올 수 없습니다.{"\n"}
            {errMsg}
          </Text>
        </View>
      </View>
    );
  }

  if (loading || !appkey) {
    return (
      <View style={styles.container}>
        <View style={[styles.mapArea, styles.centerContent]}>
          <Text style={styles.mapPlaceholderText}>
            {appkey ? "지도 로딩 중..." : "카카오맵 API 키를 설정해 주세요"}
          </Text>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.mapArea}>
        {/* [작업 가이드] 초기 중심 = DEFAULT_LOCATION, 초기 줌 = config의 DEFAULT_ZOOM_LEVEL 사용. 드래그 이동은 SDK 기본. 플랜: doc/map_implementation_plan.md §4 요구사항 4, 8, 9 */}
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
          {/* [작업 가이드] 우측에 ZoomControl(position="RIGHT") + "내 위치로 이동" 버튼 추가. 내 위치 이동 시 Map ref로 setCenter(DEFAULT_LOCATION). 플랜: doc/map_implementation_plan.md §4 요구사항 6, 7 */}
        </Map>
      </View>

      {selectedPin && (
        <View style={styles.popupOverlay}>
          <View style={styles.popup}>
            <View style={styles.popupHeader}>
              <Text style={styles.popupCategory}>
                {selectedPin.category} · 게시글
              </Text>
              <TouchableOpacity onPress={() => setSelectedPin(null)}>
                <Text style={styles.popupClose}>✕</Text>
              </TouchableOpacity>
            </View>
            <Text style={styles.popupTitle}>{selectedPin.title}</Text>
            <Text style={styles.popupContent}>{selectedPin.content}</Text>
            <Text style={styles.popupLocation}>
              📍 {selectedPin.location_name}
            </Text>
            <TouchableOpacity
              style={styles.popupButton}
              onPress={handleViewPost}
              activeOpacity={0.8}
            >
              <Text style={styles.popupButtonText}>게시글 보기</Text>
            </TouchableOpacity>
          </View>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.gray[200],
    minHeight: Platform.OS === "web" ? "calc(100vh - 180px)" : undefined,
  },
  mapArea: { flex: 1, width: "100%", minHeight: 400 },
  centerContent: { alignItems: "center", justifyContent: "center" },
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
  popupOverlay: {
    position: "absolute",
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: "rgba(0,0,0,0.3)",
    padding: spacing.lg,
    alignItems: "center",
  },
  popup: {
    backgroundColor: colors.white,
    borderRadius: radius.xl,
    padding: spacing.lg,
    width: "100%",
    maxWidth: 320,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 12,
    elevation: 10,
  },
  popupHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: spacing.sm,
  },
  popupClose: { color: colors.gray[400], fontSize: 18 },
  popupTitle: {
    fontSize: 16,
    fontWeight: "600",
    color: colors.foreground,
  },
  popupContent: { color: colors.gray[600], fontSize: 14, marginTop: 4 },
  popupLocation: {
    color: colors.gray[500],
    fontSize: 14,
    marginTop: spacing.sm,
    marginBottom: spacing.md,
  },
  popupButton: {
    backgroundColor: colors.primary,
    paddingVertical: spacing.sm,
    borderRadius: radius.lg,
    alignItems: "center",
  },
  popupButtonText: { color: colors.white, fontWeight: "500" },
});
