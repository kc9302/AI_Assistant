---
name: travel-guide
description: 전문가 수준의 여행 일정 계획 및 로직 지원. 프로젝트 내의 여행 관련 지식 베이스(itinerary, logistics, restaurants)를 활용하여 최적의 경로와 장소를 추천합니다.
---

# Travel Guide Skill

이 스킬은 사용자가 여행 계획, 장소 추천, 또는 물류(교통 등) 관련 질문을 할 때 활성화됩니다.

## 스킬 사용 시점
- 사용자가 특정 지역(예: 일본, 도쿄 등)의 여행 일정을 물어볼 때
- 식당 추천이나 이동 수단에 대한 정보가 필요할 때
- `backend/knowledge/travel/` 디렉토리에 정의된 지식을 기반으로 응답해야 할 때

## 사용 가이드 및 규칙
1. **RAG 우선순위**: 항상 `backend/knowledge/travel/` 폴더 내의 마크다운 파일을 먼저 검색하십시오.
2. **구체성**: 단순히 장소를 나열하지 말고, `itinerary.md`에 정의된 타임라인을 준수하여 답변하십시오.
3. **일관성**: `logistics.md`에 있는 교통 정보를 바탕으로 현실적인 이동 시간을 고려하십시오.
4. **출처 명시**: 가능한 경우 프로젝트 내부 문서에서 참조했음을 부드럽게 언급하십시오.

## 관련 리소스
- `backend/knowledge/travel/itinerary.md`: 상세 일정
- `backend/knowledge/travel/restaurants.md`: 엄선된 맛집 리스트
- `backend/knowledge/travel/logistics.md`: 교통 및 예약 정보
