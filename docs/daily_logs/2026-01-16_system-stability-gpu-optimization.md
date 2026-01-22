# [2026-01-16] Engineering Log: UX Refinement & Deletion Stability

## 1. 📝 요약 (Summary)
사용자 피드백을 반영하여 캘린더 응답의 가독성을 높이고(원문 보존), 일정 생성 시의 답변을 단순화했습니다. 또한 "방금 만든 일정 삭제" 기능의 안정성을 위해 메모리 참조 및 세션 태그 검색 로직을 강화했습니다.

## 2. 🚀 주요 변경 사항 (Key Changes)
- **UI/UX**: 답변 포맷 단순화 및 데이터 무결성 보존
  - `backend/app/agent/graph.py`: 일정 생성 완료 시 "(Double-checked)"와 같은 기술적 문구를 제거하고 "[일정]을 [캘린더]에 추가했습니다" 형식으로 단순화.
  - `backend/app/agent/graph.py`: `list_events` 요약 시 대괄호(`[...]`) 및 접두사를 포함한 원본 제목을 변형 없이 그대로 출력하도록 강제.
- **Fix**: 일정 삭제 로직 안정화 및 자동화
  - `backend/app/agent/graph.py`: `executor_node`에서 삭제 요청 시 인자가 부족하면 로컬 `ContextManager`를 참조하여 최근 생성된 `event_id`를 자동 주입.
  - `backend/app/tools/calendar.py`: `delete_event` 도구에- **Refactor**: 대용량 회의록 처리 분할 (Chunking)
  - `backend/app/tools/meeting_tools.py`: 1,500자 단위 Chunking 도입으로 GPU 타임아웃 및 할루시네이션 방지.
- **Fix (Critical)**: 캘린더 등록 오류 및 날짜 계산 정밀화 (Expert Verified)
  - `backend/app/tools/calendar.py`: `create_event` 툴에 **중복 방지(Conflict Check)** 로직 + 'Bad Request' 방지를 위한 **Hotfix(Timezone correction)** 적용.
  - `backend/app/agent/graph.py`: **Forced Date Override** 구현. "다음 주 수요일"과 같은 패턴 감지 시, Python 코드가 LLM의 판단을 무시하고 수학적으로 정확한 날짜로 강제 변환.
  - `backend/app/agent/graph.py`: 리팩토링 중 발생한 NameError(`now_kst`) 서버 크래시 해결.

## 3. 🧠 기술적 맥락 (Context for AI)
- **Prompt Enforced Verbatim**: 사용자가 캘린더 툴의 리턴값을 그대로 보기를 원함에 따라, LLM의 "친절한 재편집" 성향을 억제하고 원본 텍스트를 `assistant_message`에 그대로 투사하도록 지시함.
- **State Capture**: `tool_with_logging` 노드에서 `create_event` 결과의 `eventId`를 `ContextManager`에 즉시 저장하여 세션 내 연속성을 확보함.
- **Hybrid Date Logic**: LLM의 유연함과 Python의 정확함을 결합. 일반적인 날짜는 LLM에게 맡기되, "Next Week" 키워드는 로직으로 강제하여 환각을 원천 차단함.
- **Safe Fail Pattern**: API 호출 실패(예: 중복 체크)가 메인 프로세스(일정 등록)를 차단하지 않도록 `try-except`로 감싸 경고 로그만 남기고 진행하도록 설계함.

## 4. ✅ 남은 과제 (Next Steps)
- [ ] `test_executor_duplicates.py` 및 `test_date_calculation.py` 정기 테스트 파이프라인 편입.
- [ ] `nvidia-smi`를 통한 멀티 GPU 부하 분산 실측 및 리포트.
