from src.collectors.platforms.diningcode_collector import DiningCodeCollector
from src.collectors.platforms.naver_collector import NaverCollector
from src.collectors.platforms.google_collector import GoogleCollector
from src.collectors.platforms.kakao_collector import KakaoCollector

from src.services.parsers.diningcode_parser import DiningCodeParser
from src.services.parsers.naver_parser import NaverParser
from src.services.parsers.google_parser import GoogleParser
from src.services.parsers.kakao_parser import KakaoParser

from src.pipeline.stages.stage0_target_selection import Stage0TargetSelection
from src.pipeline.stages.stage1_raw_collection import Stage1RawCollection
from src.pipeline.stages.stage2_candidate_parsing import Stage2CandidateParsing
from src.pipeline.stages.stage3_validation_normalization import Stage3ValidationNormalization
from src.pipeline.stages.stage4_load import Stage4Load
from src.pipeline.stages.stage5_fail_classification import Stage5FailClassification

# 1. 수집기 등록소
COLLECTOR_MAP = {
    "DiningCode": DiningCodeCollector,
    "Naver": NaverCollector,
    "Google": GoogleCollector,
    "Kakao": KakaoCollector
}

# 2. 파서 등록소
PARSER_MAP = {
    "DiningCode": DiningCodeParser,
    "Naver": NaverParser,
    "Google": GoogleParser,
    "Kakao": KakaoParser
}

# 3. 스테이지 등록소 (상수화)
STAGE_MAP = {
    "target_selection": Stage0TargetSelection,
    "raw_collection": Stage1RawCollection,
    "candidate_parsing": Stage2CandidateParsing,
    "validation_normalization": Stage3ValidationNormalization,
    "load": Stage4Load,
    "fail_classification": Stage5FailClassification
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
