# API 명세 (Key Endpoints)

- `GET /status`: 서버 연결 및 모델 로드 상태 확인
  - `llm_provider`, `llm_base_url`, `llm_model`, `llm_connected`, `llm_details` 포함
- `POST /api/chat`: 대화 엔진 호출
  - `thread_id`: 대화 맥락 유지를 위한 고유 ID (생략 시 자동 생성)
- `POST /api/unload`: 리소스 절약을 위해 GPU 메모리에서 LLM 즉시 언로드
