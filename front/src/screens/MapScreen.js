import React, { useEffect, useState, useCallback, useRef } from "react";
import { View, ScrollView, TouchableOpacity, Text, Alert } from "react-native";
import { useNavigation } from "@react-navigation/native";
import * as Location from "expo-location"; //사용자 위치 획득 

//config : 백앤드 작업 전 위치 값 목록, 맵의 줌 레벨 제어 
import { DEFAULT_LOCATION, MAP_DEFAULT_LEVEL } from "../config/map";

//api : 지도 조회용 api (카카오맵 api 연동 & 백앤드 작업 전 마커 목록 획득 사전구현 )
import { getMapMarkers } from "../api/mapApi";

//styles
import mapScreenStyles from "../styles/map";

//components 
import MapPostPreviewCard from "../components/map/MapPostPreviewCard"; //pin 선택 시 게시글 미리보기 
import KakaoMapWebView from "../components/map/KakaoMapWebView"; //맵 화면 구현 ( 웹 -> 앱환경 )
import MapMapControls from "../components/map/MapMapControls"; //맵 화면제어 관련 

//맵 화면 정의 
export default function MapScreen() {
  const navigation = useNavigation(); //네비게이션 객체 
  const mapRef = useRef(null); //카카오 맵 웹 버전을 해당 객체로 생성해서 사용하기 위함  
  const [pins, setPins] = useState([]); //맵에서 표시할 마커 목록 
  const [selectedPin, setSelectedPin] = useState(null); //선택된 마커 정보 (해당 마커만 업데이트)
  const [locationLoading, setLocationLoading] = useState(false);

  //랜더링 이후 표시데이터 로드 
  useEffect(() => {
    loadData(); //데이터 로드 
  }, []);

  //맵 표시정보 업데이트 (api 연동 이후 )
  const loadData = async () => {
    const { lat, lng } = DEFAULT_LOCATION; //지도상의 내 위치 (백앤드 연동 전)
    const markers = await getMapMarkers({ lat, lng }); //api 호출 [백엔드 연동 전] config 고정 데이터 반환 -> 해당 부분을 api를 통해 가져오도록 만들어야 함 
    setPins(markers); //맵에서 표시할 마커 목록 업데이트 
  };

  //마커 선택 시 호출 함수 -> 마커 선택 시 해당 마커를 업데이트 하고 선택 된 마커 상태로 변경함 
  const handlePinPress = (pin) => setSelectedPin(pin);

  //
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

  //내 위치로 갱신 
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

  //맵 화면 랜더링
  return (
    /* 전체 화면 */  
    <View style={mapScreenStyles.container}>
      {/* 지도 영역 */}
      <View style={mapScreenStyles.mapArea}>
        {/* 카카오 맵 웹뷰 컨테이너 */}
        <KakaoMapWebView
          ref={mapRef} //생성한 맵 객체 연결 
          center={{ lat: DEFAULT_LOCATION.lat, lng: DEFAULT_LOCATION.lng }} //기본 위치 값 (화면 중앙)
          pins={pins} //표시할 마커 목록 
          mapLevel={MAP_DEFAULT_LEVEL} //기본 줌 레벨 
          onMarkerPress={handleMarkerPress} //마커 클릭 시 호출 함수 
        />
        {/* 맵 화면제어 관련 컴포넌트(화면 우측 메뉴) */}
        <MapMapControls
          onZoomIn={() => mapRef.current?.zoomIn()} //확대 버튼  
          onZoomOut={() => mapRef.current?.zoomOut()} //축소 버튼 
          onMyLocation={handleMyLocation} //내 위치로 이동 (화면 중심 갱신)
          locationLoading={locationLoading} //내 위치 로딩 상태 여부 -> 내 위치를 가져오는 api 통신 시 딜레이를 감안해서 만들어 놓음 
        />
      </View>

      {/* 마커 목록 스크롤 영역 (선택된 마커가 없을 때 표시) */}
      {pins.length > 0 && !selectedPin && (
        <ScrollView
          horizontal //가로 방향 스크롤 
          style={mapScreenStyles.pinListScroll} //마커 목록 스크롤 영역 스타일 
          contentContainerStyle={mapScreenStyles.pinListContent} //마커 목록 컨테이너 스타일 
          showsHorizontalScrollIndicator={false} //가로 스크롤 인dicator 숨김 
        >
          {/* 마커 목록 아이템 렌더링 */}
          {pins.map((pin) => (
            <TouchableOpacity
              key={pin.id} //마커 고유 id 
              style={[
                mapScreenStyles.pinListItem, //마커 목록 아이템 스타일 
                selectedPin?.id === pin.id && mapScreenStyles.pinListItemSelected,
              ]}
              onPress={() => handlePinPress(pin)} //마커 클릭 시 호출 함수 (해당 마커를 선택 상태로 변경함 )
            >
              <Text style={mapScreenStyles.pinListTitle} numberOfLines={1}>
                {pin.title} {/* 마커 제목 */}
              </Text>
              <Text style={mapScreenStyles.pinListCategory}>{pin.category}</Text> 
            </TouchableOpacity>
          ))}
        </ScrollView>
      )}

      {/* 선택된 마커 정보 표시 영역 */}
      {selectedPin && (
        <View style={mapScreenStyles.popupOverlay}>
          <MapPostPreviewCard
            post={{ ...selectedPin, location: selectedPin.location_name }} //선택된 마커 정보 
            onClose={() => setSelectedPin(null)} //닫기 버튼 클릭 시 호출 함수 
            onPressViewPost={handleViewPost} //게시글 보기 버튼 클릭 시 호출 함수 
          />
        </View>
      )}
    </View>
  );
}
