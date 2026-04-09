--코드테이블--
CREATE TABLE codeT( 
    cd VARCHAR(6) PRIMARY KEY, --코드--
    name VARCHAR(30) NOT NULL, --이름--
    cd_info TEXT NOT NULL, --코드설명--
    cd_upper VARCHAR(6) NULL, --부모코드--
);


--사용자 테이블--
CREATE TABLE users(
    user_id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    nickname VARCHAR(100),
    profile_image VARCHAR(255),
    google_id VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status_cd VARCHAR(6) NOT NULL REFERENCES codeT(cd)
);

--지도테이블--
CREATE TABLE maps(
    map_id BIGSERIAL PRIMARY KEY, 
    name TEXT,
    category_cd VARCHAR(6) NOT NULL REFERENCES codeT(cd),--맛집/모임 구분--
    address_cd VARCHAR(6) NOT NULL REFERENCES codeT(cd), --주소 대분류(시군구 단위)--
    address_detail TEXT NOT NULL, --주소 상세--
    latitude FLOAT NOT NULL,      --위도--
    longitude FLOAT NOT NULL,     --경도--
);

--가게(맛집,...) 테이블
CREATE TABLE shop(
    shop_id BIGSERIAL PRIMARY KEY, --가게 고유 번호--
    map_id BIGINT NOT NULL REFERENCES maps(map_id), --지도 고유 번호--
    category_cd VARCHAR(6) NOT NULL REFERENCES codeT(cd), --한식/중식/양식/일식/카페/기타--
    rating FLOAT --평점--
);

--포스트 테이블 (맛집 댓글, 크롤링 게시글, 커뮤니티, 게시글)--
CREATE TABLE posts(
    post_id BIGSERIAL PRIMARY KEY, --게시글 고유 번호--
    title varchar(100) NOT NULL, --게시글 제목--
    content TEXT NOT NULL, --게시글 내용--
    created_at TIMESTAMP NOT NULL, --게시글 생성일--
    modify_at TIMESTAMP NOT NULL, --게시글 수정일--
    status_cd VARCHAR(6) NOT NULL REFERENCES codeT(cd), --게시글 상태(정상/삭제)--
    post_cd VARCHAR(6) NOT NULL REFERENCES codeT(cd), --post_cd를 통해 게시글과 커뮤니티, 댓글을 구분한다)--
    --user_id BIGINT NOT NULL REFERENCES users(user_id),--
    map_id BIGINT REFERENCES maps(map_id), --만약 커뮤니티나 맛집에 대한 내용이라면 map_id 작성--
    shop_id BIGINT REFERENCES shop(shop_id), --만약 맛집에 대한 내용이라면 shop_id 작성--
);

CREATE TABLE crawling(
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
    map_id BIGINT REFERENCES maps(map_id), --지도 고유 번호--
    category_cd VARCHAR(6) REFERENCES codeT(cd), --it/정보--
);  


CREATE TABLE menu(
    menu_id BIGSERIAL PRIMARY KEY, --메뉴 고유 번호--
    shop_id BIGINT REFERENCES shop(shop_id), --가게 고유 번호--
    name VARCHAR(100), --메뉴 이름--
    price INT, --메뉴 가격--
);

CREATE TABLE images(
    image_id BIGSERIAL PRIMARY KEY, --이미지 고유 번호--
    image_url VARCHAR(500) NOT NULL, --이미지 URL--
    table_name VARCHAR(20) NOT NULL, --테이블 이름--
    table_id BIGINT NOT NULL, --테이블 고유 번호--
);
CREATE INDEX idx_image_polymorphic ON images (table_name, table_id);

CREATE TABLE likes(
    like_id BIGSERIAL PRIMARY KEY, --좋아요 고유 번호--
    post_id BIGINT NOT NULL REFERENCES posts(post_id), --게시글 고유 번호--
    --user_id BIGINT NOT NULL REFERENCES users(user_id),--
);

CREATE TABLE comments(
    comment_id BIGSERIAL PRIMARY KEY, --댓글 고유 번호--
    post_id BIGINT NOT NULL REFERENCES posts(post_id), --게시글 고유 번호--
    --user_id BIGINT NOT NULL REFERENCES users(user_id),--
    content TEXT NOT NULL, --댓글 내용--    
    created_at TIMESTAMP NOT NULL, --생성일--
    modify_at TIMESTAMP NOT NULL, --수정일--
    status_cd VARCHAR(6) NOT NULL REFERENCES codeT(cd), --댓글 상태(정상/삭제)--
);