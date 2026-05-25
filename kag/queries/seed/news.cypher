MERGE (topic_ai:Topic {normalized_name: "ai"})
SET topic_ai.topic_id = "TOPIC001", topic_ai.name = "AI", topic_ai.topic_type = "technology_area";

MERGE (topic_cloud:Topic {normalized_name: "클라우드"})
SET topic_cloud.topic_id = "TOPIC002", topic_cloud.name = "클라우드", topic_cloud.topic_type = "industry";

MERGE (topic_security:Topic {normalized_name: "보안"})
SET topic_security.topic_id = "TOPIC003", topic_security.name = "보안", topic_security.topic_type = "security";

MERGE (topic_startup:Topic {normalized_name: "스타트업"})
SET topic_startup.topic_id = "TOPIC004", topic_startup.name = "스타트업", topic_startup.topic_type = "startup";

MERGE (topic_semiconductor:Topic {normalized_name: "반도체"})
SET topic_semiconductor.topic_id = "TOPIC005", topic_semiconductor.name = "반도체", topic_semiconductor.topic_type = "industry";

MERGE (topic_data:Topic {normalized_name: "데이터엔지니어링"})
SET topic_data.topic_id = "TOPIC006", topic_data.name = "데이터엔지니어링", topic_data.topic_type = "technology_area";

MERGE (topic_it:Topic {normalized_name: "it"})
SET topic_it.topic_id = "TOPIC007", topic_it.name = "IT", topic_it.topic_type = "industry";

MERGE (tech_gpt:Technology {normalized_name: "gpt"})
SET tech_gpt.technology_id = "TECH001", tech_gpt.name = "GPT", tech_gpt.technology_type = "ai_model";

MERGE (tech_genai:Technology {normalized_name: "생성형ai"})
SET tech_genai.technology_id = "TECH002", tech_genai.name = "생성형AI", tech_genai.technology_type = "ai_model";

MERGE (tech_llm:Technology {normalized_name: "llm"})
SET tech_llm.technology_id = "TECH003", tech_llm.name = "LLM", tech_llm.technology_type = "ai_model";

MERGE (tech_gpu:Technology {normalized_name: "gpu"})
SET tech_gpu.technology_id = "TECH004", tech_gpu.name = "GPU", tech_gpu.technology_type = "hardware";

MERGE (tech_ondevice:Technology {normalized_name: "온디바이스ai"})
SET tech_ondevice.technology_id = "TECH005", tech_ondevice.name = "온디바이스AI", tech_ondevice.technology_type = "ai_model";

MERGE (tech_cloud_infra:Technology {normalized_name: "클라우드인프라"})
SET tech_cloud_infra.technology_id = "TECH006", tech_cloud_infra.name = "클라우드인프라", tech_cloud_infra.technology_type = "platform";

MERGE (comp_openai:Company {normalized_name: "openai"})
SET comp_openai.company_id = "COMP001", comp_openai.name = "OpenAI", comp_openai.company_type = "ai_company", comp_openai.country = "US";

MERGE (comp_google:Company {normalized_name: "google"})
SET comp_google.company_id = "COMP002", comp_google.name = "Google", comp_google.company_type = "bigtech", comp_google.country = "US";

MERGE (comp_ms:Company {normalized_name: "microsoft"})
SET comp_ms.company_id = "COMP003", comp_ms.name = "Microsoft", comp_ms.company_type = "bigtech", comp_ms.country = "US";

MERGE (comp_samsung:Company {normalized_name: "삼성"})
SET comp_samsung.company_id = "COMP004", comp_samsung.name = "삼성", comp_samsung.company_type = "semiconductor", comp_samsung.country = "KR";

MERGE (comp_apple:Company {normalized_name: "애플"})
SET comp_apple.company_id = "COMP005", comp_apple.name = "애플", comp_apple.company_type = "bigtech", comp_apple.country = "US";

MERGE (evt_update:Event {normalized_name: "업데이트"})
SET evt_update.event_id = "EVENT001", evt_update.name = "업데이트", evt_update.event_type = "update";

MERGE (evt_invest:Event {normalized_name: "투자"})
SET evt_invest.event_id = "EVENT002", evt_invest.name = "투자", evt_invest.event_type = "investment";

MERGE (evt_reg:Event {normalized_name: "규제"})
SET evt_reg.event_id = "EVENT003", evt_reg.name = "규제", evt_reg.event_type = "regulation";

MERGE (evt_security:Event {normalized_name: "보안사고"})
SET evt_security.event_id = "EVENT004", evt_security.name = "보안사고", evt_security.event_type = "security_incident";

MERGE (evt_trend:Event {normalized_name: "트렌드"})
SET evt_trend.event_id = "EVENT005", evt_trend.name = "트렌드", evt_trend.event_type = "trend";

MERGE (evt_compete:Event {normalized_name: "기술경쟁"})
SET evt_compete.event_id = "EVENT006", evt_compete.name = "기술경쟁", evt_compete.event_type = "competition";

MERGE (evt_recovery:Event {normalized_name: "투자회복"})
SET evt_recovery.event_id = "EVENT007", evt_recovery.name = "투자회복", evt_recovery.event_type = "investment";

MERGE (aud_dev:Audience {normalized_name: "개발자"})
SET aud_dev.audience_id = "AUD001", aud_dev.name = "개발자", aud_dev.audience_type = "developer";

MERGE (aud_founder:Audience {normalized_name: "창업자"})
SET aud_founder.audience_id = "AUD002", aud_founder.name = "창업자", aud_founder.audience_type = "founder";

MERGE (aud_de:Audience {normalized_name: "데이터엔지니어"})
SET aud_de.audience_id = "AUD003", aud_de.name = "데이터엔지니어", aud_de.audience_type = "developer";

MERGE (a1:NewsArticle {article_id: "A001"})
SET a1.title = "OpenAI GPT 업데이트 공개",
    a1.summary = "OpenAI가 GPT 관련 기능 업데이트를 공개했다.",
    a1.published_at = date("2026-05-01"),
    a1.source = "TechDaily",
    a1.url = "https://example.com/news/a001",
    a1.importance_score = 0.91,
    a1.reliability_score = 0.88;

MERGE (a2:NewsArticle {article_id: "A002"})
SET a2.title = "클라우드 시장에서 AI 인프라 경쟁 심화",
    a2.summary = "주요 클라우드 기업들이 AI 인프라 투자를 확대하고 있다.",
    a2.published_at = date("2026-04-28"),
    a2.source = "ITNews",
    a2.url = "https://example.com/news/a002",
    a2.importance_score = 0.87,
    a2.reliability_score = 0.84;

MERGE (a3:NewsArticle {article_id: "A003"})
SET a3.title = "삼성과 애플의 온디바이스 AI 경쟁",
    a3.summary = "삼성과 애플이 모바일 AI 기술 경쟁을 강화하고 있다.",
    a3.published_at = date("2026-04-25"),
    a3.source = "DigitalTimes",
    a3.url = "https://example.com/news/a003",
    a3.importance_score = 0.85,
    a3.reliability_score = 0.82;

MERGE (a4:NewsArticle {article_id: "A004"})
SET a4.title = "생성형 AI 규제 논의 확대",
    a4.summary = "각국 정부가 생성형 AI 규제 프레임워크를 논의하고 있다.",
    a4.published_at = date("2026-04-20"),
    a4.source = "PolicyTech",
    a4.url = "https://example.com/news/a004",
    a4.importance_score = 0.89,
    a4.reliability_score = 0.86;

MERGE (a5:NewsArticle {article_id: "A005"})
SET a5.title = "보안 업계 대규모 데이터 유출 사고 대응",
    a5.summary = "보안 기업들이 최근 데이터 유출 사고에 대한 대응책을 발표했다.",
    a5.published_at = date("2026-04-18"),
    a5.source = "SecurityNews",
    a5.url = "https://example.com/news/a005",
    a5.importance_score = 0.88,
    a5.reliability_score = 0.83;

MERGE (a6:NewsArticle {article_id: "A006"})
SET a6.title = "판교 스타트업 투자 회복 조짐",
    a6.summary = "판교 지역 스타트업을 중심으로 투자 회복 신호가 나타나고 있다.",
    a6.published_at = date("2026-04-16"),
    a6.source = "StartupBrief",
    a6.url = "https://example.com/news/a006",
    a6.importance_score = 0.76,
    a6.reliability_score = 0.79;

MATCH (a:NewsArticle {article_id: "A001"}), (t:Topic {normalized_name: "ai"})
MERGE (a)-[:MENTIONS]->(t);

MATCH (a:NewsArticle {article_id: "A001"}), (t:Technology {normalized_name: "gpt"})
MERGE (a)-[:MENTIONS_TECH]->(t);

MATCH (a:NewsArticle {article_id: "A001"}), (t:Technology {normalized_name: "llm"})
MERGE (a)-[:MENTIONS_TECH]->(t);

MATCH (a:NewsArticle {article_id: "A001"}), (c:Company {normalized_name: "openai"})
MERGE (a)-[:MENTIONS_COMPANY]->(c);

MATCH (a:NewsArticle {article_id: "A001"}), (e:Event {normalized_name: "업데이트"})
MERGE (a)-[:DESCRIBES_EVENT]->(e);

MATCH (a:NewsArticle {article_id: "A002"}), (t:Topic {normalized_name: "클라우드"})
MERGE (a)-[:MENTIONS]->(t);

MATCH (a:NewsArticle {article_id: "A002"}), (t:Topic {normalized_name: "ai"})
MERGE (a)-[:MENTIONS]->(t);

MATCH (a:NewsArticle {article_id: "A002"}), (t:Technology {normalized_name: "클라우드인프라"})
MERGE (a)-[:MENTIONS_TECH]->(t);

MATCH (a:NewsArticle {article_id: "A002"}), (t:Technology {normalized_name: "gpu"})
MERGE (a)-[:MENTIONS_TECH]->(t);

MATCH (a:NewsArticle {article_id: "A002"}), (c:Company {normalized_name: "google"})
MERGE (a)-[:MENTIONS_COMPANY]->(c);

MATCH (a:NewsArticle {article_id: "A002"}), (c:Company {normalized_name: "microsoft"})
MERGE (a)-[:MENTIONS_COMPANY]->(c);

MATCH (a:NewsArticle {article_id: "A002"}), (e:Event {normalized_name: "투자"})
MERGE (a)-[:DESCRIBES_EVENT]->(e);

MATCH (a:NewsArticle {article_id: "A002"}), (e:Event {normalized_name: "트렌드"})
MERGE (a)-[:DESCRIBES_EVENT]->(e);

MATCH (a:NewsArticle {article_id: "A003"}), (t:Topic {normalized_name: "ai"})
MERGE (a)-[:MENTIONS]->(t);

MATCH (a:NewsArticle {article_id: "A003"}), (t:Technology {normalized_name: "온디바이스ai"})
MERGE (a)-[:MENTIONS_TECH]->(t);

MATCH (a:NewsArticle {article_id: "A003"}), (c:Company {normalized_name: "삼성"})
MERGE (a)-[:MENTIONS_COMPANY]->(c);

MATCH (a:NewsArticle {article_id: "A003"}), (c:Company {normalized_name: "애플"})
MERGE (a)-[:MENTIONS_COMPANY]->(c);

MATCH (a:NewsArticle {article_id: "A003"}), (e:Event {normalized_name: "기술경쟁"})
MERGE (a)-[:DESCRIBES_EVENT]->(e);

MATCH (a:NewsArticle {article_id: "A004"}), (t:Topic {normalized_name: "ai"})
MERGE (a)-[:MENTIONS]->(t);

MATCH (a:NewsArticle {article_id: "A004"}), (t:Technology {normalized_name: "생성형ai"})
MERGE (a)-[:MENTIONS_TECH]->(t);

MATCH (a:NewsArticle {article_id: "A004"}), (e:Event {normalized_name: "규제"})
MERGE (a)-[:DESCRIBES_EVENT]->(e);

MATCH (a:NewsArticle {article_id: "A005"}), (t:Topic {normalized_name: "보안"})
MERGE (a)-[:MENTIONS]->(t);

MATCH (a:NewsArticle {article_id: "A005"}), (e:Event {normalized_name: "보안사고"})
MERGE (a)-[:DESCRIBES_EVENT]->(e);

MATCH (a:NewsArticle {article_id: "A006"}), (t:Topic {normalized_name: "스타트업"})
MERGE (a)-[:MENTIONS]->(t);

MATCH (a:NewsArticle {article_id: "A006"}), (e:Event {normalized_name: "투자회복"})
MERGE (a)-[:DESCRIBES_EVENT]->(e);
