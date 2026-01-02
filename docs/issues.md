# 오류 및 이슈 정리

## 환경 설정 관련
- **OLLAMA_HOST 누락**: `app/core/settings.py`에서 필수 값으로 로드되므로 `.env`에 설정하지 않으면 FastAPI가 시작되지 않는다.
- **Google 토큰 만료/손상**: `backend/token.json`이 만료되면 `app/core/google_auth.py`가 `invalid_grant`를 출력한다. `python backend/scripts/reauth.py`로 토큰을 재발급한다.
- **캘린더 Scope 미설정**: `.env`에 `GOOGLE_CALENDAR_SCOPES`가 비어 있으면 기본 스코프(`https://www.googleapis.com/auth/calendar`)만 적용된다. 추가 스코프가 필요하면 `.env`에 명시한다.

## 러닝타임/연동
- **Ollama 미가동**: `/status`에서 `ollama_connected`가 `false`이면 `OLLAMA_HOST`로 지정한 Ollama 서버가 꺼져 있거나 방화벽에 막힌 상태다. Ollama를 시작하고 Gemma3 모델을 로드한 뒤 다시 `/status`를 확인한다.
- **온디바이스 모델 자산(선택)**: 온디바이스 LLM을 쓰지 않는다면 `pubspec.yaml`의 `assets` 항목에서 모델 경로를 제거해 빌드 오류를 방지할 수 있다. 로컬 모델을 사용할 때는 지정한 GGUF 파일을 선언한 경로에 배치해야 한다.
- **백엔드 버전 불일치**: `verification/verify_and_test.py`는 `/status` 응답의 `version`이 `debug-1-check`일 때만 최신으로 판단한다. 다른 값이면 서버 재시작 또는 배포 버전 확인이 필요하다.

## 운영 팁
- **세션 스냅샷 위치**: `data/sessions/YYYY-MM-DD/`에 대화 기록이 저장된다. 디스크 사용량이 늘어나면 오래된 스냅샷을 정리한다.
- **장기 프로필 확인**: `data/user_profile.json`에 Facts와 대화 요약이 저장된다. 비정상 데이터가 쌓인 경우 백업 후 초기화하면 모델 답변 품질이 복구된다.
