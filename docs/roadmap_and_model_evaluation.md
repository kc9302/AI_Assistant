# 진행 상황 및 로드맵

- ✅ **Phase 1-3**: 기본 인프라, 캘린더 연동, 하이브리드 라우팅 (완료)
- ✅ **Phase 4**: LangGraph 및 SQLite 기반 지능형 메모리 & 장기 기억 분석 시스템 (완료)
- ✅ **Phase 4.5**: ID 교정 가드레일 및 안정성 강화 (완료)
- ✅ **Phase 4.6**: 일자별 세션 관리 및 인증 유틸리티 최적화 (완료)
- ✅ **Phase 5**: 배포 자동화 및 보안 강화 (완료)
- ✅ **Phase 6**: 코드 품질 개선 및 린트 최적화 (완료)
- ✅ **Phase 7**: 모델 구성 업데이트 (완료)
  - Backend 모델을 llama3.1:8b로 변경 (Ollama 서버의 실제 사용 가능 모델 반영)
- ✅ **Phase 8**: 싱글 모델 아키텍처 전환 및 OSS 최적화 (완료)
  - `gpt-oss:20b` 단일 모델 기반 Planner/Executor 통합
  - OSS 모델 대응을 위한 Manual JSON Parsing 및 Few-Shot 프롬프팅 적용
  - 대화 문맥(Context) 유지력 검증 완료
- ✅ **Phase 10**: 의존성 관리 최적화 및 인덱싱 자동화 (완료)
  - `uv` 기반 패키지 관리 시스템 도입 및 가상환경 설정 가이드 고도화
  - `travel_index` 자동 동기화 엔진 구현 (Knowledge 변경 감지 및 자동 갱신)
- ✅ **Phase 11**: 지능형 프로필 구조 개편 및 맥락 가이드 수립 (완료)
  - `user_profile.json` 구조적 분리 (고정 정보 'user' vs 동적 정보 'facts')
  - 에이전트 인지 시스템 고도화 및 `ai_context_guide.md` 상세 명세 작성
- ✅ **Phase 12**: 회의록 요약 및 자동 일정 등록 (완료)
  - `summarize_meeting_notes` 도구 및 전용 추출 프롬프트 구현
  - 추출된 일정의 보관(State) 및 사용자 승인 후 일괄 등록 프로세스 구축
  - 통합 테스트(`test_meeting_summary.py`)를 통한 흐름 검증

**현재 버전**: 1.6.0 (Stable)  
**최근 업데이트**: 2026-01-16

---

## 모델 성능 평가 이력 (Model Evaluation History)

### Local Router (FunctionGemma-270M) 성능 평가 (2025-12-30)
초기 설계된 온디바이스 하이브리드 라우팅의 실효성을 검증하기 위해 벤치마크를 수행했습니다.

- **테스트 환경**: Local LlamaCpp (functiongemma-270m-it-q8_0.gguf)
- **평가 항목**: 의도 분류 (answer, simple, complex)
- **결과 요약**:
  - **정확도 (Accuracy)**: **14.3% (1/7)**
  - **주요 결함**: 자연어 의도 파악 오류, JSON 출력 형식 불완전, 복잡한 문장 해석 불가.
- **결정**: 로컬 모델의 낮은 신뢰도로 인해 사용자 경험을 해칠 수 있다고 판단, 온디바이스 라우팅 로직을 모두 제거하고 고성능 리모트 모델(Gemma3:27b -> llama3.1:8b -> gpt-oss:20b)로 단일화함.

### gpt-oss:20b 싱글 모델 성능 검증 (2026-01-07)
Ollama 서버의 공유 리소스인 20B 모델을 전체 에이전트 노드에 적용했습니다.

- **평가 항목**: 세션 문맥 유지(Context Persistence), 도구 호출(Tool Calling) 정확도
- **결과 요약**:
  - **파싱 안정성**: `with_structured_output` 미지원으로 인해 초기 실패했으나, Manual JSON Parsing 도입 후 해결.
  - **문맥 유지**: LangGraph Checkpointer를 통해 다회차 대화에서도 이전 대화 내용을 정확히 인지함.
  - **지연 시간**: 노드당 약 1.5s~4s 소요 (모델 크기 대비 양호).
  - **도구 호출**: 복잡한 의도에서 Default 도구(`list_events`)로 회귀하는 경향이 있어 Few-Shot 프롬프트로 보정 완료.