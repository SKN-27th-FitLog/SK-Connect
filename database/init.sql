--코드테이블--
CREATE TABLE "codeT"( 
    cd VARCHAR(6) PRIMARY KEY, --코드--
    name VARCHAR(30) NOT NULL, --이름--
    cd_info TEXT NOT NULL, --코드설명--
    cd_upper VARCHAR(6) NULL --부모코드--
);

--사용자 테이블--
CREATE TABLE "users"(
    user_id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    nickname VARCHAR(100),
    profile_image VARCHAR(255),
    google_id VARCHAR(255) UNIQUE,              -- NOT NULL 제거 (Day 2에서 컬럼 자체 삭제 예정)
    role VARCHAR(10) DEFAULT 'user',            -- 추가
    created_at TIMESTAMP NOT NULL,
    status_cd VARCHAR(6) NOT NULL
);
-- 소셜 로그인 계정 테이블
CREATE TABLE "social_accounts" (
    id               BIGSERIAL PRIMARY KEY,
    user_id          BIGINT NOT NULL REFERENCES "users"(user_id) ON DELETE CASCADE,
    provider         VARCHAR(20) NOT NULL,
    provider_user_id VARCHAR(100) NOT NULL,
    created_at       TIMESTAMP DEFAULT NOW(),
    UNIQUE (provider, provider_user_id)
);

-- Refresh Token 관리 테이블
CREATE TABLE "refresh_tokens" (
    id         BIGSERIAL PRIMARY KEY,
    user_id    BIGINT NOT NULL REFERENCES "users"(user_id) ON DELETE CASCADE,
    token      VARCHAR(512) NOT NULL UNIQUE,
    ip_address INET,
    user_agent TEXT,
    is_revoked BOOLEAN DEFAULT FALSE,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 의심 로그인 기록 테이블
CREATE TABLE "suspicious_logins" (
    id         BIGSERIAL PRIMARY KEY,
    user_id    BIGINT NOT NULL REFERENCES "users"(user_id) ON DELETE CASCADE,
    ip_address INET NOT NULL,
    user_agent TEXT,
    status     VARCHAR(10) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
);

--지도테이블--
CREATE TABLE "maps"(
    map_id BIGSERIAL PRIMARY KEY, 
    name TEXT,
    category_cd VARCHAR(6) NOT NULL,--맛집/모임 구분--
    address_cd VARCHAR(6) NOT NULL, --주소 대분류(시군구 단위)--
    address_detail TEXT NOT NULL, --주소 상세--
    latitude FLOAT NOT NULL,      --위도--
    longitude FLOAT NOT NULL      --경도--
);

--가게(맛집,...) 테이블
CREATE TABLE "shop"(
    shop_id BIGSERIAL PRIMARY KEY, --가게 고유 번호--
    map_id BIGINT NOT NULL REFERENCES maps(map_id) ON DELETE CASCADE, --지도 고유 번호--
    shop_cd VARCHAR(6) NOT NULL, --한식/중식/양식/일식/카페/기타--
    rating FLOAT --평점--
);


CREATE TABLE "crawling"(
    crawling_id BIGSERIAL PRIMARY KEY, --크롤링 고유 번호--
    title varchar(200), --제목--
    content TEXT, --내용--
    thread VARCHAR(20), --스레드--
    article_url VARCHAR(500), --게시글 URL--
    created_at TIMESTAMP, --생성일--
    view_count INT, --조회수--
    comment_count INT, --댓글수--
    point FLOAT, --평점--
    author VARCHAR(100), --작성자--
    map_id BIGINT REFERENCES maps(map_id) ON DELETE SET NULL, --지도 고유 번호--
    category_cd VARCHAR(6), --it/정보--
    keywords VARCHAR(100) --키워드--
);

--포스트 테이블 (맛집 댓글, 크롤링 게시글, 커뮤니티, 게시글)--
CREATE TABLE "posts"(
    post_id BIGSERIAL PRIMARY KEY, --게시글 고유 번호--
    title varchar(100) NOT NULL, --게시글 제목--
    content TEXT NOT NULL, --게시글 내용--
    created_at TIMESTAMP NOT NULL, --게시글 생성일--
    modify_at TIMESTAMP NOT NULL, --게시글 수정일--
    status_cd VARCHAR(6) NOT NULL, --게시글 상태(정상/삭제)--
    post_cd VARCHAR(6) NOT NULL, --post_cd를 통해 게시글과 커뮤니티, 댓글을 구분한다)--
    category_cd VARCHAR(6), --카테고리 코드--
    user_id BIGINT REFERENCES users(user_id),
    map_id BIGINT REFERENCES maps(map_id) ON DELETE SET NULL, --만약 커뮤니티나 맛집에 대한 내용이라면 map_id 작성--
    shop_id BIGINT REFERENCES shop(shop_id) ON DELETE SET NULL, --만약 맛집에 대한 내용이라면 shop_id 작성--
    crawling_id BIGINT REFERENCES crawling(crawling_id) ON DELETE SET NULL, --크롤링 고유 번호-- (FK는 아래에서 추가)
    tag VARCHAR(100) --게시글 태그--
);


CREATE TABLE "menu"(
    menu_id BIGSERIAL PRIMARY KEY, --메뉴 고유 번호--
    shop_id BIGINT NOT NULL REFERENCES shop(shop_id) ON DELETE CASCADE, --가게 고유 번호--
    name VARCHAR(100) NOT NULL, --메뉴 이름--
    price INT --메뉴 가격--
);

CREATE TABLE "images"(
    image_id BIGSERIAL PRIMARY KEY, --이미지 고유 번호--
    image_url VARCHAR(500) NOT NULL, --이미지 URL--
    table_name VARCHAR(20) NOT NULL, --테이블 이름--
    table_id BIGINT NOT NULL --테이블 고유 번호--
);

CREATE TABLE "likes"(
    like_id BIGSERIAL PRIMARY KEY, --좋아요 고유 번호--
    post_id BIGINT NOT NULL REFERENCES posts(post_id) ON DELETE CASCADE, --게시글 고유 번호--
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE "comments"(
    comment_id BIGSERIAL PRIMARY KEY, --댓글 고유 번호--
    post_id BIGINT REFERENCES posts(post_id) ON DELETE CASCADE, --게시글 고유 번호--
    crawling_id BIGINT REFERENCES crawling(crawling_id) ON DELETE CASCADE, --크롤링 고유 번호--
    user_id BIGINT NOT NULL REFERENCES users(user_id),
    content TEXT NOT NULL, --댓글 내용--    
    created_at TIMESTAMP NOT NULL, --생성일--
    modify_at TIMESTAMP NOT NULL, --수정일--
    status_cd VARCHAR(6) NOT NULL --댓글 상태(정상/삭제)--
);

CREATE EXTENSION IF NOT EXISTS vector;
-- LangChain PGVector 전용 테이블
-- 주의: langchain_postgres.PGVector를 사용하는 경우 아래 테이블명은 라이브러리 내부에서 고정으로 사용된다.
--       (langchain_pg_collection, langchain_pg_embedding)
--       따라서 테이블명을 임의 변경하면 add_documents/similarity_search 동작이 깨질 수 있다.
--       커스텀 이름을 원하면 라이브러리 코드를 포크/수정하거나 별도 직접 SQL 저장 로직을 사용해야 한다.
CREATE TABLE "langchain_pg_collection"(
    uuid UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    cmetadata JSON
);

CREATE TABLE "langchain_pg_embedding"(
    id VARCHAR(255) PRIMARY KEY,
    collection_id UUID REFERENCES langchain_pg_collection(uuid) ON DELETE CASCADE,
    embedding vector(768),
    document TEXT,
    cmetadata JSONB
);

CREATE INDEX "ix_cmetadata_gin"
ON "langchain_pg_embedding"
USING gin (cmetadata jsonb_path_ops);

-- 참고:
-- 1) 일반 게시글 원본 데이터는 posts 테이블에 저장
-- 2) 벡터 검색용 데이터는 langchain_pg_embedding.document/cmetadata/embedding에 저장
--    (document = page_content, cmetadata = metadata)


COPY "codeT" (cd, name, cd_info, cd_upper) FROM '/docker-entrypoint-initdb.d/data/codeT.csv' DELIMITER ',' CSV HEADER;


-- post 생성 용 데이터 분석 테이블 --
CREATE TABLE "analysis"(
    crawling_id BIGINT PRIMARY KEY, --크롤링 고유 번호 (crawling과 동일 값, FK 없음)--
    title VARCHAR(200), --제목--
    content TEXT, --내용--
    article_url VARCHAR(500), --게시글 URL--
    map_id BIGINT, --지도 고유 번호 (crawling과 동일 타입, FK 없음)--
    shop_id BIGINT, --가게 고유 번호 (FK 없음)--
    category_cd VARCHAR(6), --카테고리 코드 (crawling.category_cd와 동일 제약)--
    created_dt TIMESTAMP, --분석 테이블로 적재된 시각--
    sentimental VARCHAR(16), --positive / negative, 미분석 시 NULL--
    score FLOAT, --감성 점수--
    keywords TEXT, --키워드 목록 (# 구분)--
    positive_kw TEXT, --긍정 키워드 (# 구분)--
    negative_kw TEXT --부정 키워드 (# 구분)--
);

-------------------------------------------------------------------------------
-- 해당 파일들은 2026년 4월 29일 기준 스냅샷 (테스트 용이하게 하기위한 용도) --
COPY "maps" (map_id, name, category_cd, address_cd, address_detail, latitude, longitude) FROM '/docker-entrypoint-initdb.d/data/maps.csv' DELIMITER ',' CSV HEADER;
COPY "shop" (shop_id, map_id, shop_cd, rating) FROM '/docker-entrypoint-initdb.d/data/shop.csv' DELIMITER ',' CSV HEADER;
COPY "crawling" (crawling_id, title, content, thread, article_url, created_at, view_count, comment_count, point, author, map_id, category_cd, keywords) FROM '/docker-entrypoint-initdb.d/data/crawling.csv' DELIMITER ',' CSV HEADER;
COPY "menu" (menu_id, shop_id, name, price) FROM '/docker-entrypoint-initdb.d/data/menu.csv' DELIMITER ',' CSV HEADER;
COPY "images" (image_id, image_url, table_name, table_id) FROM '/docker-entrypoint-initdb.d/data/images.csv' DELIMITER ',' CSV HEADER;
COPY "analysis" (crawling_id, title, content, article_url, map_id, shop_id, category_cd, created_dt, sentimental, score, keywords, positive_kw, negative_kw) FROM '/docker-entrypoint-initdb.d/data/analysis.csv' DELIMITER ',' CSV HEADER;

-- 시드 COPY로 명시적 PK를 넣었으므로 시퀀스를 MAX에 맞춤 (다음 INSERT 시 충돌 방지)
SELECT setval(pg_get_serial_sequence('maps', 'map_id'), COALESCE((SELECT MAX(map_id) FROM "maps"), 1));
SELECT setval(pg_get_serial_sequence('shop', 'shop_id'), COALESCE((SELECT MAX(shop_id) FROM "shop"), 1));
SELECT setval(pg_get_serial_sequence('crawling', 'crawling_id'), COALESCE((SELECT MAX(crawling_id) FROM "crawling"), 1));
SELECT setval(pg_get_serial_sequence('menu', 'menu_id'), COALESCE((SELECT MAX(menu_id) FROM "menu"), 1));
SELECT setval(pg_get_serial_sequence('images', 'image_id'), COALESCE((SELECT MAX(image_id) FROM "images"), 1));