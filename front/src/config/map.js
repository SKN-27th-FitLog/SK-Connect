/**
 * 지도 관련 설정
 * - 내 위치: API 미사용 시 config 고정값 사용
 * - 마커(핀): 일단 config 고정, 추후 백엔드에서 조회
 *
 * FR-MAP-02: 위치 권한 없을 때 대체
 * FR-MAP-04, PR-MAP-01: 마커 데이터 (백엔드 연동 전)
 *
 * [작업 가이드] 전체: doc/map_implementation_plan.md §4 요구사항 4, 5, 7, 8
 */

/** 기본 표시 위치 (강남역) - 내 위치·지도 초기 중심용. 실제 구현 전까지 config 값 사용. 플랜: 요구사항 4 */
export const DEFAULT_LOCATION = {
  lat: 37.468194,
  lng: 126.886750,
  name: "대륭 테크노타운 17차",
};

/**
 * 카카오맵 level: 숫자가 작을수록 확대(가까움), 클수록 축소(멀음). 허용 범위 보통 1~14.
 * KakaoMapWebView 초기 level · 우측 줌 버튼에서 사용.
 */
export const MAP_DEFAULT_LEVEL = 3;
export const MAP_LEVEL_MIN = 1;
export const MAP_LEVEL_MAX = 14;

/**
 * 마커 타입별 스타일 및 리스트 표시 정보
 */
export const PIN_STYLES = {
  post: {
    color: "#FF5A5F",
    iconUrl: "https://cdn-icons-png.flaticon.com/512/3209/3209265.png",
    emoji: "📝",
  },
  community: {
    color: "#00A699",
    iconUrl: "https://cdn-icons-png.flaticon.com/512/476/476863.png",
    emoji: "👥",
  },
  recommend: {
    color: "#FC642D",
    iconUrl: "https://cdn-icons-png.flaticon.com/512/1828/1828884.png",
    emoji: "⭐",
  },
  restaurant: {
    color: "#F59E0B",
    iconUrl: "https://cdn-icons-png.flaticon.com/512/1046/1046857.png",
    emoji: "🍽️",
  },
  cafe: {
    color: "#8B5CF6",
    iconUrl: "https://cdn-icons-png.flaticon.com/512/3233/3233004.png",
    emoji: "☕",
  },
};
