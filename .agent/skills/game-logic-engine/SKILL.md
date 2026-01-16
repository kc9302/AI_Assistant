---
name: game-logic-engine
description: 물고기 스킬 시스템 및 체스 로직 등 복잡한 게임 메커니즘을 분석하고 시뮬레이션합니다. 턴제 전투 로직 및 버프/디버프 계산을 지원합니다.
---

# Game Logic Engine Skill

게임 엔진 수준의 복잡한 상태 값과 로직을 해석합니다.

## 스킬 사용 시점
- `FishSkillType`, `FishBuff` 등 게임 관련 열거형 데이터에 대한 질문이 있을 때
- `Skill` 구조체(UCI ELO 기반 레벨 계산 등)의 동작 방식을 설명해야 할 때
- 턴 종료 시의 `clear_skill`, `clear_hit` 로직을 시뮬레이션할 때

## 사용 가이드 및 규칙
1. **버프 계산**: `SWELL`, `HEAL`, `SHIELD` 등 각 버프의 비트마스크(Bitmask) 값을 정확히 해석하십시오.
2. **레벨링 로직**: ELO 점수를 기반으로 한 `std::pow((uci_elo - 1346.6) / 143.4, 1 / 0.806)` 수식을 이해하고, 결과값이 0~20 사이로 제한됨을 인지하십시오.
3. **상태 초기화**: `clear_skill()` 호출 시 `is_skill`은 false가 되고, 타겟 수는 0으로 초기화됨을 보장하십시오.
4. **정확성**: 체스(CastlingRights, PieceType) 관련 로직은 표준 규칙을 따르되, 코드에 정의된 비트 연산 방식을 준수하십시오.

## 주요 데이터
- `FishBuff`: SWELL(1), HEAL(2), SHIELD(4), LIFEONHIT(8), DEFLECT(16)
- `CastlingRights`: 킹사이드/퀸사이드 캐슬링 권한 비트 연산
