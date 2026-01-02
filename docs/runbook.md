# 실행 및 운영 가이드

## 요구사항
- Python 3.11 이상
- Flutter 3.9+ (Dart ^3.9.2)
- Ollama에 Gemma3 모델 배포 (`settings.OLLAMA_MODEL` 기본값: `gemma3:27b`)
- Google Calendar 자격 증명: `backend/credentials.json`과 `backend/token.json`

## 백엔드 (FastAPI)

1. 의존성 설치
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. 환경 변수(.env) 설정 예시
   ```env
   OLLAMA_HOST=http://localhost:11434
   OLLAMA_MODEL=gemma3:27b
   OLLAMA_MODEL_PLANNER=gemma3:27b
   OLLAMA_KEEP_ALIVE=0
   GOOGLE_API_KEY=<optional-if-used>
   GOOGLE_CALENDAR_SCOPES=https://www.googleapis.com/auth/calendar
   ```

3. 서버 실행
   ```bash
   cd backend
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

4. 상태/기능 확인
   ```bash
   cd backend
   python verification/verify_and_test.py
   ```
   - `/status`가 `version: debug-1-check`를 반환해야 최신 코드 기준임.
   - `/api/chat`는 `test_payload.json` 형식의 입력을 기대한다.

5. RAG 인덱스 업데이트 (여행 지식 수정 시)
   ```bash
   cd backend
   PYTHONPATH=. python scripts/index_travel.py
   ```

## 클라이언트 (Flutter)

1. 의존성 설치
   ```bash
   cd client
   flutter pub get
   ```

2. 온디바이스 LLM (선택 사항)
   - 기본 템플릿은 `pubspec.yaml`의 `assets` 섹션에 온디바이스 모델 경로를 지정해 둡니다. 로컬 모델을 쓰지 않는다면 해당 엔트리를 제거하거나 원하는 GGUF 파일 경로로 교체하세요.
   - 로컬 모델을 사용할 경우, 지정한 GGUF 파일을 `client/assets/` 등 선언한 경로에 배치해야 합니다.

3. 백엔드 URL 설정
   - 기본값: 에뮬레이터(Android) `http://10.0.2.2:8000`, 데스크톱/웹 `http://localhost:8000` (`SettingsProvider`에서 로드).
   - 앱 실행 후 설정 화면에서 URL을 변경할 수 있다.

4. 앱 실행
   ```bash
   cd client
   flutter run -d <device-id>
   ```

## 유용한 스크립트 및 엔드포인트
- 모델 언로드: `POST /api/unload` (keep_alive=0으로 강제 언로드)
- Google 인증 갱신: `python backend/scripts/reauth.py`
- 상태 확인: `GET /status`에서 Ollama 연결 및 Google API 설정 여부 확인
