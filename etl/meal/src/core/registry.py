from src.collectors.platforms.diningcode_collector import DiningCodeCollector
from src.collectors.platforms.naver_collector import NaverCollector
from src.collectors.platforms.google_collector import GoogleCollector
from src.collectors.platforms.kakao_collector import KakaoCollector
from src.collectors.platforms.recipe10000_collector import Recipe10000Collector

from src.services.parsers.diningcode_parser import DiningCodeParser
from src.services.parsers.naver_parser import NaverParser
from src.services.parsers.google_parser import GoogleParser
from src.services.parsers.kakao_parser import KakaoParser
from src.services.parsers.recipe10000_parser import Recipe10000Parser

from src.projects.crawl.stage0_target_selection import Stage0TargetSelection
from src.projects.crawl.stage1_raw_collection import Stage1RawCollection
from src.projects.process.stage2_candidate_parsing import Stage2CandidateParsing
from src.projects.process.stage3_validation_normalization import Stage3ValidationNormalization
from src.projects.save.stage4_load import Stage4Load
from src.projects.failcheck.stage5_fail_classification import Stage5FailClassification
from src.core.repository.code_table_repository import CodeTableRepository
from src.core.repository.batch_meta_repo import BatchMetadataRepository

# 스테이지 명칭 상수화 (각 클래스의 NAME 속성 참조 - 순환 참조 방지)
STAGE_TARGET_SELECTION = Stage0TargetSelection.NAME
STAGE_RAW_COLLECTION = Stage1RawCollection.NAME
STAGE_CANDIDATE_PARSING = Stage2CandidateParsing.NAME
STAGE_VALIDATION_NORMALIZATION = Stage3ValidationNormalization.NAME
STAGE_LOAD = Stage4Load.NAME
STAGE_FAIL_CLASSIFICATION = Stage5FailClassification.NAME

# 0. 리포지토리 등록소 (v11/v12/v13/v14 설계 반영)
REPOSITORY_MAP = {
    "code_table": CodeTableRepository,
    "batch_metadata": BatchMetadataRepository,
}

# 1. 수집기 등록소
COLLECTOR_MAP = {
    "DiningCode": DiningCodeCollector,
    "Naver": NaverCollector,
    "Google": GoogleCollector,
    "Kakao": KakaoCollector,
    "Recipe10000": Recipe10000Collector,
}

# 2. 파서 등록소
PARSER_MAP = {
    "DiningCode": DiningCodeParser,
    "Naver": NaverParser,
    "Google": GoogleParser,
    "Kakao": KakaoParser,
    "Recipe10000": Recipe10000Parser,
}

# 3. 스테이지 등록소
STAGE_MAP = {
    STAGE_TARGET_SELECTION: Stage0TargetSelection,
    STAGE_RAW_COLLECTION: Stage1RawCollection,
    STAGE_CANDIDATE_PARSING: Stage2CandidateParsing,
    STAGE_VALIDATION_NORMALIZATION: Stage3ValidationNormalization,
    STAGE_LOAD: Stage4Load,
    STAGE_FAIL_CLASSIFICATION: Stage5FailClassification
}

def get_stage(stage_name: str, **kwargs):
    """스테이지 이름을 기반으로 인스턴스 반환"""
    stage_cls = STAGE_MAP.get(stage_name)
    if not stage_cls:
        raise ValueError(f"Unsupported stage: {stage_name}")
    return stage_cls(**kwargs)

def get_collector(platform: str):
    """플랫폼 이름을 기반으로 수집기 인스턴스 반환"""
    collector_cls = COLLECTOR_MAP.get(platform)
    if not collector_cls:
        raise ValueError(f"Unsupported platform for collector: {platform}")
    return collector_cls()

def get_parser(platform: str):
    """플랫폼 이름을 기반으로 파서 인스턴스 반환"""
    parser_cls = PARSER_MAP.get(platform)
    if not parser_cls:
        raise ValueError(f"Unsupported platform for parser: {platform}")
    return parser_cls()

def get_repository(name: str):
    """리포지토리 이름을 기반으로 인스턴스 반환"""
    repo_cls = REPOSITORY_MAP.get(name)
    if not repo_cls:
        raise ValueError(f"Unsupported repository: {name}")
    return repo_cls()
