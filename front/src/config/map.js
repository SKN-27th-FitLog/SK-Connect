/**
 * 지도 관련 설정
 * - 내 위치: API 미사용 시 config 고정값 사용
 * - 마커(핀): 일단 config 고정, 추후 백엔드에서 조회
 *
 * FR-MAP-02: 위치 권한 없을 때 대체
 * FR-MAP-04, PR-MAP-01: 마커 데이터 (백엔드 연동 전)
 */

/** 기본 표시 위치 (강남역) - 내 위치 API 미사용 시 사용 */
export const DEFAULT_LOCATION = {
  lat: 37.497942,
  lng: 127.027638,
  name: "강남역",
};

/**
 * 지도 마커 목록 (config 고정)
 * 추후: 백엔드 API로 중심좌표 기준 조회
 * FR-MAP-04, PR-MAP-01 참고
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
