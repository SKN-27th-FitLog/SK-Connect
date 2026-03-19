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
  lat: 37.497942,
  lng: 127.027638,
  name: "강남역",
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
    iconUrl: "https://cdn-icons-png.flaticon.com/512/149/149059.png",
    emoji: "📝",
  },
  community: {
    color: "#00A699",
    iconUrl: "https://cdn-icons-png.flaticon.com/512/615/615075.png",
    emoji: "👥",
  },
  recommend: {
    color: "#FC642D",
    iconUrl: "https://cdn-icons-png.flaticon.com/512/3135/3135715.png",
    emoji: "⭐",
  },
};

/**
 * 지도 마커 목록 (config 고정)
 * - 지도에 표시할 pin 소스. 현재는 이 배열을 그대로 사용
 * - 추후: 백엔드 API로 중심좌표 기준 조회 (FR-MAP-04, PR-MAP-01)
 * 플랜 문서: doc/map_implementation_plan.md §4 요구사항 5
 */
export const MAP_PINS = [
  {
    id: 1,
    postId: 1,
    type: "post",
    lat: 37.497942,
    lng: 127.027638,
    title: "강남역 점심팟",
    content: "점심 같이 드실 분 구합니다.",
    category: "점심팟",
    location_name: "강남역",
  },
  {
    id: 2,
    postId: 2,
    type: "community",
    lat: 37.5012,
    lng: 127.0396,
    title: "역삼 스터디",
    content: "알고리즘 스터디 모집 중",
    category: "스터디",
    location_name: "역삼동",
  },
  {
    id: 3,
    postId: 3,
    type: "recommend",
    lat: 37.4950,
    lng: 127.0220,
    title: "한강 러닝",
    content: "퇴근 후 러닝 동료 구해요",
    category: "운동",
    location_name: "한강공원",
  },
  {
    id: 4,
    postId: 4,
    type: "community",
    lat: 37.5045, // 선릉역 근처
    lng: 127.0490,
    title: "선릉역 독서 모임",
    content: "매주 주말 아침 독서 하실 분",
    category: "모임",
    location_name: "선릉역",
  },
  {
    id: 5,
    postId: 5,
    type: "post",
    lat: 37.5111, // 삼성역 근처
    lng: 127.0598,
    title: "삼성역 카페 투어",
    content: "새로 생긴 카페 가보실 분 구해요",
    category: "카페",
    location_name: "삼성역",
  },
  {
    id: 6,
    postId: 6,
    type: "recommend",
    lat: 37.4912, // 교대역 근처
    lng: 127.0141,
    title: "교대 맛집 추천",
    content: "여기 곱창 정말 맛있어요",
    category: "맛집",
    location_name: "교대역",
  },
  {
    id: 7,
    postId: 7,
    type: "community",
    lat: 37.5088, // 신논현역 근처
    lng: 127.0220,
    title: "신논현 코딩 스터디",
    content: "리액트 네이티브 같이 공부해요",
    category: "스터디",
    location_name: "신논현역",
  },
  {
    id: 8,
    postId: 8,
    type: "recommend",
    lat: 37.4831, // 양재역 근처
    lng: 127.0345,
    title: "양재 시민의 숲 산책",
    content: "날씨 좋은데 같이 산책해요",
    category: "운동",
    location_name: "양재동",
  },
  {
    id: 9,
    postId: 9,
    type: "post",
    lat: 37.4955, // 강남역 다른 위치
    lng: 127.0311,
    title: "강남역 보드게임",
    content: "주말에 보드게임 하실 분",
    category: "모임",
    location_name: "강남역",
  },
];
