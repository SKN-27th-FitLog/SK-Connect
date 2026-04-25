# 🚀 ETL 로컬 통합 실행기 사용 가이드

이 가이드는 AWS 배포 전, 로컬 환경에서 즉시 데이터를 수집하고 서비스 DB에 적재하기 위한 `local_pipeline_runner.py` 사용법을 안내합니다.

## 1. 개요
이 도구는 **Crawl -> Process -> Save** 프로젝트를 순차적으로 실행하며, 복잡한 내부 저장 구조를 거치지 않고도 **하나의 폴더에서 모든 결과를 확인**할 수 있도록 설계되었습니다.

---

## 2. 사전 준비
실행 전 [ .env](.env) 파일을 열어 다음 설정을 확인하십시오.

- **DB 연결**: `DB_HOST`, `DB_PASSWORD` 등이 실제 서비스 DB 정보를 바라보고 있어야 합니다.
- **임시 저장소**: `LAKE_ROOT_PATH`가 원하는 로컬 경로(예: `./_temp_lake`)로 설정되어 있어야 합니다.

---

## 3. 실행 방법
터미널에서 아래 명령어를 입력하여 실행합니다.

```powershell
# 옵션 1: 기본값으로 실행 (Naver 플랫폼, SC01 카테고리)
python local_pipeline_runner.py

# 옵션 2: 특정 플랫폼 및 카테고리 지정 실행
python local_pipeline_runner.py --platform Kakao --category SC05
```

---

## 4. 결과 확인 (한 폴더에서 보기)
실행이 완료되면 루트 경로에 `./run_snapshot/{batch_id}/` 폴더가 생성됩니다. 이 폴더 하나에서 모든 단계의 결과물을 한눈에 볼 수 있습니다.

- `raw_raw_collection_success.jsonl`: 수집된 원본 데이터 사본
- `normalized_validation_normalization_success.jsonl`: 전처리/정규화 완료 데이터 사본
- `load_load_success.jsonl`: 최종 DB 적재 시도 결과 사본

---

## 5. 로컬 정리 및 AWS 전환 (Zero-footprint)
로컬에서 데이터 수집 업무가 끝났거나 AWS로 환경을 옮길 때는 아래 항목들만 삭제하면 로컬 컴퓨터가 깨끗하게 정리됩니다.

1.  **임시 데이터 삭제**: `rm -rf ./_temp_lake` (또는 지정한 레이크 폴더)
2.  **결과 스냅샷 삭제**: `rm -rf ./run_snapshot`
3.  **실행기 삭제**: `local_pipeline_runner.py` 및 `LOCAL_RUNNER_GUIDE.md` 삭제

---
> [!IMPORTANT]
> 본 도구는 데이터 확인용 사본을 생성할 뿐, 실제 시스템의 Hive 구조를 파괴하지 않습니다. 따라서 로컬에서 검증된 코드를 수정 없이 그대로 AWS Lambda 등에 배포할 수 있습니다.
