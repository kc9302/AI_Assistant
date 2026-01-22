# [2026-01-16] Calendar Functionality Improvement

## 1. 📝 요약 (Summary)
구글 캘린더 연동 기능의 핵심적인 4가지 문제(날짜 인식, 캘린더 선택, 통합 조회, 스마트 삭제)를 해결하여 사용자 경험과 AI의 도구 호출 정확도를 대폭 개선했습니다.

## 2. 🚀 주요 변경 사항 (Key Changes)
- **Fix**: MemoryService `TypeError` 해결
  - `backend/app/services/memory.py`: `get_user_profile`, `update_user_profile` 메서드에 `thread_id` 인자 추가하여 LangGraph 노드 호출 시 발생하는 타입 에러 해결.
- **Refactor**: AI 비서 4대 핵심 역할 정립 및 프롬프트 고정
  - `backend/app/agent/graph.py`: `router_node`와 `planner` 프롬프트에 일반 챗, 일정 관리, RAG, 회의록 요약 4대 역할을 명시하여 모델의 정체성과 동작 범위를 명확히 함.
- **Fix**: 상대 날짜 인식 오류 해결
  - `backend/app/agent/graph.py`: `executor_node`에 다음 주 각 요일의 날짜를 계산하여 `DATE REFERENCE`에 주입하는 로직 추가. `planner` 프롬프트에 요일 산술 예제 추가.
- **Fix**: 캘린더 선택 및 매핑 Guardrail 추가
  - `backend/app/agent/graph.py`: 사용자 요청 메시지에서 캘린더 이름(예: '[WS] Inc.')을 감지하여 올바른 `calendar_id`로 강제 매핑하는 Guardrail 로직 구현.
- **Feat**: 통합 캘린더 조회 기능
  - `backend/app/agent/graph.py`: 일정 조회 시 `calendar_id`를 생략하도록 프롬프트 수정하여, 기본적으로 모든 관리 가능한 캘린더의 일정을 함께 보여주도록 개선.
- **Feat**: `thread_id` 기반 스마트 삭제 구현
  - `backend/app/agent/graph.py`: `router_node`와 `planner`가 `config`에서 `thread_id`를 정확히 추출하도록 수정.
  - `backend/app/services/context_manager.py`: 일정 생성 시 `thread_id`와 연계하여 DB에 저장.
  - `backend/app/agent/graph.py`: "방금 만든 거 삭제해줘" 요청 시 메모리에서 최근 ID를 조회하여 자동으로 삭제 도구를 실행하는 Guardrail 강화.

## 3. 🧠 기술적 맥락 (Context for AI)
- **구현 의도**: LLM이 복잡한 날짜 계산이나 특정 ID 기억을 완벽히 수행하기 어렵기 때문에, 백엔드 로직(Guardrail)이 대화 맥락(`thread_id`)과 현재 시간 정보를 바탕으로 부족한 정보를 보충하도록 설계함.
- **트레이드오프**: 모든 캘린더 조회를 기본값으로 설정하여 사용자 편의성을 높였으나, 캘린더가 매우 많은 사용자의 경우 응답 데이터가 커질 수 있음. 이를 위해 `max_results`를 적절히 유지함.
- **중요 변수/설정**: `thread_id`는 LangGraph의 `config["configurable"]["thread_id"]`에서 가져오며, SQLite 기반의 `context_v3.db`를 사용하여 세션 간 맥락을 유지함.

## 4. ✅ 남은 과제 (Next Steps)
- [ ] 현재 1회성 삭제만 지원하므로, 여러 이벤트를 한꺼번에 삭제하는 효율적인 배치 처리 로직 검토.
- [ ] 캘린더 조회 시 응답이 너무 길어질 경우를 대비한 요약 엔진(Summarizer) 성능 최적화.
