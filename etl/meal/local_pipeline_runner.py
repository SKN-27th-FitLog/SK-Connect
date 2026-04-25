import asyncio
import os
import shutil
import glob
import logging
import argparse
from datetime import datetime
from src.projects.crawl.crawl_service import CrawlService
from src.projects.process.process_service import ProcessService
from src.projects.save.save_service import SaveService
from src.core.config import settings

# 로깅 설정 (로컬 실행 시 출력을 보기 좋게 커스터마이징)
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("LocalRunner")

async def run_and_consolidate(platform: str, category_cd: str):
    """
    1. 전체 ETL 파이프라인(Crawl -> Process -> Save) 실행
    2. 생성된 복잡한 Hive 폴더 구조 내 파일들을 ./run_snapshot/{batch_id} 폴더에 모으기
    """
    logger.info(f"🚀 통합 파이프라인 로컬 실행 시작 (플랫폼: {platform}, 카테고리: {category_cd})")
    start_time = datetime.now()

    # ---------------------------------------------------------
    # 단계 1: Crawl (수집)
    # ---------------------------------------------------------
    try:
        crawl_result = await CrawlService.run_crawl(platform, category_cd)
        batch_id = crawl_result.get("batch_id")
        if not batch_id:
            logger.error("❌ 배치 ID 생성에 실패했습니다. (Stage 0 타겟 없음 등)")
            return
    except Exception as e:
        logger.error(f"❌ Crawl 프로젝트 실행 중 오류 발생: {e}", exc_info=True)
        return

    # ---------------------------------------------------------
    # 단계 2: Process (전처리/정규화)
    # ---------------------------------------------------------
    try:
        ProcessService.run_process(platform, category_cd)
    except Exception as e:
        logger.error(f"❌ Process 프로젝트 실행 중 오류 발생: {e}", exc_info=True)
        return

    # ---------------------------------------------------------
    # 단계 3: Save (DB 적재)
    # ---------------------------------------------------------
    try:
        SaveService.run_save(category_cd)
    except Exception as e:
        logger.error(f"❌ Save 프로젝트 실행 중 오류 발생: {e}", exc_info=True)
        return

    # ---------------------------------------------------------
    # 단계 4: 결과물 집계 (Snapshot 폴더 생성)
    # ---------------------------------------------------------
    snapshot_dir = f"./run_snapshot/{batch_id}"
    os.makedirs(snapshot_dir, exist_ok=True)
    
    print("\n" + "="*70)
    print(f"📊 [결과 집계 완료] 배치 ID: {batch_id}")
    print("="*70)

    # 수집할 단계 정의
    stages = [
        ("raw", "raw_collection"),
        ("candidate", "candidate_parsing"),
        ("normalized", "validation_normalization"),
        ("load", "load")
    ]
    
    count = 0
    for proc, stage_name in stages:
        # Hive 메타 데이터 구조(process=.../**/*batch_id=...)를 검색
        pattern = os.path.join(settings.LAKE_ROOT_PATH, f"process={proc}/**/*batch_id={batch_id}/*.jsonl")
        files = glob.glob(pattern, recursive=True)
        
        # HTML 등의 RAW 파일도 포함 (raw 단계인 경우)
        if proc == "raw":
            raw_file_pattern = os.path.join(settings.LAKE_ROOT_PATH, f"process={proc}/**/*batch_id={batch_id}/*.html")
            files.extend(glob.glob(raw_file_pattern, recursive=True))

        for f in files:
            status = "success" if "status=success" in f else "fail"
            ext = os.path.splitext(f)[1]
            dest_name = f"{proc}_{stage_name}_{status}{ext}"
            
            # 동일 이름 충돌 방지 (여러 파일일 경우)
            if os.path.exists(os.path.join(snapshot_dir, dest_name)):
                timestamp = datetime.now().strftime("%H%M%S")
                dest_name = f"{proc}_{stage_name}_{status}_{timestamp}{ext}"

            shutil.copy2(f, os.path.join(snapshot_dir, dest_name))
            print(f"✅ 결과물 복사 완료 -> {dest_name}")
            count += 1

    duration = (datetime.now() - start_time).seconds
    print("-" * 70)
    print(f"🕒 총 소요 시간: {duration}초")
    print(f"📁 통합 확인 폴더: {os.path.abspath(snapshot_dir)}")
    print(f"💾 실제 DB 적재 확인: {settings.DB_NAME} (Table: maps, shop, crawling)")
    print("="*70)
    print("\n💡 [로컬 정리 가이드]")
    print(f"   1. 임시 데이터 제거: rm -rf {settings.LAKE_ROOT_PATH}")
    print(f"   2. 결과 스냅샷 제거: rm -rf ./run_snapshot")
    print("   3. 코드 정리: run_local_pipeline_runner.py 파일 삭제")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ETL 파이프라인 로컬 통합 실행기")
    parser.add_argument("--platform", type=str, default="Naver", help="수집 대상 플랫폼 (Naver, Kakao 등)")
    parser.add_argument("--category", type=str, default="SC01", help="수집 대상 카테고리 코드 (SC01 등)")
    args = parser.parse_args()
    
    asyncio.run(run_and_consolidate(platform=args.platform, category_cd=args.category))
