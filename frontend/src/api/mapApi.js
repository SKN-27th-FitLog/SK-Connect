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

import { DEFAULT_LOCATION } from "../config/map";

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
