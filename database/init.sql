--코드테이블--
CREATE TABLE codeT( 
    cd VARCHAR(6) PRIMARY KEY, --코드--
    name VARCHAR(30) NOT NULL, --이름--
    cd_info TEXT NOT NULL, --코드설명--
    cd_upper VARCHAR(6) NULL, --부모코드--
);

--지도테이블--
CREATE TABLE maps(
    map_id BIGSERIAL PRIMARY KEY, 
    name TEXT,
    category_cd VARCHAR(6) NOT NULL REFERENCES codeT(cd),
    address_cd VARCHAR(6) NOT NULL REFERENCES codeT(cd), --주소 대분류(시군구 단위)--
    address_detail TEXT NOT NULL,
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
);

--가게(맛집,...) 테이블
CREATE TABLE shop(
    shop_id BIGSERIAL PRIMARY KEY,
    map_id BIGINT NOT NULL REFERENCES maps(map_id),
    category_cd VARCHAR(6) NOT NULL REFERENCES codeT(cd),
    rating FLOAT
);

--포스트 테이블 (맛집 댓글, 크롤링 게시글, 커뮤니티, 게시글)--
CREATE TABLE posts(
    post_id BIGSERIAL PRIMARY KEY,
    title varchar(100) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    modify_at TIMESTAMP NOT NULL,
    status_cd VARCHAR(6) NOT NULL REFERENCES codeT(cd),
    post_cd VARCHAR(6) NOT NULL REFERENCES codeT(cd), --post_cd를 통해 게시글과 커뮤니티, 댓글을 구분한다)--
    --user_id BIGINT NOT NULL REFERENCES users(user_id),--
    map_id BIGINT REFERENCES maps(map_id), --만약 커뮤니티나 맛집에 대한 내용이라면 map_id 작성--
    shop_id BIGINT REFERENCES shop(shop_id),

);

CREATE TABLE crawling(
    crawling_id BIGSERIAL PRIMARY KEY,
    title varchar(200),
    content TEXT,
    thread VARCHAR(20),
    article_url VARCHAR(500),
    created_at TIMESTAMP,
    view_count INT,
    comment_count INT,
    point FLOAT,
    author VARCHAR(100),
    map_id BIGINT REFERENCES maps(map_id),
    category_cd VARCHAR(6) REFERENCES codeT(cd),
);  


CREATE TABLE menu(
    menu_id BIGSERIAL PRIMARY KEY,
    shop_id BIGINT REFERENCES shop(shop_id),
    name VARCHAR(100),
    price INT,
);

CREATE TABLE images(
    image_id BIGSERIAL PRIMARY KEY,
    image_url VARCHAR(500) NOT NULL,
    table_name VARCHAR(20) NOT NULL,
    table_id BIGINT NOT NULL
);
CREATE INDEX idx_image_polymorphic ON images (table_name, table_id);

CREATE TABLE likes(
    like_id BIGSERIAL PRIMARY KEY,
    post_id BIGINT NOT NULL REFERENCES posts(post_id),
    --user_id BIGINT NOT NULL REFERENCES users(user_id),--
);

CREATE TABLE comments(
    comment_id BIGSERIAL PRIMARY KEY,
    post_id BIGINT NOT NULL REFERENCES posts(post_id),
    --user_id BIGINT NOT NULL REFERENCES users(user_id),--
    content TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    modify_at TIMESTAMP NOT NULL,
    status_cd VARCHAR(6) NOT NULL REFERENCES codeT(cd),
);