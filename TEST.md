# ETL Meal to KAG 검증 문서

## 목적

`etl/meal`에서 크롤링한 데이터가 PostgreSQL에 저장되고, 같은 산출물이 KAG importer를 통해 Neo4j에 정상 적재되는지 단계별로 확인한다.

이번 검증 범위는 다음과 같다.

- `etl/it_news`는 기존 구조를 변경하지 않고 그대로 실행만 확인한다.
- `etl/meal`은 `SCxx` 입력을 받아 Hive 산출물 경로를 `category_cd=CA01/shop_cd=SCxx`로 생성하는지 확인한다.
- `etl/meal` 저장 직전에 `crawling.article_url`, `images.image_url`이 HTML 태그 형태로 변환되는지 확인한다.
- `kag`가 `it_news`, `meal cleaning`, `meal recipe` 산출물을 함께 읽어 Neo4j statement를 생성하는지 확인한다.

## 검증 대상 파일

### ETL meal

- `etl/meal/local_pipeline_runner.py`
  - 실제 실행 순서: `Crawl -> Process -> Recipe -> Save`
  - `RecipeService.run_recipe(category_cd)`까지 포함한다.
- `etl/meal/src/core/storage/path_builder.py`
  - `normalized`, `candidate` 산출물을 `process=cleaning`으로 매핑한다.
  - `SCxx` 입력을 `category_cd=CA01/shop_cd=SCxx` 파티션으로 변환한다.
- `etl/meal/src/projects/save/stage4_load.py`
  - PostgreSQL 적재 직전에 `article_url`을 `<a href="...">...</a>`로 변환한다.
  - PostgreSQL 적재 직전에 `image_url`을 `<img src="..." alt="식당 이미지"/>`로 변환한다.
  - `maps.category_cd`, `crawling.category_cd`에는 `CA01`을 저장하고, `shop.shop_cd`에는 `SCxx`를 저장한다.

### KAG

- `kag/src/kag_graph/hive_importer.py`
  - `it_news`: 기존 `process=cleaning/category_cd=IC02/.../*.csv` 유지
  - `meal cleaning`: `process=cleaning/category_cd=CA01/shop_cd=*/.../validation_normalization_*.jsonl`
  - `meal recipe`: `process=recipe/category_cd=CA01/shop_cd=*/.../recipe_collection_*.jsonl`

## 테스트 파일

### 1. Hive path 계약 테스트

파일:

```text
etl/meal/tests/test_path_builder_contract.py
```

검증 내용:

- `category_cd="SC01"` 입력 시 산출 경로가 `category_cd=CA01/shop_cd=SC01`로 생성된다.
- `normalized` process가 외부 경로에서는 `process=cleaning`으로 저장된다.
- `save` process는 `save=shop` 파티션을 유지한다.

핵심 테스트 코드:

```python
path = HivePathBuilder.build_path(
    process="normalized",
    service="shop",
    category_cd="SC01",
    stage="validation_normalization",
    batch_id="20260428_SC01_001",
    status="success",
    dt=dt,
)

assert path == (
    "lake\\process=cleaning\\category_cd=CA01\\shop_cd=SC01\\year=2026\\month=04\\day=28\\status=success"
)
```

실행 명령:

```powershell
cd C:\dev\Project\SK-Connect
$env:PYTHONPATH="C:\dev\Project\SK-Connect\etl\meal"
.\.venv\Scripts\python.exe -m pytest etl\meal\tests\test_path_builder_contract.py -v --basetemp=.pytest_tmp
```

기대 결과:

```text
3 passed
```

### 2. PostgreSQL 적재 직전 값 변환 테스트

파일:

```text
etl/meal/tests/test_stage4_backend_category_contract.py
```

검증 내용:

- `maps.category_cd`에 `CA01`이 저장된다.
- `shop.shop_cd`에 `SC01`이 저장된다.
- `crawling.article_url`에 `<a href="...">...</a>` 태그가 저장된다.
- `images.image_url`에 `<img src="..." alt="식당 이미지"/>` 태그가 저장된다.

핵심 테스트 코드:

```python
stage._load_crawling_and_reviews(session, store, [], map_id="10", category_cd="SC01")

assert session.params[0]["article_url"] == (
    '<a href="https://example.com/store">Sample Store</a>'
)
```

```python
stage._load_images(session, [{"url": "https://cdn.example.com/image.png"}], shop_id="20")

assert session.params[0]["image_url"] == (
    '<img src="https://cdn.example.com/image.png" alt="식당 이미지"/>'
)
```

실행 명령:

```powershell
cd C:\dev\Project\SK-Connect
$env:PYTHONPATH="C:\dev\Project\SK-Connect\etl\meal"
.\.venv\Scripts\python.exe -m pytest etl\meal\tests\test_stage4_backend_category_contract.py -v --basetemp=.pytest_tmp
```

확인된 결과:

```text
4 passed
```

### 3. KAG importer 산출물 탐색 테스트

파일:

```text
kag/tests/test_hive_importer.py
```

검증 내용:

- `it_news` 기존 경로를 유지해서 읽는다.
- `meal cleaning` 새 경로를 읽는다.
- `meal recipe` 새 경로를 읽는다.
- `collect_current_hive_statements()`가 meal 정규화 산출물과 recipe 산출물을 함께 읽어 statement를 만든다.

핵심 테스트 경로:

```text
process=cleaning/category_cd=IC02/year=2026/month=05/day=05/status=success/it_news.csv
process=cleaning/category_cd=CA01/shop_cd=SC01/year=2026/month=05/day=05/status=success/validation_normalization_*.jsonl
process=recipe/category_cd=CA01/shop_cd=SC01/year=2026/month=05/day=12/status=success/recipe_collection_*.jsonl
```

실행 명령:

```powershell
cd C:\dev\Project\SK-Connect
$env:PYTHONPATH="C:\dev\Project\SK-Connect\kag\src"
.\.venv\Scripts\python.exe -m pytest `
  kag\tests\test_hive_importer.py::test_find_meal_process_cleansing_success_files_uses_current_hive_partition `
  kag\tests\test_hive_importer.py::test_find_meal_recipe_success_files_matches_recipe_process_partition `
  kag\tests\test_hive_importer.py::test_collect_current_hive_statements_reads_it_news_cleaning_and_meal_process `
  kag\tests\test_hive_importer.py::test_collect_current_hive_statements_reads_recipe_files_from_meal_root `
  -v --basetemp=.pytest_tmp
```

확인된 결과:

```text
4 passed
```

## 실제 실행 검증 절차

### 1. 의존성 설치

```powershell
cd C:\dev\Project\SK-Connect
.\.venv\Scripts\python.exe -m pip install -r etl\meal\requirements.txt
.\.venv\Scripts\python.exe -m pip install -r etl\it_news\requirements.txt
.\.venv\Scripts\python.exe -m pip install -e kag
.\.venv\Scripts\python.exe -m playwright install chromium
```

### 2. DB와 Neo4j 실행

```powershell
cd C:\dev\Project\SK-Connect\database
docker compose up -d
```

확인 명령:

```powershell
docker ps --filter "name=sk_connect"
```

기대 결과:

```text
sk_connect_db
sk_connect_neo4j
```

### 3. IT 뉴스 ETL 실행

`etl/it_news` 코드는 변경하지 않는다. 기존 산출물 경로가 KAG importer와 맞는지만 확인한다.

```powershell
cd C:\dev\Project\SK-Connect\etl\it_news
$env:PYTHONPATH="C:\dev\Project\SK-Connect\etl\it_news"
..\..\.venv\Scripts\python.exe pipeline.py
```

산출물 확인:

```powershell
Get-ChildItem C:\dev\Project\SK-Connect\etl\it_news\process=cleaning -Recurse -Filter *.csv | Select-Object FullName
```

기대 경로:

```text
process=cleaning\category_cd=IC02\year=...\month=...\day=...\status=success\it_news_*.csv
```

### 4. Meal ETL 실행

```powershell
cd C:\dev\Project\SK-Connect\etl\meal
$env:PYTHONPATH="C:\dev\Project\SK-Connect\etl\meal"
..\..\.venv\Scripts\python.exe local_pipeline_runner.py --platform DiningCode --seed target_sc01.csv
```

실행 순서:

```text
Crawl -> Process -> Recipe -> Save
```

산출물 확인:

```powershell
Get-ChildItem C:\dev\Project\SK-Connect\etl\meal\_temp_lake -Recurse -Filter *.jsonl | Select-Object FullName
```

기대 경로:

```text
process=raw\category_cd=CA01\shop_cd=SC01\...
process=cleaning\category_cd=CA01\shop_cd=SC01\...
process=recipe\category_cd=CA01\shop_cd=SC01\...
process=save\category_cd=CA01\shop_cd=SC01\save=shop\...
```

### 5. PostgreSQL 적재 확인

```powershell
docker exec sk_connect_db psql -U user -d service -c "SELECT category_cd, count(*) FROM maps GROUP BY category_cd ORDER BY category_cd;"
```

기대 결과:

```text
CA01 행이 존재해야 한다.
```

```powershell
docker exec sk_connect_db psql -U user -d service -c "SELECT shop_cd, count(*) FROM shop GROUP BY shop_cd ORDER BY shop_cd;"
```

기대 결과:

```text
SC01 행이 존재해야 한다.
```

HTML 태그 저장 확인:

```powershell
docker exec sk_connect_db psql -U user -d service -c "SELECT article_url FROM crawling WHERE article_url LIKE '<a href=%' LIMIT 5;"
```

```powershell
docker exec sk_connect_db psql -U user -d service -c "SELECT image_url FROM images WHERE image_url LIKE '<img src=%' LIMIT 5;"
```

기대 결과:

```text
<a href="...">...</a>
<img src="..." alt="식당 이미지"/>
```

### 6. KAG seed/schema 적재

```powershell
cd C:\dev\Project\SK-Connect
$env:PYTHONPATH="C:\dev\Project\SK-Connect\kag\src"
.\.venv\Scripts\python.exe kag\scripts\load_neo4j.py
```

### 7. KAG dry-run

```powershell
.\.venv\Scripts\python.exe kag\scripts\import_hive_neo4j.py --mode current-hive --meal-root etl\meal\_temp_lake --it-news-root etl\it_news --dry-run
```

기대 결과:

```text
statements=0 이 아니어야 한다.
```

### 8. KAG 실제 Neo4j 적재

```powershell
.\.venv\Scripts\python.exe kag\scripts\import_hive_neo4j.py --mode current-hive --meal-root etl\meal\_temp_lake --it-news-root etl\it_news
```

기대 결과:

```text
loaded=0 이 아니어야 한다.
```

### 9. Neo4j 적재 검증

전체 노드 수:

```powershell
docker exec sk_connect_neo4j cypher-shell -u neo4j -p password "MATCH (n) RETURN labels(n) AS labels, count(*) AS count ORDER BY labels;"
```

전체 관계 수:

```powershell
docker exec sk_connect_neo4j cypher-shell -u neo4j -p password "MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS count ORDER BY type;"
```

음식점과 메뉴:

```powershell
docker exec sk_connect_neo4j cypher-shell -u neo4j -p password "MATCH (r:Restaurant)-[:SELLS]->(m:Menu) RETURN r.name AS restaurant, collect(m.name)[0..5] AS menus LIMIT 10;"
```

음식 재료:

```powershell
docker exec sk_connect_neo4j cypher-shell -u neo4j -p password "MATCH (m:Menu)-[rel:CONTAINS]->(i:Ingredient) RETURN m.name AS menu, i.name AS ingredient, rel.source AS source, rel.source_url AS source_url LIMIT 20;"
```

IT 뉴스:

```powershell
docker exec sk_connect_neo4j cypher-shell -u neo4j -p password "MATCH (a:NewsArticle) RETURN a.category_cd AS category_cd, count(*) AS count;"
```

KAG 검증 스크립트:

```powershell
cd C:\dev\Project\SK-Connect
$env:PYTHONPATH="C:\dev\Project\SK-Connect\kag\src"
.\.venv\Scripts\python.exe kag\scripts\verify_neo4j.py
```

## 현재까지 확인된 결과

### 통과

```text
etl/meal/tests/test_stage4_backend_category_contract.py
4 passed
```

```text
kag/tests/test_hive_importer.py selected 4 tests
4 passed
```

```text
py_compile
통과
```

### 아직 실제 실행 결과가 필요한 항목

아래 항목은 실제 네트워크 크롤링과 DB/Neo4j 컨테이너가 필요하므로 로컬 실행 후 결과를 기록해야 한다.

- `etl/it_news/pipeline.py` 실행 결과
- `etl/meal/local_pipeline_runner.py` 실행 결과
- PostgreSQL `maps`, `shop`, `images`, `crawling` 적재 결과
- KAG dry-run `statements` 수
- KAG 실제 import `loaded` 수
- Neo4j `Restaurant`, `Menu`, `Ingredient`, `NewsArticle` 노드 및 관계 수

## 결과 기록 양식

실제 실행 후 아래에 값을 적는다.

```text
실행일:

IT 뉴스 CSV 산출물:
- success 파일:
- row 수:

Meal JSONL 산출물:
- raw 파일:
- cleaning 파일:
- recipe 파일:
- save 파일:

PostgreSQL 확인:
- maps CA01 count:
- shop SC01 count:
- crawling <a> count:
- images <img> count:

KAG dry-run:
- statements:

KAG import:
- loaded:

Neo4j 확인:
- Restaurant count:
- Menu count:
- Ingredient count:
- NewsArticle count:
- SELLS 관계 count:
- CONTAINS 관계 count:
- MENTIONS 계열 관계 count:
```
