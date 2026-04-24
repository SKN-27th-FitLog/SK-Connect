## 1. 크롤링

게시판에서 URL을 모은 뒤 게시글별로 HTML을 받아 파싱하고, 행 단위로 성공·실패를 나눕니다.

```mermaid
sequenceDiagram
    participant 크롤링
    participant 웹페이지
    participant 게시글
    participant 로컬
    participant DB

    alt 마지막 수집일 조회
        크롤링->>DB: crawling.created_at MAX 조회
        DB-->>크롤링: MAX(created_at) 반환
    end

    alt 게시글 URL 목록 수집
        크롤링->>웹페이지: 게시판 목록 요청
        웹페이지-->>크롤링: 게시글 URL 목록
    end

    loop 게시글 URL마다
        크롤링->>게시글: HTML 문서 요청
        게시글-->>크롤링: HTML (파싱용 문서)
        크롤링->>크롤링: 컬럼별 필드 추출
        alt 추출·검증 성공
            크롤링->>로컬: df_success에 행 추가
        else 실패
            크롤링->>로컬: df_fail에 URL·에러 추가
        end
    end

    alt CSV 기록
        크롤링->>로컬: df_success 또는 df_fail에 행이 있음 > CSV 저장
    end
```

---

## 2. 클리닝

같은 기준일로 크롤링 성공 CSV를 합친 뒤 전처리하고, `State`로 성공·실패를 구분해 다시 CSV로 씁니다.

```mermaid
sequenceDiagram
    participant 클리닝
    participant 데이터로드
    participant 전처리
    participant 로컬
    participant DB

    alt 마지막 수집일 조회
        클리닝->>DB: crawling.created_at MAX 조회
        DB-->>클리닝: 마지막 수집일
    end

    alt 대상 데이터 로드
        클리닝->>데이터로드: 기준일 이후 크롤링 성공 CSV
        데이터로드-->>클리닝: DataFrame concat
    end

    alt 전처리
        클리닝->>전처리: thread 기준 중복 제거
        클리닝->>전처리: 주요 컬럼 이상치 검사 (title, content, article_url, thread, category_cd)
        전처리-->>클리닝: 이상치 행 → State = fail
        클리닝->>전처리: 나머지 컬럼 DB 스키마에 맞게 정규화
        전처리-->>클리닝: 정규화 오류 행 → State = fail
    end

    alt 결과 CSV 저장
        클리닝->>로컬: State = success → df_success
        클리닝->>로컬: State = fail → df_fail
        opt df_success 또는 df_fail에 행이 있음
            클리닝->>로컬: CSV 파일로 기록
        end
    end
```

---

## 3. DB 저장

클리닝 성공분을  `crawling` 테이블에 머지하고, 결과를 다시 성공·실패 CSV로 남깁니다.

```mermaid
sequenceDiagram
    participant 저장
    participant 데이터로드
    participant 로컬
    participant DB

    alt 마지막 수집일 조회
        저장->>DB: crawling.created_at MAX 조회
        DB-->>저장: 마지막 수집일
    end

    alt 대상 데이터 로드
        저장->>데이터로드: 기준일 이후 클리닝 성공 CSV
        데이터로드-->>저장: DataFrame concat
    end

    alt DB 반영
        저장->>DB: crawling 테이블에 DataFrame 머지
        DB-->>저장: 저장 실패한 행
    end

    alt 결과 CSV 저장
        저장->>로컬: 성공 반영분 → df_success
        저장->>로컬: DB 저장 실패 행 → df_fail
        opt df_success 또는 df_fail에 행이 있음
            저장->>로컬: CSV 파일로 기록
        end
    end
```
