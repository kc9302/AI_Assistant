# 개발 및 테스트

### 백엔드 테스트 실행 가이드

다양한 시나리오를 검증하기 위해 분리된 통합 테스트를 지원합니다:

```powershell
cd backend
# 1. 자연어 프롬프트 시나리오 (기본 응답 기능)
python tests\integration\run_llm_natural_language_prompt_scenarios.py

# 2. 지능형 메모리 시나리오 (이전 대화 기억 및 지칭어 처리)
python tests\integration\run_llm_memory_scenarios.py

# 3. 캘린더 전체 시나리오 (조회/생성/삭제 통합)
python tests\integration\run_calendar_scenarios.py

# 4. 전체 단위 테스트
pytest tests\unit\ 
```

## ?? ?? ??

- ??: `backend/log/app.log`
- ?? ??: `rg -n "YYYY-MM-DD" backend/log/app.log`
- ?? ??: `rg -n "ERROR" backend/log/app.log`
- ?? ??? ??? ??: `rg -n "YYYY-MM-DD" backend/log/app.log | rg "ERROR"`
- ?? ? ??/?? ??? ??? (?? ???? ?? ?? ??).

