# SK-Connect Project Memory

## Current State

- Repository is a monorepo containing Django backend, Expo/React Native frontend, PostgreSQL/Neo4j database setup, ETL pipelines, KAG graph code, and AI post-processing/post-generation pipelines.
- Local `AGENTS.md` was not found in the repository. User-provided AGENTS instructions are the active project instructions.
- Current Git branch observed: `patch-post-analysis...origin/patch-post-analysis`. `git status --short --branch` showed no tracked/untracked changes before this memory file was added, but emitted permission warnings for `C:\Users\Playdata/.config/git/ignore`.
- Root `.venv` executable was not present. `C:\Python314\python.exe` is available and was used for read-only Python AST validation.

## Operating Context

- Backend: Django/DRF with PostgreSQL, `django-cors-headers`, `drf-spectacular`, JWT auth utilities, Google social login support.
- Frontend: Expo/React Native app with React Navigation, Axios, Kakao map WebView integration, and environment key `EXPO_PUBLIC_KAKAO_MAP_JS_KEY`.
- Database: `database/docker-compose.yml` starts `pgvector/pgvector:pg16` as `sk_connect_db` and `neo4j:5` as `sk_connect_neo4j`.
- KAG: Python package `kag-graph`, Python >= 3.11, dependencies include `kiwipiepy`, `neo4j`, `python-dotenv`, `pytest`.
- ETL:
  - `etl/it_news` crawls GeekNews/PyTorch, cleans CSV outputs, and saves to PostgreSQL `crawling`.
  - `etl/meal` runs Crawl -> Process -> Image Validation -> Recipe -> Save with Hive-style JSONL/HTML outputs.
- AI:
  - `ai/post_analysis` moves `crawling` rows to `analysis`, runs BERT sentiment, and LLM keyword extraction.
  - `ai/postmake_pipeline` groups analysis data, generates posts through a LangGraph flow, saves posts, and writes vector data.

## Structure

- `backend/`: Django project. `config/urls.py` currently wires `api/users/`, `api/schema/`, and `api/docs/`.
- `frontend/`: Expo app. `App.js` wraps `AppNavigator`; navigation includes Home, Community, Chat, Map, MyPage and post/map screens/components.
- `database/`: schema, seed CSVs, Docker Compose, ERD/setup docs.
- `etl/meal/`: staged restaurant/meal ETL with `src/projects/*`, `src/core/*`, collectors, parsers, policies, repositories, image validation services.
- `etl/it_news/`: IT news crawl/clean/save pipeline with tests and integrity docs.
- `kag/`: graph query builder, Neo4j repository/loader, Hive importer, IT keyword extraction service, Cypher templates, tests.
- `ai/post_analysis/`: review/sentiment/keyword analysis pipeline with docs and unit tests.
- `ai/postmake_pipeline/`: post generation and vector persistence pipeline.
- `docs/superpowers/` and `doc/`: implementation specs/plans. These are source-of-truth candidates and must be read before related implementation.

## Core Models And State

- PostgreSQL schema source is `database/init.sql`.
- Django models mostly mirror existing DB tables and many are `managed = False`.
- Main DB tables: `codeT`, `users`, `social_accounts`, `refresh_tokens`, `suspicious_logins`, `maps`, `shop`, `crawling`, `posts`, `menu`, `images`, `likes`, `comments`, `analysis`, `langchain_pg_collection`, `langchain_pg_embedding`.
- `backend/config/settings.py` defines `default` and `secondary` PostgreSQL databases, but `DatabaseRouter.route_app_labels` is currently empty, so normal routing goes to `default`.
- KAG graph write model centers on `GraphWriteStatement`; Neo4j entities include Restaurant, Menu, Ingredient, Area, NewsArticle, Technology, Company, Event, Topic, Tag, Concept relationships.
- `etl/meal/src/core/storage/path_builder.py` maps `SCxx` inputs to `category_cd=CA01/shop_cd=SCxx`, aliases candidate/normalized/image_validation to `process=cleaning`, and load to `process=save`.

## Decisions And Conventions

- Implementation documents are authoritative; do not infer missing behavior.
- ETL design emphasizes stage responsibility separation, policy in Resolver, explicit reason codes, JSONL outputs, Hive-style paths, and no overwrite.
- SQL/query strings and code-table values are intended to be centralized in constants/config/repositories.
- Tests are contract-heavy and split by component. `etl/it_news` and `ai/post_analysis` pytest configs exclude `readonly_smoke` and `slow` by default.
- KAG keyword extraction separates extraction JSONL generation from Neo4j import. LLM classifies unresolved keywords; it is not intended to perform primary extraction.

## Known Issues And Risks

- Many Korean comments/docs render as mojibake in PowerShell output. Before implementing from Korean docs, verify using a UTF-8-safe view.
- Frontend dependencies are not installed locally: `frontend/node_modules` does not exist.
- Root `.venv` is absent, although several docs reference `.\.venv\Scripts\python.exe`.
- 2026-06-01 investigation: local Docker DB has `analysis.information_cd` NULL count 0 and `IC01` `shop_cd` NULL count 0, but `crawling` has 3188 CA01 rows with blank `information_cd`/`shop_cd`; `analysis` currently enriches those rows to `IC01` and `shop.shop_cd`. Treat fixes that write back to `crawling` as a separate requirement because current docs/tests focus enrichment in `analysis`.
- 2026-06-01 investigation: local Docker DB still has 106 legacy `crawling.category_cd=IC02` rows with blank `information_cd`; current `get_reviews` only treats `category_cd=CA07` as IT, so those legacy rows are not represented in `analysis`.
- 2026-06-01 investigation: `analyze_it_keywords.py` is not present on current `dev`; it exists on `patch-post-analysis`. An Ollama `HTTP 404` in that script means the configured Ollama base URL or model should be checked on the machine that produced the log.
- 2026-06-02 investigation on branch `patch-model`: IC02 keyword extraction is implemented in `ai/post_analysis/analyze_it_keywords.py` with `compressed_content`, KiWi candidate extraction, candidate-limited prompts, and Ollama JSON calls. Local CSV sampling showed preprocessing/candidate extraction is sub-10ms per row after KiWi warmup; the primary remaining speed risk is row-by-row Ollama inference.
- 2026-06-02 patch: user approved keeping `AnalyzeItKeywordsConfig.DEFAULT_MODEL = "gemma4:e4b"`. Sparse valid LLM keywords are now supplemented from deterministic ranked candidates instead of making a second Ollama call, and IC02 target loading now uses a SQL-filtered helper instead of full-table `analysis`/`crawling` reads.
- 2026-06-02 patch follow-up: IC02 keyword extraction now has a conservative deterministic-first gate and an LLM candidate-id selector fallback. Current local DB 20-row benchmark (`test-results/it-keyword-benchmark/current-20-conservative`) classified 3/20 rows as deterministic and estimated 639.384 seconds saved at the measured 213.128s/LLM-call baseline. Live checks: fallback selector row 7 took 243.689s, deterministic row 8 took 2.309s. Main remaining risk is still row-by-row `gemma4:e4b`; id selection improves validation more than latency.
- 2026-06-02 patch follow-up: IC02 keyword extraction now supports bounded parallel workers, but the default remains `workers=1`. Local live benchmark with `gemma4:e4b` showed `workers=2` timed out both LLM rows under 300s, and completed two rows in 435.457s only after raising timeout to 600s. This is about 10.65% faster than the 487.378s estimated sequential baseline, not a 2x gain. Ollama `/api/ps` reported `size_vram=0`, so current local parallelism is CPU/memory-bound and should be treated as controlled experiment only.
- 2026-06-02 patch follow-up: IC02 deterministic keyword confidence now has a stricter quality gate before LLM skip: weak fragment tokens, one-letter mixed fragments, and repeated-token phrases are excluded from deterministic storage. The deterministic average-score threshold was relaxed from 17 to 16 only after that guard. Local non-mutating 50-row benchmark changed deterministic rows from 12 to 16 and LLM selector rows from 38 to 34, adding 852.512s estimated LLM-call savings at the 213.128s/call baseline.
- `README.md`, `TEST.md`, and several docs output garbled text in the current terminal. Treat direct terminal rendering as unreliable for Korean prose.
- Backend only exposes user auth URLs at present; frontend APIs refer to `/posts/`, `/api/posts/`, and map endpoints that are not wired in `backend/config/urls.py` based on current inspection.
- `backend/requirements.txt` pins `django==5.0.14`, while `backend/config/settings.py` header says generated by Django 6.0.2. Confirm runtime expectation before backend changes.
- `.env` exists in root but was not read to avoid exposing secrets.

## Verification

- Command: `Get-ChildItem -Force`
  - Location: `D:\dev\Project\SK-Connect`
  - Result: root project structure inspected.
- Command: `rg --files`
  - Location: `D:\dev\Project\SK-Connect`
  - Result: repository file inventory inspected.
- Command: `git status --short --branch`
  - Location: `D:\dev\Project\SK-Connect`
  - Result: branch `patch-post-analysis...origin/patch-post-analysis`; permission warnings for user git ignore.
- Command: `C:\Python314\python.exe -c "... ast.parse ..."`
  - Location: `D:\dev\Project\SK-Connect`
  - Result: parsed 268 Python files, bad 0.
- Command: `.\.venv\Scripts\python.exe -`
  - Location: `C:\dev\Project\SK-Connect`
  - Result: sampled `database/data/crawling.csv` IT-like rows for IC02 preprocessing and candidate extraction; 342 rows, 339 preprocessing successes, 3 empty-content preprocessing failures, median original length 1013 chars, median compressed length 352 chars, average preprocessing 0.423ms, average candidate extraction 5.281ms after KiWi warmup.

## Next Actions

- Before any implementation, identify the exact source-of-truth document for that feature and compare it against current code.
- For backend/API work, first confirm whether community/place/map endpoints should be implemented in Django or are intentionally outside this repo state.
- For frontend work, install dependencies or use the approved project setup before running Expo/web checks.
- For ETL/KAG work, use focused pytest targets matching the affected module and set `PYTHONPATH` exactly as existing docs/tests require.
- For future IC02 keyword speed work, keep `compressed_content` and candidate verification. Prompt candidate count changes, batching, caching, or parallel Ollama calls should be covered by a new source-of-truth implementation document before implementation.
