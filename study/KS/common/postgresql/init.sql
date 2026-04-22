-- ============================================================================
-- LangGraph 사용자 정의 체크포인트 테이블 (민감정보 자동 암호화)
-- ============================================================================
-- 이 테이블은 LLM이 자동으로 민감정보를 판단하여 
-- 암호화된 컬럼과 평문 컬럼에 선택적으로 저장합니다.
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_chat_history (
    id SERIAL PRIMARY KEY,
    thread_id TEXT NOT NULL,
    checkpoint_id TEXT NOT NULL,
    parent_checkpoint_id TEXT,
    is_encrypted BOOLEAN NOT NULL DEFAULT TRUE,  -- 암호화 여부 플래그
    encrypted_checkpoint_data BYTEA,             -- 암호화된 데이터 저장 (민감정보)
    checkpoint_data TEXT,                        -- 평문 데이터 저장 (일반 대화)
    metadata_json JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(thread_id, checkpoint_id)
);

-- 인덱스 생성 (조회 성능 향상)
CREATE INDEX IF NOT EXISTS idx_user_chat_history_thread_id 
    ON user_chat_history(thread_id);
CREATE INDEX IF NOT EXISTS idx_user_chat_history_created_at 
    ON user_chat_history(created_at DESC);

-- 테이블 주석
COMMENT ON TABLE user_chat_history IS 'LangGraph 저장용 사용자 대화 체크포인트 테이블 (민감정보 자동 암호화)';

-- 컬럼 주석
COMMENT ON COLUMN user_chat_history.id IS '고유 식별자 (자동 증가)';
COMMENT ON COLUMN user_chat_history.thread_id IS '대화 세션을 구분하는 스레드 ID';
COMMENT ON COLUMN user_chat_history.checkpoint_id IS '체크포인트의 고유 ID (UUID)';
COMMENT ON COLUMN user_chat_history.parent_checkpoint_id IS '이전 체크포인트 ID (대화 히스토리 추적용)';
COMMENT ON COLUMN user_chat_history.is_encrypted IS '암호화 여부 (TRUE: 민감정보 있음, FALSE: 일반 대화)';
COMMENT ON COLUMN user_chat_history.encrypted_checkpoint_data IS '암호화된 체크포인트 데이터 (BYTEA) - 민감정보 포함 시 사용';
COMMENT ON COLUMN user_chat_history.checkpoint_data IS '평문 체크포인트 데이터 (TEXT) - 일반 대화 시 사용';
COMMENT ON COLUMN user_chat_history.metadata_json IS '추가 메타데이터 (JSONB 형식)';
COMMENT ON COLUMN user_chat_history.created_at IS '레코드 생성 시간';
