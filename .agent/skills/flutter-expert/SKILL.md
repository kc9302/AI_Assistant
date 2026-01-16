---
name: flutter-expert
description: Flutter 및 Dart를 사용한 크로스 플랫폼 클라이언트 개발 전문가입니다. Clean Architecture, 상태 관리, UI/UX 최적화를 담당합니다.
---

# Flutter Expert Skill

Flutter 클라이언트 애플리케이션(`client/`)의 설계, 구현, 유지보수를 위한 지침입니다.

## 스킬 사용 시점
- Flutter UI 위젯 구현 및 수정 시
- 상태 관리(Provider/Riverpod 등) 로직 설계 시
- API 연동 및 데이터 모델링(`client/lib/data`, `client/lib/domain`) 작업 시
- 성능 최적화 및 플랫폼 별(Android/iOS) 이슈 해결 시

## 개발 가이드 및 규칙

### 1. 아키텍처 (Clean Architecture)
- **Presentation Layer**: UI 위젯(`pages`, `widgets`)과 상태 관리(`providers`)를 담당합니다. 비즈니스 로직을 최소화하십시오.
- **Domain Layer**: 엔티티(`entities`)와 유스케이스, 리포지토리 인터페이스(`repositories`)를 정의합니다. 외부 라이브러리에 의존하지 않는 순수 Dart 코드로 작성하십시오.
- **Data Layer**: API 통신, 로컬 DB 접근 등 실제 데이터 처리를 담당하며(`datasources`), Domain의 리포지토리 인터페이스를 구현합니다(`repositories`).

### 2. 상태 관리
- 프로젝트의 기존 상태 관리 패턴(Provider 또는 Riverpod 등)을 엄격히 준수하십시오.
- UI와 상태 로직을 분리하여 테스트 가능성을 높이십시오.

### 3. UI/UX 및 스타일
- Material Design 가이드를 기본으로 하되, 커스텀 디자인 요구사항을 반영하십시오.
- 위젯을 작게 분리하여 재사용성을 높이십시오.
- 반응형 레이아웃을 고려하여 다양한 화면 크기에 대응하십시오.

### 4. 비동기 처리 및 에러 핸들링
- `Future`, `Stream`을 적절히 사용하여 비동기 작업을 처리하십시오.
- 사용자에게 친절한 에러 메시지를 표시하고, 적절한 로딩 상태를 구현하십시오.

## 관련 리소스
- `client/pubspec.yaml`: 의존성 관리
- `client/lib/core`: 공통 유틸리티 및 상수
