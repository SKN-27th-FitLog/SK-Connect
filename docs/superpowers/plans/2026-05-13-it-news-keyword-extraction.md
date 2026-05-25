# IT News Keyword Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `Design_V2.md` IT news keyword extraction pipeline from normalized article JSONL to keyword extraction JSONL and Neo4j import statements.

**Architecture:** Add a new `kag_graph.extraction` package that is separate from the existing CSV-based `hive_importer.py` path. The extraction service reads normalized articles, runs preprocessing, ranking, dictionary resolution, LLM classification, validation, and writes success/fail/metrics JSONL/JSON outputs. Neo4j import is added as a JSONL-based path without replacing existing importer behavior.

**Tech Stack:** Python 3.14 virtualenv, pytest, `kiwipiepy` for Korean morphology, standard-library JSON/CSV/path/dataclass modules, existing Neo4j statement pattern.

---

### Task 1: Virtualenv And Dependencies

**Files:**
- Modify: `kag/pyproject.toml`

- [ ] **Step 1: Add dependency contract**

Add `kiwipiepy` to project dependencies because `Design_V2.md` explicitly selects Kiwi.

- [ ] **Step 2: Create or reuse virtualenv**

Run: `C:\Python314\python.exe -m venv .venv`

- [ ] **Step 3: Install package in editable mode**

Run: `.venv\Scripts\python.exe -m pip install -e kag[test]`

- [ ] **Step 4: Verify import**

Run: `.venv\Scripts\python.exe -c "from kiwipiepy import Kiwi; print(Kiwi)"`

---

### Task 2: Extraction Models

**Files:**
- Create: `kag/src/kag_graph/extraction/__init__.py`
- Create: `kag/src/kag_graph/extraction/models.py`
- Test: `kag/tests/test_keyword_extraction_models.py`

- [ ] **Step 1: Write failing tests**

Cover normalized article validation, malformed reason codes, review reason constants, keyword extraction record shape, and metrics status.

- [ ] **Step 2: Run tests and verify RED**

Run: `.venv\Scripts\python.exe -m pytest kag\tests\test_keyword_extraction_models.py -v`

- [ ] **Step 3: Implement dataclasses/constants**

Implement `NormalizedArticle`, `KeywordCandidate`, `ClassifiedKeyword`, `EventSignal`, `KeywordExtractionRecord`, `MalformedArticleRecord`, `ExtractionMetrics`, `ReviewReason`, and `MalformedReason`.

- [ ] **Step 4: Run tests and verify GREEN**

Run: `.venv\Scripts\python.exe -m pytest kag\tests\test_keyword_extraction_models.py -v`

---

### Task 3: Preprocessing And Corpus Ranking

**Files:**
- Create: `kag/src/kag_graph/extraction/preprocessing/__init__.py`
- Create: `kag/src/kag_graph/extraction/preprocessing/korean_morph_analyzer.py`
- Create: `kag/src/kag_graph/extraction/preprocessing/token_filter.py`
- Create: `kag/src/kag_graph/extraction/preprocessing/candidate_phrase_builder.py`
- Create: `kag/src/kag_graph/extraction/preprocessing/action_signal_extractor.py`
- Create: `kag/src/kag_graph/extraction/corpus_context_builder.py`
- Create: `kag/src/kag_graph/extraction/hybrid_keyword_ranker.py`
- Test: `kag/tests/test_keyword_extraction_preprocessing.py`
- Test: `kag/tests/test_keyword_extraction_ranking.py`

- [ ] **Step 1: Write failing preprocessing tests**

Cover Kiwi token extraction, filtering rules, 1~3 ngram candidate creation, and action signal extraction without keyword node creation.

- [ ] **Step 2: Write failing ranking tests**

Cover batch corpus `document_count`, small corpus review signal, max 10 keywords, min score filtering, and `tfidf_textrank_hybrid_v1`.

- [ ] **Step 3: Run tests and verify RED**

Run: `.venv\Scripts\python.exe -m pytest kag\tests\test_keyword_extraction_preprocessing.py kag\tests\test_keyword_extraction_ranking.py -v`

- [ ] **Step 4: Implement preprocessing and deterministic hybrid ranking**

Use Kiwi for morphology. Implement lightweight TF-IDF/TextRank without adding dependencies beyond `kiwipiepy`.

- [ ] **Step 5: Run tests and verify GREEN**

Run: `.venv\Scripts\python.exe -m pytest kag\tests\test_keyword_extraction_preprocessing.py kag\tests\test_keyword_extraction_ranking.py -v`

---

### Task 4: Dictionary, LLM, Parser, Validator

**Files:**
- Create: `kag/src/kag_graph/extraction/dictionary_resolver.py`
- Create: `kag/src/kag_graph/extraction/llm_client.py`
- Create: `kag/src/kag_graph/extraction/providers/__init__.py`
- Create: `kag/src/kag_graph/extraction/providers/mock_llm_client.py`
- Create: `kag/src/kag_graph/extraction/response_parser.py`
- Create: `kag/src/kag_graph/extraction/keyword_schema_validator.py`
- Test: `kag/tests/test_keyword_extraction_classification.py`
- Test: `kag/tests/test_keyword_schema_validator.py`

- [ ] **Step 1: Write failing tests**

Cover exact/lower/trim/alias matching, alias conflict review, LLM dictionary-only fallback, JSON block parser failure, confidence thresholds, Ignore removal, recoverable validator errors, unrecoverable validator errors, and all review_required automatic conditions.

- [ ] **Step 2: Run tests and verify RED**

Run: `.venv\Scripts\python.exe -m pytest kag\tests\test_keyword_extraction_classification.py kag\tests\test_keyword_schema_validator.py -v`

- [ ] **Step 3: Implement classifier support modules**

Implement dictionary resolution, mock LLM classifier, response parser, and validator exactly according to `Design_V2.md`.

- [ ] **Step 4: Run tests and verify GREEN**

Run: `.venv\Scripts\python.exe -m pytest kag\tests\test_keyword_extraction_classification.py kag\tests\test_keyword_schema_validator.py -v`

---

### Task 5: Writer And Extraction Service

**Files:**
- Create: `kag/src/kag_graph/extraction/writer/__init__.py`
- Create: `kag/src/kag_graph/extraction/writer/keyword_extraction_writer.py`
- Create: `kag/src/kag_graph/extraction/extraction_service.py`
- Test: `kag/tests/test_keyword_extraction_writer.py`
- Test: `kag/tests/test_extraction_service.py`

- [ ] **Step 1: Write failing writer tests**

Cover UTF-8 JSONL writes, timestamped non-overwrite filenames, fail JSONL path, and metrics JSON path.

- [ ] **Step 2: Write failing service tests**

Cover normalized JSONL input, malformed schema handling, partial success, LLM fallback, review_required saved as success, and metrics counts.

- [ ] **Step 3: Run tests and verify RED**

Run: `.venv\Scripts\python.exe -m pytest kag\tests\test_keyword_extraction_writer.py kag\tests\test_extraction_service.py -v`

- [ ] **Step 4: Implement writer and service**

Keep orchestration in `ExtractionService`; do not write Neo4j, poll S3, use Redis, or generate Cypher here.

- [ ] **Step 5: Run tests and verify GREEN**

Run: `.venv\Scripts\python.exe -m pytest kag\tests\test_keyword_extraction_writer.py kag\tests\test_extraction_service.py -v`

---

### Task 6: Neo4j JSONL Import

**Files:**
- Create: `kag/src/kag_graph/it_news_importer.py`
- Modify: `kag/queries/schema/constraints.cypher`
- Test: `kag/tests/test_it_news_importer.py`
- Test: `kag/tests/test_kag_static_contract.py`

- [ ] **Step 1: Write failing importer tests**

Cover `NewsArticle` properties, canonical-name MERGE for `Technology`, `Company`, `Event`, `Topic`, relationship names from `Design_V2.md`, Ignore absence, and `event_signals` JSON property storage only.

- [ ] **Step 2: Write failing constraint test**

Cover `canonical_name` uniqueness constraints for `Technology`, `Company`, `Event`, and `Topic`.

- [ ] **Step 3: Run tests and verify RED**

Run: `.venv\Scripts\python.exe -m pytest kag\tests\test_it_news_importer.py kag\tests\test_kag_static_contract.py -v`

- [ ] **Step 4: Implement importer and constraints**

Add JSONL import statement builder without changing existing CSV importer behavior.

- [ ] **Step 5: Run tests and verify GREEN**

Run: `.venv\Scripts\python.exe -m pytest kag\tests\test_it_news_importer.py kag\tests\test_kag_static_contract.py -v`

---

### Task 7: Final Verification

- [ ] **Step 1: Run focused extraction suite**

Run: `.venv\Scripts\python.exe -m pytest kag\tests\test_keyword_extraction_models.py kag\tests\test_keyword_extraction_preprocessing.py kag\tests\test_keyword_extraction_ranking.py kag\tests\test_keyword_extraction_classification.py kag\tests\test_keyword_schema_validator.py kag\tests\test_keyword_extraction_writer.py kag\tests\test_extraction_service.py kag\tests\test_it_news_importer.py -v`

- [ ] **Step 2: Run full kag suite**

Run: `.venv\Scripts\python.exe -m pytest kag\tests -v`

- [ ] **Step 3: Inspect git diff**

Run: `git status --short` and review touched files.
