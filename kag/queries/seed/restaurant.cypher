MERGE (gangnam:Area {normalized_name: "강남"})
SET gangnam.area_id = "AREA001", gangnam.name = "강남", gangnam.level = 1;

MERGE (hongdae:Area {normalized_name: "홍대"})
SET hongdae.area_id = "AREA002", hongdae.name = "홍대", hongdae.level = 1;

MERGE (euljiro:Area {normalized_name: "을지로"})
SET euljiro.area_id = "AREA003", euljiro.name = "을지로", euljiro.level = 1;

MERGE (seongsu:Area {normalized_name: "성동"})
SET seongsu.area_id = "AREA004", seongsu.name = "성동", seongsu.level = 1;

MERGE (pangyo:Area {normalized_name: "판교"})
SET pangyo.area_id = "AREA005", pangyo.name = "판교", pangyo.level = 1;

MERGE (jongno:Area {normalized_name: "종로"})
SET jongno.area_id = "AREA006", jongno.name = "종로", jongno.level = 1;

MERGE (italian:Menu {normalized_name: "이탈리안"})
SET italian.menu_id = "MENU001", italian.name = "이탈리안", italian.menu_type = "category";

MERGE (pasta:Menu {normalized_name: "파스타"})
SET pasta.menu_id = "MENU002", pasta.name = "파스타", pasta.menu_type = "dish";

MERGE (sushi:Menu {normalized_name: "초밥"})
SET sushi.menu_id = "MENU003", sushi.name = "초밥", sushi.menu_type = "dish";

MERGE (meat:Menu {normalized_name: "고기"})
SET meat.menu_id = "MENU004", meat.name = "고기", meat.menu_type = "category";

MERGE (cafe:Menu {normalized_name: "카페"})
SET cafe.menu_id = "MENU005", cafe.name = "카페", cafe.menu_type = "category";

MERGE (chinese:Menu {normalized_name: "중국음식"})
SET chinese.menu_id = "MENU006", chinese.name = "중국음식", chinese.menu_type = "category";

MERGE (jajang:Menu {normalized_name: "짜장면"})
SET jajang.menu_id = "MENU007", jajang.name = "짜장면", jajang.menu_type = "dish";

MERGE (jjamppong:Menu {normalized_name: "짬뽕"})
SET jjamppong.menu_id = "MENU008", jjamppong.name = "짬뽕", jjamppong.menu_type = "dish";

MERGE (hansik:Menu {normalized_name: "한식"})
SET hansik.menu_id = "MENU009", hansik.name = "한식", hansik.menu_type = "category";

MERGE (doenjang:Menu {normalized_name: "된장찌개"})
SET doenjang.menu_id = "MENU010", doenjang.name = "된장찌개", doenjang.menu_type = "dish";

MERGE (health:Menu {normalized_name: "건강식"})
SET health.menu_id = "MENU011", health.name = "건강식", health.menu_type = "category";

MERGE (bunsik:Menu {normalized_name: "분식"})
SET bunsik.menu_id = "MENU012", bunsik.name = "분식", bunsik.menu_type = "category";

MERGE (noodle:Ingredient {normalized_name: "면"})
SET noodle.ingredient_id = "ING001", noodle.name = "면";

MERGE (soybean:Ingredient {normalized_name: "된장"})
SET soybean.ingredient_id = "ING002", soybean.name = "된장";

MERGE (pork:Ingredient {normalized_name: "고기"})
SET pork.ingredient_id = "ING003", pork.name = "고기";

MERGE (greasy:Ingredient {normalized_name: "기름진음식"})
SET greasy.ingredient_id = "ING004", greasy.name = "기름진음식";

MERGE (cucumber:Ingredient {normalized_name: "오이"})
SET cucumber.ingredient_id = "ING005", cucumber.name = "오이";

MERGE (mood:Tag {normalized_name: "분위기좋은"})
SET mood.tag_id = "TAG001", mood.name = "분위기좋은", mood.tag_type = "mood";

MERGE (cheap:Tag {normalized_name: "가성비"})
SET cheap.tag_id = "TAG002", cheap.name = "가성비", cheap.tag_type = "price_signal";

MERGE (gathering:Tag {normalized_name: "회식"})
SET gathering.tag_id = "TAG003", gathering.name = "회식", gathering.tag_type = "situation";

MERGE (quiet:Tag {normalized_name: "조용한"})
SET quiet.tag_id = "TAG004", quiet.name = "조용한", quiet.tag_type = "mood";

MERGE (noisy:Tag {normalized_name: "시끄러운"})
SET noisy.tag_id = "TAG005", noisy.name = "시끄러운", noisy.tag_type = "negative_signal";

MERGE (solo:Tag {normalized_name: "혼밥가능"})
SET solo.tag_id = "TAG006", solo.name = "혼밥가능", solo.tag_type = "situation";

MERGE (light:Tag {normalized_name: "담백한"})
SET light.tag_id = "TAG007", light.name = "담백한", light.tag_type = "taste";

MERGE (greasy_tag:Tag {normalized_name: "기름진음식"})
SET greasy_tag.tag_id = "TAG008", greasy_tag.name = "기름진음식", greasy_tag.tag_type = "negative_signal";

MERGE (healthy:Tag {normalized_name: "건강식"})
SET healthy.tag_id = "TAG009", healthy.name = "건강식", healthy.tag_type = "taste";

MERGE (night:Tag {normalized_name: "야간영업"})
SET night.tag_id = "TAG010", night.name = "야간영업", night.tag_type = "operation";

MERGE (clean:Tag {normalized_name: "깔끔한"})
SET clean.tag_id = "TAG011", clean.name = "깔끔한", clean.tag_type = "mood";

MERGE (delivery:Tag {normalized_name: "배달가능"})
SET delivery.tag_id = "TAG012", delivery.name = "배달가능", delivery.tag_type = "service";

MERGE (waiting:Tag {normalized_name: "웨이팅긴"})
SET waiting.tag_id = "TAG013", waiting.name = "웨이팅긴", waiting.tag_type = "negative_signal";

MERGE (adult:Tag {normalized_name: "어른동반적합"})
SET adult.tag_id = "TAG014", adult.name = "어른동반적합", adult.tag_type = "situation";

MERGE (r1:Restaurant {restaurant_id: "R001"})
SET r1.name = "강남파스타",
    r1.address = "서울 강남구",
    r1.rating = 4.5,
    r1.avg_price = 18000,
    r1.review_count = 320,
    r1.description = "강남에서 분위기 좋은 이탈리안 레스토랑",
    r1.is_active = true;

MERGE (r2:Restaurant {restaurant_id: "R002"})
SET r2.name = "홍대초밥",
    r2.address = "서울 마포구 홍대",
    r2.rating = 4.4,
    r2.avg_price = 15000,
    r2.review_count = 210,
    r2.description = "가성비 좋은 초밥집",
    r2.is_active = true;

MERGE (r3:Restaurant {restaurant_id: "R003"})
SET r3.name = "을지로고기집",
    r3.address = "서울 중구 을지로",
    r3.rating = 4.3,
    r3.avg_price = 22000,
    r3.review_count = 540,
    r3.description = "회식하기 좋은 고기집",
    r3.is_active = true;

MERGE (r4:Restaurant {restaurant_id: "R004"})
SET r4.name = "조용한카페",
    r4.address = "서울 성동구",
    r4.rating = 4.6,
    r4.avg_price = 9000,
    r4.review_count = 180,
    r4.description = "조용하고 깔끔한 카페",
    r4.is_active = true;

MERGE (r5:Restaurant {restaurant_id: "R005"})
SET r5.name = "홍콩반점",
    r5.address = "서울 강남구",
    r5.rating = 4.1,
    r5.avg_price = 9000,
    r5.review_count = 430,
    r5.description = "중국음식 전문점",
    r5.is_active = true;

MERGE (r6:Restaurant {restaurant_id: "R006"})
SET r6.name = "담백한고기집",
    r6.address = "경기 성남시 판교",
    r6.rating = 4.5,
    r6.avg_price = 19000,
    r6.review_count = 260,
    r6.description = "기름지지 않고 담백한 고기 메뉴 제공",
    r6.is_active = true;

MERGE (r7:Restaurant {restaurant_id: "R007"})
SET r7.name = "건강한한식",
    r7.address = "서울 종로구",
    r7.rating = 4.2,
    r7.avg_price = 12000,
    r7.review_count = 150,
    r7.description = "운동 후 먹기 좋은 건강식 한식집",
    r7.is_active = true;

MERGE (r8:Restaurant {restaurant_id: "R008"})
SET r8.name = "야간분식",
    r8.address = "서울 강남구",
    r8.rating = 4.0,
    r8.avg_price = 8000,
    r8.review_count = 390,
    r8.description = "늦은 밤에도 영업하는 분식집",
    r8.is_active = true;

MATCH (r:Restaurant {restaurant_id: "R001"}), (a:Area {normalized_name: "강남"})
MERGE (r)-[:LOCATED_IN]->(a);

MATCH (r:Restaurant {restaurant_id: "R002"}), (a:Area {normalized_name: "홍대"})
MERGE (r)-[:LOCATED_IN]->(a);

MATCH (r:Restaurant {restaurant_id: "R003"}), (a:Area {normalized_name: "을지로"})
MERGE (r)-[:LOCATED_IN]->(a);

MATCH (r:Restaurant {restaurant_id: "R004"}), (a:Area {normalized_name: "성동"})
MERGE (r)-[:LOCATED_IN]->(a);

MATCH (r:Restaurant {restaurant_id: "R005"}), (a:Area {normalized_name: "강남"})
MERGE (r)-[:LOCATED_IN]->(a);

MATCH (r:Restaurant {restaurant_id: "R006"}), (a:Area {normalized_name: "판교"})
MERGE (r)-[:LOCATED_IN]->(a);

MATCH (r:Restaurant {restaurant_id: "R007"}), (a:Area {normalized_name: "종로"})
MERGE (r)-[:LOCATED_IN]->(a);

MATCH (r:Restaurant {restaurant_id: "R008"}), (a:Area {normalized_name: "강남"})
MERGE (r)-[:LOCATED_IN]->(a);

MATCH (r:Restaurant {restaurant_id: "R001"}), (m:Menu {normalized_name: "이탈리안"})
MERGE (r)-[:SELLS]->(m);

MATCH (r:Restaurant {restaurant_id: "R001"}), (m:Menu {normalized_name: "파스타"})
MERGE (r)-[:SELLS]->(m);

MATCH (r:Restaurant {restaurant_id: "R002"}), (m:Menu {normalized_name: "초밥"})
MERGE (r)-[:SELLS]->(m);

MATCH (r:Restaurant {restaurant_id: "R003"}), (m:Menu {normalized_name: "고기"})
MERGE (r)-[:SELLS]->(m);

MATCH (r:Restaurant {restaurant_id: "R004"}), (m:Menu {normalized_name: "카페"})
MERGE (r)-[:SELLS]->(m);

MATCH (r:Restaurant {restaurant_id: "R005"}), (m:Menu {normalized_name: "중국음식"})
MERGE (r)-[:SELLS]->(m);

MATCH (r:Restaurant {restaurant_id: "R005"}), (m:Menu {normalized_name: "짜장면"})
MERGE (r)-[:SELLS]->(m);

MATCH (r:Restaurant {restaurant_id: "R005"}), (m:Menu {normalized_name: "짬뽕"})
MERGE (r)-[:SELLS]->(m);

MATCH (r:Restaurant {restaurant_id: "R006"}), (m:Menu {normalized_name: "고기"})
MERGE (r)-[:SELLS]->(m);

MATCH (r:Restaurant {restaurant_id: "R007"}), (m:Menu {normalized_name: "한식"})
MERGE (r)-[:SELLS]->(m);

MATCH (r:Restaurant {restaurant_id: "R007"}), (m:Menu {normalized_name: "된장찌개"})
MERGE (r)-[:SELLS]->(m);

MATCH (r:Restaurant {restaurant_id: "R007"}), (m:Menu {normalized_name: "건강식"})
MERGE (r)-[:SELLS]->(m);

MATCH (r:Restaurant {restaurant_id: "R008"}), (m:Menu {normalized_name: "분식"})
MERGE (r)-[:SELLS]->(m);

MATCH (r:Restaurant {restaurant_id: "R001"}), (t:Tag {normalized_name: "분위기좋은"})
MERGE (r)-[:HAS_TAG]->(t);

MATCH (r:Restaurant {restaurant_id: "R001"}), (t:Tag {normalized_name: "깔끔한"})
MERGE (r)-[:HAS_TAG]->(t);

MATCH (r:Restaurant {restaurant_id: "R002"}), (t:Tag {normalized_name: "가성비"})
MERGE (r)-[:HAS_TAG]->(t);

MATCH (r:Restaurant {restaurant_id: "R002"}), (t:Tag {normalized_name: "혼밥가능"})
MERGE (r)-[:HAS_TAG]->(t);

MATCH (r:Restaurant {restaurant_id: "R003"}), (t:Tag {normalized_name: "회식"})
MERGE (r)-[:HAS_TAG]->(t);

MATCH (r:Restaurant {restaurant_id: "R003"}), (t:Tag {normalized_name: "웨이팅긴"})
MERGE (r)-[:HAS_TAG]->(t);

MATCH (r:Restaurant {restaurant_id: "R004"}), (t:Tag {normalized_name: "조용한"})
MERGE (r)-[:HAS_TAG]->(t);

MATCH (r:Restaurant {restaurant_id: "R004"}), (t:Tag {normalized_name: "깔끔한"})
MERGE (r)-[:HAS_TAG]->(t);

MATCH (r:Restaurant {restaurant_id: "R004"}), (t:Tag {normalized_name: "어른동반적합"})
MERGE (r)-[:HAS_TAG]->(t);

MATCH (r:Restaurant {restaurant_id: "R005"}), (t:Tag {normalized_name: "가성비"})
MERGE (r)-[:HAS_TAG]->(t);

MATCH (r:Restaurant {restaurant_id: "R005"}), (t:Tag {normalized_name: "혼밥가능"})
MERGE (r)-[:HAS_TAG]->(t);

MATCH (r:Restaurant {restaurant_id: "R006"}), (t:Tag {normalized_name: "담백한"})
MERGE (r)-[:HAS_TAG]->(t);

MATCH (r:Restaurant {restaurant_id: "R006"}), (t:Tag {normalized_name: "회식"})
MERGE (r)-[:HAS_TAG]->(t);

MATCH (r:Restaurant {restaurant_id: "R007"}), (t:Tag {normalized_name: "건강식"})
MERGE (r)-[:HAS_TAG]->(t);

MATCH (r:Restaurant {restaurant_id: "R007"}), (t:Tag {normalized_name: "깔끔한"})
MERGE (r)-[:HAS_TAG]->(t);

MATCH (r:Restaurant {restaurant_id: "R008"}), (t:Tag {normalized_name: "야간영업"})
MERGE (r)-[:HAS_TAG]->(t);

MATCH (r:Restaurant {restaurant_id: "R008"}), (t:Tag {normalized_name: "배달가능"})
MERGE (r)-[:HAS_TAG]->(t);

MATCH (m:Menu {normalized_name: "파스타"}), (i:Ingredient {normalized_name: "면"})
MERGE (m)-[:CONTAINS]->(i);

MATCH (m:Menu {normalized_name: "짜장면"}), (i:Ingredient {normalized_name: "면"})
MERGE (m)-[:CONTAINS]->(i);

MATCH (m:Menu {normalized_name: "짬뽕"}), (i:Ingredient {normalized_name: "면"})
MERGE (m)-[:CONTAINS]->(i);

MATCH (m:Menu {normalized_name: "된장찌개"}), (i:Ingredient {normalized_name: "된장"})
MERGE (m)-[:CONTAINS]->(i);

MATCH (m:Menu {normalized_name: "고기"}), (i:Ingredient {normalized_name: "고기"})
MERGE (m)-[:CONTAINS]->(i);

MATCH (m:Menu {normalized_name: "초밥"}), (i:Ingredient {normalized_name: "오이"})
MERGE (m)-[:CONTAINS]->(i);
