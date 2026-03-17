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
 * [작업 가이드] 지도 확대·축소 관련 상수
 * - 초기 화면 기본 확대 배율(DEFAULT_ZOOM_LEVEL), 확대·축소 허용 범위(MIN/MAX) 추가
 * - Map 컴포넌트의 level props 및 우측 확대/축소 버튼에서 사용
 * 플랜 문서: doc/map_implementation_plan.md §4 요구사항 7, 8
 */
// TODO: DEFAULT_ZOOM_LEVEL, ZOOM_LEVEL_MIN, ZOOM_LEVEL_MAX 상수 정의

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
    lat: 37.4950,
    lng: 127.0220,
    title: "한강 러닝",
    content: "퇴근 후 러닝 동료 구해요",
    category: "운동",
    location_name: "한강공원",
  },
];
