# `04_update_threads` — 댓글·이미지 보조 수집

`crawling` 테이블에 게시글이 적재된 **이후**에만 의미가 있다.  
[thread 수집 → 본문 → 클린징 → DB 삽입](../update_db_it_news.py) 파이프라인에는 **포함되어 있지 않으며**, 필요 시 **수동 실행**한다.

## 전제 조건

- PostgreSQL에 `crawling` 행이 있고, `thread`·`article_url`이 채워져 있을 것.
- 연결 정보: [insert_tables](../03_insert_tables/insert_tables.py)와 동일하게 `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD` 환경 변수(또는 코드 기본값).

## 스크립트 요약

| 스크립트 | `thread` 필터 | 데이터 소스 | 출력 CSV (기본 파일명) |
|----------|---------------|-------------|-------------------------|
| [gatter_reply_geeknews.py](gatter_reply_geeknews.py) | `geek_*` | GeekNews 토픽 HTML | `comment_geeknews_YYMMDD.csv` |
| [getter_images_geeknews.py](getter_images_geeknews.py) | `geek_*` | 토픽 HTML 본문(`topic_contents`) | `images_geeknews_YYMMDD.csv` |
| [gatter_reply_pytorch.py](gatter_reply_pytorch.py) | `pyto_*` | Discourse 토픽 JSON(답글 = `post_number` > 1) | `comment_pytorch_YYMMDD.csv` |
| [getter_images_pytorch.py](getter_images_pytorch.py) | `pyto_*` | Discourse 원글 `cooked` HTML | `images_pytorch_YYMMDD.csv` |

`YYMMDD`는 스크립트 실행일( KST 기준 `datetime` )이다.

## 공통 CLI

- `--timeout`: HTTP 타임아웃(초). 기본 `45`.
- `--sleep-seconds`: 토픽(행) 단위 요청 사이 대기. 기본 `0.75`.
- `--limit-topics`: DB에서 가져올 `crawling` 행 수 상한(앞에서부터).
- `-o` / `--output`: 출력 CSV 경로(미지정 시 위 표의 기본 이름·위치).

댓글 전용:

- `gatter_reply_geeknews.py`: `--max-comments` (토픽당 최대 댓글 수, 기본 500)
- `gatter_reply_pytorch.py`: `--max-replies` (토픽당 최대 답글 수, 기본 500)

## 실행 예 (레포 루트에서)

```bash
python etl/it_news/04_update_threads/gatter_reply_geeknews.py
python etl/it_news/04_update_threads/getter_images_geeknews.py --limit-topics 20

python etl/it_news/04_update_threads/gatter_reply_pytorch.py
python etl/it_news/04_update_threads/getter_images_pytorch.py --sleep-seconds 1.0 -o etl/it_news/04_update_threads/images_pytorch_custom.csv
```

## 소스별 동작·제한

### GeekNews

- 댓글: 토픽 페이지 HTML에 **SSR로 내려온** `div.comment_row`만 수집한다. 추가 페이지·지연 로드는 처리하지 않는다.
- 이미지: 본문 구간 `topic_contents` ~ `related-topics` 안의 `<img>`만 대상이다.

### PyTorchKR (Discourse)

- `thread` 값은 클린징 단계에서 `pyto_{topic_id}` 형태로 들어간다.
- 댓글: `t/{id}.json`의 `post_stream.posts`만으로 부족할 때(긴 토픽), `post_stream.stream`에 있는 누락 `post_id`를 `t/{id}/posts.json?post_ids[]=...`로 **추가 요청**해 병합한다.
- 이미지: **원글 한 개**(`post_number == 1`)의 `cooked`만 사용한다. 원글은 통상 첫 응답에 포함된다.

## 오케스트레이션

[update_db_it_news.py](../update_db_it_news.py)의 `_STEPS`에는 **아직 넣지 않는다**. 단계가 안정되면 선택적으로 추가할 수 있다.

## 후속 작업 (별도)

- 이 폴더 CSV에 대한 **cleaning**·**comments / images 테이블 INSERT** 스크립트.
- `get_connection_params` 등 중복 코드를 한 모듈로 묶는 리팩터(선택).
