import asyncio
import os
import csv
import shutil
import glob
import logging
import argparse
from datetime import datetime
from src.projects.crawl.crawl_service import CrawlService
from src.projects.process.process_service import ProcessService
from src.projects.save.save_service import SaveService
from src.core.config import settings
from src.core.storage.path_builder import HivePathBuilder

# 로깅 설정 (로컬 실행 시 출력을 보기 좋게 커스터마이징)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("LocalRunner")


def load_categories_from_csv(seed_file: str = "target.csv") -> list[str]:
    """
    target.csv에서 유효한 category_cd 목록을 자동으로 읽어 반환.
    빈 줄 및 중복은 제거됨.
    """
    if not os.path.exists(seed_file):
        logger.error(f"❌ target.csv 파일을 찾을 수 없습니다: {seed_file}")
        return []

    categories = []
    with open(seed_file, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cat = row.get('category_cd', '').strip()
            if cat and cat not in categories:
                categories.append(cat)

    if not categories:
        logger.warning("⚠️  target.csv에 유효한 category_cd가 없습니다.")
    else:
        logger.info(f"📋 target.csv에서 카테고리 {len(categories)}개 감지: {categories}")

    return categories


async def run_and_consolidate(platform: str, category_cd: str):
    """
    1. 전체 ETL 파이프라인(Crawl -> Process -> Save) 실행
    2. 생성된 복잡한 Hive 폴더 구조 내 파일들을 ./run_snapshot/{batch_id} 폴더에 모으기
    """
    logger.info(f"🚀 파이프라인 실행 시작 (플랫폼: {platform}, 카테고리: {category_cd})")
    start_time = datetime.now()

    # ---------------------------------------------------------
    # 단계 1: Crawl (수집)
    # ---------------------------------------------------------
    try:
        crawl_result = await CrawlService.run_crawl(platform, category_cd)
        batch_id = crawl_result.get("batch_id")
        if not batch_id:
            logger.error("❌ 배치 ID 생성에 실패했습니다. (Stage 0 타겟 없음 등)")
            return None
    except Exception as e:
        logger.error(f"❌ Crawl 프로젝트 실행 중 오류 발생: {e}", exc_info=True)
        return None

    # ---------------------------------------------------------
    # 단계 2: Process (전처리/정규화)
    # ---------------------------------------------------------
    try:
        ProcessService.run_process(platform, category_cd)
    except Exception as e:
        logger.error(f"❌ Process 프로젝트 실행 중 오류 발생: {e}", exc_info=True)
        return None

    # ---------------------------------------------------------
    # 단계 3: Save (DB 적재)
    # ---------------------------------------------------------
    try:
        SaveService.run_save(category_cd)
    except Exception as e:
        logger.error(f"❌ Save 프로젝트 실행 중 오류 발생: {e}", exc_info=True)
        return None

    # ---------------------------------------------------------
    # 단계 4: 결과물 집계 (Snapshot 폴더 생성)
    # ---------------------------------------------------------
    snapshot_dir = f"./run_snapshot/{batch_id}"
    os.makedirs(snapshot_dir, exist_ok=True)

    print("\n" + "="*70)
    print(f"📊 [결과 집계 완료] 배치 ID: {batch_id} / 카테고리: {category_cd}")
    print("="*70)

    stages = [
        ("raw", "raw_collection"),
        ("candidate", "candidate_parsing"),
        ("normalized", "validation_normalization"),
        ("load", "load")
    ]

    count = 0
    for proc, stage_name in stages:
        process_partition = HivePathBuilder._normalize_process(proc)
        pattern = os.path.join(
            settings.LAKE_ROOT_PATH,
            f"process={process_partition}/category_cd={category_cd}/**/status=*/{stage_name}_{batch_id}_*.jsonl",
        )
        files = glob.glob(pattern, recursive=True)

        if proc == "raw":
            raw_file_pattern = os.path.join(
                settings.LAKE_ROOT_PATH,
                f"process={process_partition}/category_cd={category_cd}/**/status=*/{stage_name}_{batch_id}_*.html",
            )
            files.extend(glob.glob(raw_file_pattern, recursive=True))

        for f in files:
            status = "success" if "status=success" in f else "fail"
            ext = os.path.splitext(f)[1]
            dest_name = f"{proc}_{stage_name}_{status}{ext}"

            if os.path.exists(os.path.join(snapshot_dir, dest_name)):
                timestamp = datetime.now().strftime("%H%M%S")
                dest_name = f"{proc}_{stage_name}_{status}_{timestamp}{ext}"

            shutil.copy2(f, os.path.join(snapshot_dir, dest_name))
            print(f"✅ 결과물 복사 완료 -> {dest_name}")
            count += 1

    duration = (datetime.now() - start_time).seconds
    print("-" * 70)
    print(f"🕒 소요 시간: {duration}초  |  📁 확인 폴더: {os.path.abspath(snapshot_dir)}")
    print("="*70)

    return batch_id


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ETL 파이프라인 로컬 통합 실행기")
    parser.add_argument("--platform", type=str, default="DiningCode", help="수집 대상 플랫폼 (DiningCode, Naver, Kakao 등)")
    parser.add_argument("--seed", type=str, default="target.csv", help="카테고리 목록 파일 경로 (기본: target.csv)")
    args = parser.parse_args()

    # target.csv에서 카테고리 자동 감지
    categories = load_categories_from_csv(args.seed)
    if not categories:
        logger.error("실행 가능한 카테고리가 없습니다. target.csv를 확인하세요.")
        exit(1)

    async def run_all():
        print("\n" + "="*70)
        print(f"🗂️  총 {len(categories)}개 카테고리 순차 실행: {categories}")
        print("="*70 + "\n")

        results = []
        for cat in categories:
            batch_id = await run_and_consolidate(platform=args.platform, category_cd=cat)
            results.append({"category_cd": cat, "batch_id": batch_id, "status": "완료" if batch_id else "실패"})

        # 전체 실행 요약
        print("\n" + "="*70)
        print("🏁 전체 실행 완료 요약")
        print("="*70)
        for r in results:
            icon = "✅" if r["status"] == "완료" else "❌"
            print(f"  {icon} [{r['category_cd']}] batch_id={r['batch_id']} → {r['status']}")
        print("="*70)
        print("\n💡 [로컬 정리 가이드]")
        print(f"   1. 임시 데이터 제거: rm -rf {settings.LAKE_ROOT_PATH}")
        print(f"   2. 결과 스냅샷 제거: rm -rf ./run_snapshot")

    asyncio.run(run_all())
