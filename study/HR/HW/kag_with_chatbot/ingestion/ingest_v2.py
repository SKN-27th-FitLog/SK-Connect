"""
ingestion/ingest_v2.py — 하이브리드 데이터 적재 파이프라인

CSV 원본 데이터를 Neo4j 그래프 DB에 적재합니다.

[적재 전략: Hybrid (Scale & Sentiment)]
    1단계: 식당 기본 정보 배치 적재 (100개 단위)
    2단계: 리뷰 분석 및 태그 추출
        - Fast Tags : KoNLPy 형태소 분석 (빠르고 광범위)
        - Deep Tags : LLM 기반 의미 추출 (정밀하고 맥락 인식)
        - Normalized Tags : 정규화된 태그 추가 연결

[데이터 흐름]
    shop_133312.csv  → Restaurant 노드, Area 노드, Tag 노드
    review_133312.csv → Tag 노드 (HAS_TAG 관계)

[실행 방법]
    python -m ingestion.ingest_v2 --all           # 전체 적재
    python -m ingestion.ingest_v2 --limit 10      # 10개만 적재
"""

import pandas as pd
import json
import os
import sys
import re
from tqdm import tqdm

from konlpy.tag import Okt
from langchain_ollama import ChatOllama
from database.neo4j_client import neo4j_client
from utils.logger import get_logger
from config.settings import settings

logger = get_logger("IngestV2")

# ── Java 환경 설정 (KoNLPy 의존) ──────────────
# JAVA_HOME은 .env 또는 시스템 환경 변수에서 읽어옵니다.
if settings.JAVA_HOME:
    os.environ["JAVA_HOME"] = settings.JAVA_HOME

# ── LLM 및 형태소 분석기 초기화 ──────────────
LLM_MODEL = settings.OLLAMA_MODEL
llm = ChatOllama(model=LLM_MODEL, temperature=0)
okt = Okt()

# ══════════════════════════════════════════════
# 태그 정규화 매핑 테이블
# ══════════════════════════════════════════════
# LLM이 추출한 태그를 표준화된 형태로 변환합니다.
# 예: "친절" → "친절함", "맛있" → "평점높음"
TAG_NORMALIZATION = {
    "친절": "친절함",
    "매우친절": "친절함",
    "맛있": "평점높음",
    "가성비": "가성비",
    "데이트": "분위기좋음",
    "깨끗": "청결함",
}


def normalize_tag(tag: str) -> str:
    """
    태그 문자열을 정규화된 형태로 변환합니다.

    TAG_NORMALIZATION 테이블에서 부분 매칭을 수행합니다.
    매칭되는 키가 없으면 원본 태그를 그대로 반환합니다.

    Args:
        tag: 원본 태그 문자열

    Returns:
        정규화된 태그 문자열
    """
    for key, value in TAG_NORMALIZATION.items():
        if key in tag:
            return value
    return tag


def extract_rid(url: str) -> str:
    """
    네이버 플레이스 URL에서 식당 고유 ID(rid)를 추출합니다.

    URL 예: https://...?rid=12345&...
    → "12345" 반환

    Args:
        url: 네이버 플레이스 식당 URL

    Returns:
        추출된 rid 문자열 또는 None
    """
    match = re.search(r"rid=([^&]+)", str(url))
    return match.group(1) if match else None


def get_fast_tags(content: str) -> list:
    """
    KoNLPy Okt 형태소 분석기를 사용하여 리뷰에서 명사를 추출합니다.

    빠르게 대량의 리뷰를 처리할 수 있지만
    맥락 이해가 없어 정밀도가 낮을 수 있습니다.
    1글자 명사는 노이즈가 많으므로 제외합니다.

    Args:
        content: 리뷰 텍스트

    Returns:
        추출된 명사 리스트 (2글자 이상만)
    """
    if pd.isna(content) or not content:
        return []
    nouns = okt.nouns(str(content))
    return [n for n in nouns if len(n) > 1]


def get_llm_tags(restaurant_name: str, reviews: list) -> list:
    """
    LLM을 사용하여 리뷰에서 식당 특징 태그를 추출합니다.

    여러 리뷰를 종합하여 맥락을 이해하고
    식당의 핵심 특징을 5개 이내의 키워드로 요약합니다.

    Args:
        restaurant_name: 식당명 (프롬프트 컨텍스트용)
        reviews        : 리뷰 텍스트 리스트

    Returns:
        태그 문자열 리스트 (예: ["가성비", "친절함", "조용한"])
        LLM 오류 시 빈 리스트 반환
    """
    if not reviews:
        return []

    combined_reviews = "\n".join([f"- {r}" for r in reviews])
    prompt = f"""
다음은 '{restaurant_name}' 식당의 리뷰들입니다.
이 리뷰들을 바탕으로 이 식당을 잘 설명하는 특징 키워드(태그)를 5개 이내로 뽑아주세요.
각 태그는 단어 형태여야 합니다 (예: 가성비, 친절함, 분위기좋음, 혼밥하기좋음).

리뷰 내용:
{combined_reviews}

응답은 오직 JSON 리스트 형태로만 해주세요.
예시: ["가성비", "친절함", "조용한"]
"""
    try:
        response = llm.invoke(prompt)
        json_str = re.search(r"\[.*\]", response.content, re.DOTALL)
        if json_str:
            return json.loads(json_str.group(0))
    except Exception as e:
        logger.error(f"LLM Tag Error: {e}")
    return []


def load_csv_safely(path: str) -> pd.DataFrame:
    """
    CSV 파일을 안전하게 로드합니다.

    한국어 CSV는 인코딩 문제가 빈번하므로
    여러 인코딩을 순차적으로 시도합니다.

    시도 순서: utf-8-sig → cp949 → euc-kr → utf-8 (fallback)

    검증 방법:
        처음 100행을 읽어 한글 유니코드 범위(가-힣)가
        포함되어 있는지 확인합니다.

    Args:
        path: CSV 파일 경로

    Returns:
        로드된 DataFrame
    """
    for enc in ["utf-8-sig", "cp949", "euc-kr"]:
        try:
            df = pd.read_csv(path, encoding=enc, nrows=100)
            test_col = "store_name" if "store_name" in df.columns else "content"
            sample_text = "".join(df[test_col].astype(str).tolist())
            if re.search("[가-힣]", sample_text):
                logger.info(f"Successfully detected encoding: {enc} for {path}")
                return pd.read_csv(path, encoding=enc)
        except Exception:
            continue

    logger.warning(
        f"Failed to detect proper encoding for {path}, falling back to utf-8"
    )
    return pd.read_csv(path, encoding="utf-8", errors="replace")


def run_hybrid_ingestion(limit_stores: int = None):
    """
    하이브리드 적재 파이프라인의 메인 함수.

    [실행 단계]
        1. CSV 데이터 로드 (shop + review)
        2. 식당 기본 정보 배치 적재 (Restaurant, Area, Tag 노드)
        3. 리뷰 분석: Fast Tags (KoNLPy) + Deep Tags (LLM)
        4. 태그 적재: HAS_TAG 관계 생성 (source별 가중치 차등)

    [가중치 체계]
        Fast Tags  : weight=1.0 (형태소 기반, 저정밀)
        Deep Tags  : weight=2.0 (LLM 기반, 고정밀)
        Normalized : weight=1.5 (정규화된 태그)

    Args:
        limit_stores: 적재할 식당 수 제한 (None이면 전체)
    """
    logger.info("Starting Hybrid Ingestion (Scale & Sentiment)...")

    # ── 1. 데이터 로드 ──────
    shops_df = load_csv_safely("data/shop_133312.csv")
    reviews_df = load_csv_safely("data/review_133312.csv")

    if limit_stores:
        shops_df = shops_df.head(limit_stores)

    # ── 2. 식당 기본 정보 배치 적재 ──────
    logger.info(f"Ingesting {len(shops_df)} stores...")

    if len(shops_df) > 0:
        logger.info(f"First store detected: {shops_df.iloc[0]['store_name']}")

    for i in tqdm(range(0, len(shops_df), 100), desc="Shops"):
        batch = shops_df.iloc[i : i + 100]
        cypher = """
        UNWIND $batch as row
        WITH row, split(row.store_address, ' ') as addr_parts
        MERGE (r:Restaurant {id: row.rid})
        SET r.name = row.store_name,
            r.rating = toFloat(row.store_rating),
            r.address = row.store_address,
            r.url = row.store_url,
            r.latitude = toFloat(row.latitude),
            r.longitude = toFloat(row.longitude)

        // 지역 매핑 (주소의 두 번째 단어를 Area로 사용)
        MERGE (a:Area {name: coalesce(addr_parts[1], '기타')})
        MERGE (r)-[:LOCATED_IN]->(a)

        // 기본 카테고리 태그
        MERGE (t:Tag {name: row.source_category})
        MERGE (r)-[:BELONGS_TO]->(t)
        """

        # RID 추출 및 배치 파라미터 구성
        batch_params = []
        for _, row in batch.iterrows():
            rid = extract_rid(row["store_url"])
            if rid:
                p = row.to_dict()
                p["rid"] = rid
                batch_params.append(p)

        if batch_params:
            neo4j_client.execute_write(cypher, {"batch": batch_params})

    # ── 3. 리뷰 분석 및 태그 적재 ──────
    logger.info("Analyzing reviews and extracting tags...")

    grouped_reviews = reviews_df.groupby("store_url")

    for store_url, group in tqdm(grouped_reviews, desc="Extracting Tags"):
        rid = extract_rid(store_url)
        if not rid:
            continue

        store_name = group.iloc[0]["store_name"]

        # 샘플링 전략: 최신 5개 + 고평점 5개 (중복 제거)
        sorted_recent = group.sort_values(by="date_text", ascending=False).head(5)
        sorted_rating = group.sort_values(by="rating", ascending=False).head(5)
        samples = pd.concat([sorted_recent, sorted_rating]).drop_duplicates(
            subset=["review_id"]
        )

        # ── Fast Tags (KoNLPy) — 전체 리뷰 대상 ──────
        all_fast_tags = []
        for _, r in group.iterrows():
            all_fast_tags.extend(get_fast_tags(r["content"]))
        top_fast = pd.Series(all_fast_tags).value_counts().head(10).index.tolist()

        # ── Deep Tags (LLM) — 샘플 대상 ──────
        sample_contents = samples["content"].dropna().tolist()
        deep_tags = get_llm_tags(store_name, sample_contents)

        # ── 태그 적재 (Fast + Deep) ──────
        cypher_tags = """
        MATCH (r:Restaurant {id: $rid})

        // Fast Tags (형태소 분석 기반, 가중치 낮음)
        FOREACH (tn IN $fast_tags |
            MERGE (t:Tag {name: tn})
            MERGE (r)-[rel:HAS_TAG]->(t)
            SET rel.source = 'Fast', rel.weight = 1.0
        )

        // Deep Tags (LLM 기반, 가중치 높음)
        FOREACH (tn IN $deep_tags |
            MERGE (t:Tag {name: tn})
            MERGE (r)-[rel:HAS_TAG]->(t)
            SET rel.source = 'Deep', rel.weight = 2.0
        )
        """

        # ── 정규화 태그 추가 적재 ──────
        norm_tags = [normalize_tag(t) for t in deep_tags]
        norm_tags = [t for t in norm_tags if t not in deep_tags]

        cypher_norm = """
        MATCH (r:Restaurant {id: $rid})
        UNWIND $norm_tags as tn
        MERGE (t:Tag {name: tn})
        MERGE (r)-[rel:HAS_TAG]->(t)
        SET rel.source = 'Normalized', rel.weight = 1.5
        """

        neo4j_client.execute_write(
            cypher_tags, {"rid": rid, "fast_tags": top_fast, "deep_tags": deep_tags}
        )

        if norm_tags:
            neo4j_client.execute_write(
                cypher_norm, {"rid": rid, "norm_tags": norm_tags}
            )

    logger.info("Hybrid Ingestion completed successfully.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Hybrid Ingestion Tools")
    parser.add_argument("--all", action="store_true", help="Ingest all stores")
    parser.add_argument(
        "--limit", type=int, default=5,
        help="Number of stores to ingest (default: 5)",
    )
    args = parser.parse_args()

    store_limit = None if args.all else args.limit
    run_hybrid_ingestion(limit_stores=store_limit)
