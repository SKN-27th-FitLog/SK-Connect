MERGE (gangnam:Area {normalized_name: "강남"})
SET gangnam.area_id = "AREA001", gangnam.name = "강남", gangnam.level = 1;

MERGE (seongsu:Area {normalized_name: "성동"})
SET seongsu.area_id = "AREA002", seongsu.name = "성동", seongsu.level = 1;

MERGE (pangyo:Area {normalized_name: "판교"})
SET pangyo.area_id = "AREA003", pangyo.name = "판교", pangyo.level = 1;

MERGE (chinese:Menu {normalized_name: "중국음식"})
SET chinese.menu_id = "MENU001", chinese.name = "중국음식", chinese.menu_type = "category";

MERGE (jajang:Menu {normalized_name: "짜장면"})
SET jajang.menu_id = "MENU002", jajang.name = "짜장면", jajang.menu_type = "dish", jajang.price = 8000;

MERGE (jjamppong:Menu {normalized_name: "짬뽕"})
SET jjamppong.menu_id = "MENU003", jjamppong.name = "짬뽕", jjamppong.menu_type = "dish", jjamppong.price = 9000;

MERGE (cafe:Menu {normalized_name: "카페"})
SET cafe.menu_id = "MENU004", cafe.name = "카페", cafe.menu_type = "category";

MERGE (italian:Menu {normalized_name: "이탈리안"})
SET italian.menu_id = "MENU005", italian.name = "이탈리안", italian.menu_type = "category";

MERGE (meat:Menu {normalized_name: "고기"})
SET meat.menu_id = "MENU006", meat.name = "고기", meat.menu_type = "category";

MERGE (noodle:Ingredient {normalized_name: "면"})
SET noodle.ingredient_id = "ING001", noodle.name = "면";

MERGE (quiet:Tag {normalized_name: "조용한"})
SET quiet.tag_id = "TAG001", quiet.name = "조용한", quiet.tag_type = "mood";

MERGE (noisy:Tag {normalized_name: "시끄러운"})
SET noisy.tag_id = "TAG002", noisy.name = "시끄러운", noisy.tag_type = "negative_signal";

MERGE (mood:Tag {normalized_name: "분위기좋은"})
SET mood.tag_id = "TAG003", mood.name = "분위기좋은", mood.tag_type = "mood";

MERGE (clean:Tag {normalized_name: "깔끔한"})
SET clean.tag_id = "TAG004", clean.name = "깔끔한", clean.tag_type = "mood";

MERGE (hongkong:Restaurant {restaurant_id: "R005"})
SET hongkong.name = "홍콩반점",
    hongkong.address = "서울 강남구",
    hongkong.rating = 4.1,
    hongkong.avg_price = 12000,
    hongkong.description = "중국음식 식당이며 짜장면과 짬뽕처럼 면이 포함된 메뉴를 판매하는 식당",
    hongkong.is_active = true;

MERGE (gangnam_pasta:Restaurant {restaurant_id: "R001"})
SET gangnam_pasta.name = "강남파스타",
    gangnam_pasta.address = "서울 강남구",
    gangnam_pasta.rating = 4.5,
    gangnam_pasta.avg_price = 18000,
    gangnam_pasta.description = "강남의 분위기 좋은 이탈리안 식당",
    gangnam_pasta.is_active = true;

MERGE (quiet_cafe:Restaurant {restaurant_id: "R004"})
SET quiet_cafe.name = "조용한카페",
    quiet_cafe.address = "서울 성동구",
    quiet_cafe.rating = 4.6,
    quiet_cafe.avg_price = 9000,
    quiet_cafe.description = "조용하고 깔끔한 카페",
    quiet_cafe.is_active = true;

MERGE (plain_meat:Restaurant {restaurant_id: "R006"})
SET plain_meat.name = "담백한고기집",
    plain_meat.address = "경기 성남시 판교",
    plain_meat.rating = 4.4,
    plain_meat.avg_price = 25000,
    plain_meat.description = "판교 회식에 적합한 고기집",
    plain_meat.is_active = true;

MATCH (hongkong:Restaurant {restaurant_id: "R005"}), (gangnam:Area {normalized_name: "강남"})
MERGE (hongkong)-[:LOCATED_IN]->(gangnam);

MATCH (hongkong:Restaurant {restaurant_id: "R005"}), (chinese:Menu {normalized_name: "중국음식"})
MERGE (hongkong)-[:SELLS]->(chinese);

MATCH (hongkong:Restaurant {restaurant_id: "R005"}), (jajang:Menu {normalized_name: "짜장면"})
MERGE (hongkong)-[:SELLS]->(jajang);

MATCH (hongkong:Restaurant {restaurant_id: "R005"}), (jjamppong:Menu {normalized_name: "짬뽕"})
MERGE (hongkong)-[:SELLS]->(jjamppong);

MATCH (jajang:Menu {normalized_name: "짜장면"}), (noodle:Ingredient {normalized_name: "면"})
MERGE (jajang)-[:CONTAINS]->(noodle);

MATCH (jjamppong:Menu {normalized_name: "짬뽕"}), (noodle:Ingredient {normalized_name: "면"})
MERGE (jjamppong)-[:CONTAINS]->(noodle);

MATCH (gangnam_pasta:Restaurant {restaurant_id: "R001"}), (gangnam:Area {normalized_name: "강남"})
MERGE (gangnam_pasta)-[:LOCATED_IN]->(gangnam);

MATCH (gangnam_pasta:Restaurant {restaurant_id: "R001"}), (italian:Menu {normalized_name: "이탈리안"})
MERGE (gangnam_pasta)-[:SELLS]->(italian);

MATCH (gangnam_pasta:Restaurant {restaurant_id: "R001"}), (mood:Tag {normalized_name: "분위기좋은"})
MERGE (gangnam_pasta)-[:HAS_TAG]->(mood);

MATCH (gangnam_pasta:Restaurant {restaurant_id: "R001"}), (clean:Tag {normalized_name: "깔끔한"})
MERGE (gangnam_pasta)-[:HAS_TAG]->(clean);

MATCH (quiet_cafe:Restaurant {restaurant_id: "R004"}), (seongsu:Area {normalized_name: "성동"})
MERGE (quiet_cafe)-[:LOCATED_IN]->(seongsu);

MATCH (quiet_cafe:Restaurant {restaurant_id: "R004"}), (cafe:Menu {normalized_name: "카페"})
MERGE (quiet_cafe)-[:SELLS]->(cafe);

MATCH (quiet_cafe:Restaurant {restaurant_id: "R004"}), (quiet:Tag {normalized_name: "조용한"})
MERGE (quiet_cafe)-[:HAS_TAG]->(quiet);

MATCH (quiet_cafe:Restaurant {restaurant_id: "R004"}), (clean:Tag {normalized_name: "깔끔한"})
MERGE (quiet_cafe)-[:HAS_TAG]->(clean);

MATCH (plain_meat:Restaurant {restaurant_id: "R006"}), (pangyo:Area {normalized_name: "판교"})
MERGE (plain_meat)-[:LOCATED_IN]->(pangyo);

MATCH (plain_meat:Restaurant {restaurant_id: "R006"}), (meat:Menu {normalized_name: "고기"})
MERGE (plain_meat)-[:SELLS]->(meat);
