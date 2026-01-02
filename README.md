# AI 개인비서 Flutter 앱

FunctionGemma 기반의 LangGraph 에이전트와 Flutter 클라이언트로 구성된 개인 비서 서비스입니다. 캘린더 관리, 여행 RAG, 온디바이스/서버 하이브리드 추론을 제공합니다.

## 빠른 시작
- 백엔드/플러터 실행 및 스크립트 사용법은 [docs/runbook.md](docs/runbook.md)를 참고하세요.
- 환경/연동 이슈는 [docs/issues.md](docs/issues.md)에서 확인하세요.

## 주요 기능 요약
- LangGraph 기반 대화형 에이전트 (Ollama Gemma3, 선택적 온디바이스 LLM)
- Google 캘린더 통합(조회/생성/삭제) 및 Guardrails 적용
- 하이브리드 메모리: 체크포인트, 세션 스냅샷, 장기 사용자 프로필
- 오사카 여행 RAG: `backend/knowledge/travel/*.md`를 FAISS로 검색
- 다국어 응답 및 Markdown UI 렌더링(Flutter)

## 프로젝트 구조
```
├── backend/            # FastAPI + LangGraph 에이전트
│   ├── app/            # 에이전트, 서비스, 툴 로직
│   ├── knowledge/      # 여행 RAG Markdown
│   ├── scripts/        # 인덱싱/인증 스크립트
│   └── verification/   # 상태/채팅 확인 스크립트
├── client/             # Flutter 프런트엔드
│   └── lib/            # UI, Provider, 데이터 계층
└── data/               # 세션 스냅샷 및 프로필 저장
```

## 추가 문서
- 상세 아키텍처/기능: [docs/overview.md](docs/overview.md)
- 실행/운영 가이드: [docs/runbook.md](docs/runbook.md)
- 오류 및 이슈 정리: [docs/issues.md](docs/issues.md)
- 테스트용 질문 모음: [docs/test-questions.md](docs/test-questions.md)
