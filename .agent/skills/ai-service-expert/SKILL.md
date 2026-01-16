---
name: ai-service-expert
description: LLM, RAG, 에이전트 오케스트레이션을 활용한 AI 서비스 개발 전문가입니다. LangGraph 기반의 백엔드 로직과 AI 기능을 구현합니다.
---

# AI Service Expert Skill

FastAPI 백엔드(`backend/`)와 LangGraph를 활용한 고지능 AI 에이전트 서비스 개발을 위한 지침입니다.

## 스킬 사용 시점
- LangGraph 그래프 설계 및 노드/엣지 구현 시 (`backend/app/agent/graph.py`)
- RAG(Retrieval-Augmented Generation) 시스템 구축 및 최적화 시
- 프롬프트 엔지니어링 및 LLM 응답 품질 개선 시
- 새로운 도구(Tools) 개발 및 에이전트 연동 시

## 개발 가이드 및 규칙

### 1. 에이전트 설계 (LangGraph)
- **State 관리**: `AgentState`를 명확히 정의하고, 각 노드 간의 상태 전이를 추적 가능하게 설계하십시오.
- **모듈화**: 복잡한 로직은 별도의 노드나 서브그래프로 분리하여 관리하십시오.
- **조건부 엣지**: 라우팅 로직을 명확히 하여 에이전트의 실행 흐름을 제어하십시오.

### 2. RAG 및 지식 베이스
- `backend/knowledge/` 내의 문서를 효과적으로 청킹(Chunking)하고 임베딩하십시오.
- 사용자 질문의 의도에 맞는 적절한 검색 전략(Hybrid Search 등)을 선택하십시오.
- 검색된 문맥(Context)을 프롬프트에 효과적으로 주입하여 할루시네이션을 방지하십시오.

### 3. LLM 연동 및 프롬프트
- 모델의 특성(Context Window, 추론 능력 등)을 고려하여 적절한 모델을 선택하십시오.
- 시스템 프롬프트에 페르소나와 제약 조건을 명확히 명시하십시오.
- 구조화된 출력(JSON 등)이 필요한 경우, 명시적인 스키마를 제공하거나 파싱 로직을 강화하십시오.

### 4. 성능 및 안정성
- API 호출 실패에 대한 재시도(Retry) 로직과 폴백(Fallback) 메커니즘을 구현하십시오.
- 스트리밍 응답을 지원하여 사용자 경험(Latency 감소)을 개선하십시오.

## 관련 리소스
- `backend/app/agent/`: 에이전트 코어 로직
- `backend/app/llm/`: LLM 서비스 및 핸들러
- `backend/app/tools/`: 에이전트 사용 도구
