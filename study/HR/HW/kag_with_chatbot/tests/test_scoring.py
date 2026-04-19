"""
tests/test_scoring.py — 스코어링/다양성/중복제거 단위 테스트

recommendation/scoring.py의 후처리 로직을 검증합니다.

실행: pytest tests/test_scoring.py -v
"""

import pytest

from recommendation.scoring import (
    apply_diversity_penalty,
    deduplicate_results,
    sort_and_limit,
    post_process_candidates,
)


def _make_candidate(id_: str, cat: str, score: float) -> dict:
    """테스트용 후보 딕셔너리 생성 헬퍼"""
    return {
        "id": id_, "name": f"식당_{id_}", "cat_group": cat,
        "quality_score": score, "rating": 4.0, "address": "서울",
    }


class TestDiversityPenalty:
    """카테고리 다양성 패널티 테스트"""

    def test_no_penalty_without_flag(self):
        """diversity_flag=False → 패널티 없음"""
        candidates = [
            _make_candidate("1", "한식", 0.8),
            _make_candidate("2", "한식", 0.7),
        ]
        result = apply_diversity_penalty(candidates, diversity_flag=False, limit=5)
        # 첫 번째는 패널티 0, 두 번째는 0.1 패널티
        assert result[0]["final_score"] == 0.8
        assert result[1]["final_score"] == 0.6  # 0.7 - 0.1

    def test_heavy_penalty_with_flag(self):
        """diversity_flag=True + 충분한 후보 → Cap 초과 시 강력 패널티"""
        # 후보 12개 (limit*2 이상) → Cap 적용
        candidates = [_make_candidate(str(i), "한식", 0.8) for i in range(12)]
        result = apply_diversity_penalty(candidates, diversity_flag=True, limit=5)
        # 3번째부터 Cap 초과 (MAX_PER_CAT=2)
        assert result[2]["final_score"] == pytest.approx(0.3)  # 0.8 - 0.5


class TestDeduplication:
    """ID 기반 중복 제거 테스트"""

    def test_remove_duplicates(self):
        """동일 ID 중 높은 점수만 유지"""
        candidates = [
            {**_make_candidate("1", "한식", 0.8), "final_score": 0.8},
            {**_make_candidate("1", "양식", 0.5), "final_score": 0.5},
        ]
        result = deduplicate_results(candidates)
        assert len(result) == 1
        assert result[0]["final_score"] == 0.8

    def test_no_duplicates(self):
        """중복 없는 경우 그대로 유지"""
        candidates = [
            {**_make_candidate("1", "한식", 0.8), "final_score": 0.8},
            {**_make_candidate("2", "양식", 0.7), "final_score": 0.7},
        ]
        result = deduplicate_results(candidates)
        assert len(result) == 2


class TestSortAndLimit:
    """정렬 및 개수 제한 테스트"""

    def test_sort_by_score_desc(self):
        """점수 내림차순 정렬"""
        candidates = [
            {**_make_candidate("1", "한식", 0.5), "final_score": 0.5},
            {**_make_candidate("2", "양식", 0.8), "final_score": 0.8},
        ]
        result = sort_and_limit(candidates, limit=10)
        assert result[0]["id"] == "2"

    def test_limit_applied(self):
        """개수 제한 적용"""
        candidates = [
            {**_make_candidate(str(i), "한식", 0.5), "final_score": 0.5}
            for i in range(10)
        ]
        result = sort_and_limit(candidates, limit=3)
        assert len(result) == 3


class TestPostProcessPipeline:
    """전체 후처리 파이프라인 통합 테스트"""

    def test_full_pipeline(self):
        """패널티 → 중복제거 → 정렬 → 제한 전체 흐름"""
        candidates = [
            _make_candidate("1", "한식", 0.9),
            _make_candidate("2", "양식", 0.85),
            _make_candidate("3", "한식", 0.8),
            _make_candidate("1", "한식", 0.7),  # 중복 ID
        ]
        result = post_process_candidates(candidates, diversity_flag=False, limit=3)
        assert len(result) <= 3
        # 중복 제거로 4→3개
        ids = [r["id"] for r in result]
        assert len(set(ids)) == len(ids)  # 중복 없음
