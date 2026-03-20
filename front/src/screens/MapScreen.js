import React, { useEffect, useState, useCallback, useRef } from "react";
import { View, ScrollView, TouchableOpacity, Text, Alert, Animated } from "react-native";
import { useNavigation } from "@react-navigation/native";
import * as Location from "expo-location";

import { DEFAULT_LOCATION, MAP_DEFAULT_LEVEL, PIN_STYLES } from "../config/map";
import { getMapMarkers } from "../api/remapApi";
import mapScreenStyles from "../styles/map";
import { CATEGORY_OPTIONS } from "../constants/PostTabs";

import MapPostPreviewCard from "../components/map/MapPostPreviewCard";
import KakaoMapWebView from "../components/map/KakaoMapWebView";
import MapMapControls from "../components/map/MapMapControls";

export default function MapScreen() {
  const navigation = useNavigation();
  const mapRef = useRef(null);
  const [pins, setPins] = useState([]);
  const [selectedPin, setSelectedPin] = useState(null);
  const [displayPin, setDisplayPin] = useState(null); // 애니메이션을 위해 유지되는 핀 데이터
  const [locationLoading, setLocationLoading] = useState(false);
  const [dataLoading, setDataLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState("ALL");
  const [dropdownVisible, setDropdownVisible] = useState(false);
  
  // 애니메이션을 위한 값 (초기 위치는 화면 아래쪽 400만큼 내려가 있음)
  const slideAnim = useRef(new Animated.Value(400)).current;

  useEffect(() => {
    loadData();
  }, []);

  // 선택된 핀이 바뀔 때 슬라이드 업/다운 애니메이션 실행
  useEffect(() => {
    if (selectedPin) {
      setDisplayPin(selectedPin);
      Animated.spring(slideAnim, {
        toValue: 0,
        useNativeDriver: true,
        friction: 8,
        tension: 40,
      }).start();
    } else {
      Animated.timing(slideAnim, {
        toValue: 400,
        duration: 250,
        useNativeDriver: true,
      }).start(() => {
        setDisplayPin(null);
      });
    }
  }, [selectedPin, slideAnim]);

  // 상세 창 닫기: selectedPin을 null로 만들면 useEffect에서 애니메이션 처리
  const handleClosePopup = () => {
    setSelectedPin(null);
  };

  const loadData = async () => {
    try {
      setDataLoading(true);
      const markers = await getMapMarkers();
      setPins(markers || []);
    } catch (error) {
      console.error(error);
    } finally {
      setDataLoading(false);
    }
  };

  const filteredPins = pins.filter(pin => {
    if (selectedCategory === "ALL") return true;
    const categoryLabel = CATEGORY_OPTIONS.find(c => c.value === selectedCategory)?.label;
    
    // API 데이터와 하드코딩된 데이터 구조가 다를 수 있으므로 다양한 속성 검사
    return (
      pin.category === categoryLabel || 
      pin.category_cd === selectedCategory || 
      pin.post_cd === selectedCategory ||
      pin.category === selectedCategory
    );
  });

  const getMarkerKey = (pin) => {
    if (pin.type === "post") {
      return `post-${pin.map_id}-${pin.post_id}`;
    }
    return `restaurant-${pin.map_id}`;
  };

  const handlePinPress = (pin) => {
    setSelectedPin(null); // 하단 목록 클릭 시 상세 정보창 닫기
    if (mapRef.current) {
      mapRef.current.setCenter(pin.latitude || pin.lat, pin.longitude || pin.lng); // 지도 위치만 이동
    }
  };

  const handleMarkerPress = useCallback(
    (markerKey) => {
      const pin = pins.find((p) => getMarkerKey(p) === markerKey);
      if (pin) {
        setSelectedPin(pin);
        if (mapRef.current) {
          mapRef.current.setCenter(pin.latitude || pin.lat, pin.longitude || pin.lng);
        }
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
        {/* 필터 드롭다운 */}
        <View style={mapScreenStyles.filterContainer}>
          <TouchableOpacity 
            style={mapScreenStyles.filterButton}
            onPress={() => setDropdownVisible(!dropdownVisible)}
            activeOpacity={0.8}
          >
            <Text style={mapScreenStyles.filterButtonText}>
              {selectedCategory === "ALL" ? "전체" : CATEGORY_OPTIONS.find(c => c.value === selectedCategory)?.label || "전체"}
            </Text>
            <Text style={{ fontSize: 12, color: "#666" }}>▼</Text>
          </TouchableOpacity>
          
          {dropdownVisible && (
            <View style={mapScreenStyles.filterDropdown}>
              <TouchableOpacity 
                style={mapScreenStyles.filterOption}
                onPress={() => {
                  setSelectedCategory("ALL");
                  setDropdownVisible(false);
                  setSelectedPin(null);
                }}
              >
                <Text style={[mapScreenStyles.filterOptionText, selectedCategory === "ALL" && mapScreenStyles.filterOptionSelected]}>전체</Text>
              </TouchableOpacity>
              {CATEGORY_OPTIONS.filter(cat => cat.value !== "ALL").map(cat => (
                <TouchableOpacity 
                  key={cat.value}
                  style={mapScreenStyles.filterOption}
                  onPress={() => {
                    setSelectedCategory(cat.value);
                    setDropdownVisible(false);
                    setSelectedPin(null);
                  }}
                >
                  <Text style={[mapScreenStyles.filterOptionText, selectedCategory === cat.value && mapScreenStyles.filterOptionSelected]}>{cat.label}</Text>
                </TouchableOpacity>
              ))}
            </View>
          )}
        </View>

        {!dataLoading && (
          <KakaoMapWebView
            ref={mapRef}
            center={DEFAULT_LOCATION}
            mapLevel={MAP_DEFAULT_LEVEL}
            pins={filteredPins}
            onMarkerPress={handleMarkerPress}
            pinStyles={PIN_STYLES}
          />
        )}

        <MapMapControls
          onMyLocation={handleMyLocation}
          onZoomIn={() => mapRef.current?.zoomIn()}
          onZoomOut={() => mapRef.current?.zoomOut()}
          locationLoading={locationLoading}
        />
      </View>

      {filteredPins.length > 0 && (
        <ScrollView
          horizontal
          contentContainerStyle={mapScreenStyles.pinListContent}
          showsHorizontalScrollIndicator={false}
          style={mapScreenStyles.pinListScroll}
        >
          {filteredPins.map((pin) => {
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

      {displayPin && (
        <Animated.View 
          style={[mapScreenStyles.popupOverlay, { transform: [{ translateY: slideAnim }] }]}
          pointerEvents="box-none"
        >
          <MapPostPreviewCard
            post={{ ...displayPin, location: displayPin.address_detail }}
            onClose={handleClosePopup}
            onPressViewPost={() => {
              if (!displayPin?.post_id) return;
              navigation.navigate("PostDetail", { postId: displayPin.post_id });
              setSelectedPin(null);
            }}
          />
        </Animated.View>
      )}
    </View>
  );
}