# 패키지
import pandas as pd
import psycopg
from psycopg.types.json import Jsonb
import numpy as np


# 모듈
from common.constant import AnalysisColumn
from common.postgresql.connection import PostgreDB


##############################################
# 서버에서 crwaling 테이블 데이터 로드 
##############################################
def get_crawling_data() -> pd.DataFrame:
    """ crawling 테이블의 데이터를 서버로 부터 읽어와서 데이터프레임으로 반환하는 함수 
    반환된 데이터 프레임은 이후 키워드 분석, 형태소 분해, 감정분류 등 처리를 위해 사용한다. 
    해당 함수의 역할은 데이터 불러오기만 하는 용도로 사용
    사용할 쿼리 현재 버전으로는 직접 정의해서 사용하되 나중에 범용 기능이 되면 분리 예정임 
    """

    db = PostgreDB()
    # 컬럼값 까지 확인 
    with db.conn.cursor() as cur:
        cur.execute("SELECT * FROM crawling")
        if cur.description is None:
            columns = []
        else:
            columns = [col.name for col in cur.description]
        rows = cur.fetchall()
    
    # 데이터 프레임으로 반환 
    return pd.DataFrame(rows, columns=columns)

##############################################
# 서버에서 analysis 테이블 데이터 로드 
##############################################
def get_analysis_data() -> pd.DataFrame:
    """ analysis 테이블의 데이터를 서버로 부터 읽어와서 데이터프레임으로 반환하는 함수 
    반환된 데이터 프레임은 이후 키워드 분석, 형태소 분해, 감정분류 등 처리를 위해 사용한다. 
    해당 함수의 역할은 데이터 불러오기만 하는 용도로 사용
    사용할 쿼리 현재 버전으로는 직접 정의해서 사용하되 나중에 범용 기능이 되면 분리 예정임 
    """

    db = PostgreDB()
    with db.conn.cursor() as cur:
        cur.execute("SELECT * FROM analysis")
        if cur.description is None:
            columns = []
        else:
            columns = [col.name for col in cur.description]
        rows = cur.fetchall()

    # 데이터 프레임으로 반환 
    return pd.DataFrame(rows, columns=columns)

##############################################
# 처리 후 데이터를 다시 analysis 테이블에 업데이트 
##############################################
def update_analysis_data_column(df: pd.DataFrame, column:str) -> None:
    """ 처리가 끝난 데이터 프레임을 다시 crawling 테이블에 업데이트 하는 함수 
    인자로는 적용할 데이터 프레임 자체 데이터에 추가로 업데이트를 적용할 컬럼 이름을 받는다. 
    업데이트 방식은 MERGE를 사용, 컬럼 이름을 지정해서 사용한다. 
    MERGE의 key는 crawling_id 컬럼을 사용한다. 

    - 대상 테이블: Analysis
    - 컬럼의 Key: crawling_id
    - 변경대상 컬럼 : column 인자로 받은 컬럼 이름
    """
    # 실제 테이블에 있는 컬럼만 허용 (SQL 인젝션 방지)
    if column not in AnalysisColumn.allowed_analysis_columns():
        raise ValueError(f"허용되지 않은 column: {column}")

    ids = df["crawling_id"].tolist()
    # 교체될 값 — 타입에 맞게 tolist() 전에 astype 등 정리
    vals = df[column].tolist()
    query = f"""
    UPDATE analysis AS a
    SET {column} = v.new_val
    FROM (
    SELECT unnest(%s::bigint[]) AS crawling_id,
            unnest(%s::text[]) AS new_val
    ) AS v
    WHERE a.crawling_id = v.crawling_id;
    """
    db = PostgreDB()
    with db.conn.cursor() as cur:
        cur.execute(query, (ids, vals))


    ##############################################
    # crawling테이블에서 analysis 테이블로 한번에 데이터 merge
    ##############################################

def merge_analysis_data(df: pd.DataFrame) -> None:
    """ 
    준비된 데이터를 analysis 테이블 스키마에 맞춰서 한번에 MERGE 하는 함수  
    """
    # crawling 테이블과 analysis 테이블을 한번에 merge 하는 함수 
    MERGE_ANALYSIS_SQL = r"""
    MERGE INTO analysis AS a
    USING (
    SELECT * FROM jsonb_to_recordset(%s::jsonb) AS s (
        crawling_id   bigint,
        title         varchar(500),
        content       text,
        article_url   varchar(500),
        map_id        bigint,
        shop_id       bigint,
        category_cd   varchar(6),
        created_dt    timestamp,
        sentimental   varchar(50),
        score         double precision,
        keywords      text,
        positive_kw   text,
        negative_kw   text
    )
    ) AS x
    ON a.crawling_id = x.crawling_id
    WHEN MATCHED THEN
    UPDATE SET
        title = x.title, content = x.content, article_url = x.article_url,
        map_id = x.map_id, shop_id = x.shop_id, category_cd = x.category_cd,
        created_dt = x.created_dt, sentimental = x.sentimental, score = x.score,
        keywords = x.keywords, positive_kw = x.positive_kw, negative_kw = x.negative_kw
    WHEN NOT MATCHED THEN
    INSERT (
        crawling_id, title, content, article_url, map_id, shop_id,
        category_cd, created_dt, sentimental, score, keywords, positive_kw, negative_kw
    )
    VALUES (
        x.crawling_id, x.title, x.content, x.article_url, x.map_id, x.shop_id,
        x.category_cd, x.created_dt, x.sentimental, x.score, x.keywords,
        x.positive_kw, x.negative_kw
    );
    """

    db = PostgreDB()

    # 데이터 입력 시 터질 수 있는 결측치 들 확인해서 처리 
    clean = df.replace({np.nan: None, pd.NA: None})
    clean = clean.where(pd.notnull(clean), None)

    # 시간값인 경우 형식 변환 
    if "created_dt" in clean.columns:
        s = pd.to_datetime(clean["created_dt"], errors="coerce")
        clean["created_dt"] = s.dt.strftime("%Y-%m-%dT%H:%M:%S").where(s.notna(), None)

    # bigint 컬럼값 정수로 처리 
    for col in ("crawling_id", "map_id", "shop_id"):
        if col in clean.columns:
            clean[col] = pd.to_numeric(clean[col], errors="coerce").astype("Int64")
    
    # 처리된 데이터 다시 반환 
    records = clean.to_dict(orient="records")

    with db.conn.cursor() as cur:
        cur.execute(MERGE_ANALYSIS_SQL, (Jsonb(records),))