/**
 * 지도 API
 *
 * [외부 API 필요 - 추후 구현]
 * - 지도 표시: 카카오맵 SDK, react-native-maps 등
 * - 역지오코딩(좌표→주소): 카카오맵 REST API / 기타
 * - 지도 API 키: FR-MAP-03 - 서버에서 전달 예정
 *
 * [작업 가이드] Pin 중간 다리
 * - 지도에 표시할 pin은 이 모듈의 getMapMarkers(center?) 한 경로로만 받아서 사용
 * - 추후 화면 중앙 좌표·일정 개수 기준 API 연동 시, 이 함수 내부만 수정하면 되도록 유지
 * 플랜 문서: doc/map_implementation_plan.md §4 요구사항 10
 */

import { DEFAULT_LOCATION, MAP_PINS } from "../config/map";

/**
 * 좌표로 주소/이름 조회 (역지오코딩)
 *
 * [TODO] 카카오맵 REST API 등 외부 API 연동
 * @see https://developers.kakao.com/docs/latest/ko/local/dev-guide#search-by-coord
 *
 * @param {number} lat - 위도
 * @param {number} lng - 경도
 * @returns {Promise<{ address: string, name?: string }>}
 */
export async function getAddressFromCoords(lat, lng) {
  // [외부 API 연동 전] config 기본값 반환
  if (lat === DEFAULT_LOCATION.lat && lng === DEFAULT_LOCATION.lng) {
    return {
      address: "서울특별시 강남구 강남대로 396",
      name: DEFAULT_LOCATION.name,
    };
  }
  return {
    address: `${lat.toFixed(6)}, ${lng.toFixed(6)}`,
    name: null,
  };
}

/**
 * 지도에 표시할 마커 목록 조회 (Pin 중간 다리)
 *
 * [TODO] PR-MAP-02: 중심좌표 변경 시 백엔드에서 재조회
 * - 현재: config 고정 반환
 * - 추후: center + 개수 등으로 API 호출 시 이 함수 시그니처 유지하고 내부만 변경
 *
 * @param {Object} [center] - 중심 좌표 { lat, lng } (추후 중심 기준 로딩 시 사용)
 * @returns {Promise<Array>} 마커 목록
 * 플랜 문서: doc/map_implementation_plan.md §4 요구사항 10
 */
export async function getMapMarkers(center) {
  // [백엔드 연동 전] config 고정 데이터 반환 -> 해당 부분을 api를 통해 가져오도록 만들어야 함 
  return MAP_PINS;
}
