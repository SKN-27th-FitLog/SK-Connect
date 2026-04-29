 # Analysis 테이블 
 - 리뷰/블로그 글들을 분석한 내용을 가져와서 분석하기 위한 별도 테이블 
 - 테이블은 다음 컬럼값을 가진다. 

| 컬럼명        | 타입            | 값                                      |
|---------------|-----------------|------------------------------------------|
| crawling_id   | int             | crawling.crawling_id                     |
| category_cd   | codetable       | crawling.category_cd (IC01)              |
| title         | str             | crawling.title                           |
| content       | str             | crawling.content                         |
| map_id        | int             | crawling.map_id                          |
| shop_id       | int             | shop.map_id                              |
| created_dt    | datetime        | 2016-04-25 15:55:02                      |
| sentimental   | enum            | positive / negative                      |
| score         | float           | 0.3356                                   |
| keywords         | list[str] | ["keyword1", "keyword2", ...]                                    |
| positive_kw   | list[str]       | ["keyword1", "keyword2", ...]            |
| negative_kw   | list[str]       | ["keyword3", "keyword4", ...]            |


# get_reviews()
 - crawling 테이블에서 Analysis 테이블로 컬럼 값을 가져오고 가져온 시간을 created_dt 컬럼에 기록함
 1) crawling 테이블에서 Analysis 테이블로 데이터를 MERGE 한다. 
 2) created_dt 컬럼값은 가져온 시점의 시간으로 결정한다. 

```mermaid
sequenceDiagram
    participant Func as get_reviews()
    participant DB as Crawling
    participant AN as Analysis

    Func->>DB: crawling 테이블 조회 요청
    DB->>Func: crawling 테이블 데이터 return
    Func->>AN: MERGE INTO Analysis<br/>(crawling 소스 기준)
    Func-->>AN: 반영 시 created_dt를 현재 시간으로 설정
```


 # analyze_sentimental()
 - 감성분석이 가능한 데이터들에 대해 감성분석 적용한다. 
 - enum으로 만들되 메서드로 해서 감성분석 가능한 컬럼 리스트를 구하는 함수 만들어 처리하는걸로 검토
 - Analysis 테이블에서 감성분석이 되지 않은 글들을 가져와 감성분석 적용한다. 
 1) sentimental IS NULL인 글 SELECT해서 가져온다. (감성분석이 가능한 글 중 아직 값이 없는 것들 )
 2) 가져온 글들을 BERT 모델을 사용해서 감성분석 진행한다. 
 3) 감성분석 후 나온 결과를 sentimental, score 컬럼에 적용한다. 

```mermaid
 sequenceDiagram
    participant Func as analyze_sentimental()
    participant BERT as BERT Model
    participant DB as Analysis

    Func->>DB: Analysis 테이블 조회 요청<br/>조건: sentimental IS NULL AND category_cd = 'IC01'
    DB-->>Func: 감성분석 대상 글 반환

    Func->>BERT: content 컬럼 감성분석 요청
    BERT-->>Func: 분석 결과 반환

    Func->>DB: sentimental, score 분석 결과 업데이트 
```

 # analyze_keywords()
 1) keywords IS NULL인 글 SELECT 한다.  
 2) 가져온 글들을 kiwi를 사용해서 형태소 분석 / 키워드 추출 진행한다. 
 3) 추출된 키워드 리스트 keywords에 등록한다. 

```mermaid
 sequenceDiagram
    participant Func as analyze_keywords()
    participant Kiwi as Kiwi NLP
    participant DB as Analysis


    Func->>DB: Analysis 테이블 조회 요청<br/>조건: keywords IS NULL
    DB-->>Func: 키워드 추출 대상 목록 반환 

    Func->>Kiwi: content 기반 형태소 분석 및 키워드 추출 요청
    Kiwi-->>Func: 키워드 리스트 반환
    Func->>DB: keywords 컬럼에 키워드 리스트 적용

```

# classify_keywords()
 - Analysis 테이블에서 키워드 추출이 완료된 IC01인 글을 가져와 키워드 분류 한다.
 1) positive_kw IS NULL AND negative_kw IS NULL인 글 SELECT
 2) LLM 또는 Bert모델에게 keywords 기반 키워드 분류를 요청한다. (긍정/부정 라벨링 작업)
 3) 키워드를 분류해서 긍정 키워드는 positive_kw, 부정 키워드는 negative_kw에 분류한다. 
 4) 분류한 데이터를 다시 Analysis 테이블에 적용한다. 


```mermaid
 sequenceDiagram
    participant Func as classify_keywords()
    participant Model as LLM / BERT
    participant DB as Analysis 


    Func->>DB: Analysis 테이블 조회 요청<br/>조건: positive_kw IS NULL AND negative_kw IS NULL AND category_cd = 'IC01'
    DB-->>Func: 키워드 분류 대상 글 반환

    Func->>Model: keywords 기반 키워드 감성 분류 요청<br/>(긍정/부정 라벨링)
    Model-->>Func: 키워드 분류해서 각 컬럼에 반환 


    Func->>DB : 분류한 키워드를 positive_kw, negative_kw에 적용한다. 
```