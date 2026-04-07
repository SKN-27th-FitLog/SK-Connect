CREATE TABLE codeT(
    cd VARCHAR(6) PRIMARY KEY,
    name VARCHAR(30) NOT NULL,
    cd_info TEXT NOT NULL,
    cd_upper VARCHAR(6) NULL,
);

CREATE TABLE maps(
    map_id BIGSERIAL PRIMARY KEY,
    name TEXT,
    category_cd VARCHAR(6) NOT NULL REFERENCES codeT(cd),
    address_cd VARCHAR(6) NOT NULL REFERENCES codeT(cd),
    address_detail TEXT NOT NULL,
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
);

CREATE TABLE shop(
    shop_id BIGSERIAL PRIMARY KEY,
    map_id BIGINT NOT NULL REFERENCES maps(map_id),
    category_cd VARCHAR(6) NOT NULL REFERENCES codeT(cd),
    rating FLOAT
);


CREATE TABLE posts(
    post_id BIGSERIAL PRIMARY KEY,
    title varchar(100) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    modify_at TIMESTAMP NOT NULL,
    status_cd VARCHAR(6) NOT NULL REFERENCES codeT(cd),
    post_cd VARCHAR(6) NOT NULL REFERENCES codeT(cd),
    --user_id BIGINT NOT NULL REFERENCES users(user_id),--
    map_id BIGINT REFERENCES maps(map_id),
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