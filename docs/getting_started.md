# 시작하기

### 사전 요구 사항 (Prerequisites)

이 앱은 **Ollama**를 모델 서버로 사용합니다. 최적의 성능을 위해 다음 모델들을 미리 다운로드해야 합니다:

### 설치 및 설정

0. **uv 설치 (Windows)**
   ```powershell
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

1. **Backend 설치**
   ```bash
      cd backend

      # 1) Python 3.12 설치 및 가상환경 생성
      uv venv venv --python 3.12
      .\venv\Scripts\activate

      # 2) 의존성 설치
      uv pip install -r requirements.txt
   ```

2. **환경변수 설정**
   `backend/.env.example`를 `backend/.env`로 복사하고 아래 환경변수를 설정합니다.
   ```powershell
   copy backend\.env.example backend\.env
   ```
   ```text
   GOOGLE_API_KEY=your_google_ai_studio_api_key
   GOOGLE_CALENDAR_SCOPES=https://www.googleapis.com/auth/calendar
   LLM_PROVIDER=ollama
   LLM_BASE_URL=http://localhost:11434
   LLM_MODEL=gpt-oss:20b
   LLM_MODEL_ROUTER=gpt-oss:20b
   LLM_MODEL_PLANNER=gpt-oss:20b
   LLM_MODEL_EXECUTOR=gpt-oss:20b
   LLM_KEEP_ALIVE=5m
   ```

   **프로파일별 환경 파일 사용 (권장)**
   - `backend/.env.ollama`, `backend/.env.lmstudio`에 각 환경값을 유지합니다.
   - 실행 시 프로파일을 선택해서 로드합니다.
   ```powershell
   cd backend
   .\scripts\run_backend.ps1 -Profile lmstudio -Reload
   ```

   **LLM Provider 전환 (선택)**
   ```text
   # Provider switch (ollama | lmstudio)
   LLM_PROVIDER=ollama
   LLM_BASE_URL=http://localhost:11434
   LLM_API_KEY=
   LLM_EMBEDDING_MODEL=nomic-embed-text
   LLM_MODEL=gpt-oss:20b
   LLM_MODEL_PLANNER=gpt-oss:20b
   LLM_MODEL_EXECUTOR=gpt-oss:20b
   ```
   LM Studio 사용 시:
   ```text
   LLM_PROVIDER=lmstudio
   LLM_BASE_URL=http://127.0.0.1:1234/v1
   LLM_API_KEY=lm-studio
   LLM_MODEL=zai-org/glm-4.6v-flash
   LLM_MODEL_PLANNER=zai-org/glm-4.6v-flash
   LLM_MODEL_EXECUTOR=zai-org/glm-4.6v-flash
   ```

3. **Google OAuth 설정**
   - [Google Cloud Console](https://console.cloud.google.com/)에서 **Google Calendar API**를 활성화합니다.
   - OAuth 2.0 클라이언트 ID를 생성하고 `credentials.json` 파일을 다운로드하여 `backend/` 폴더에 배치합니다.
   - 첫 실행 전 또는 인증 만료 시 아래 명령어로 인증을 수행합니다:
     ```bash
     python scripts/reauth.py
     ```

4. **Backend 실행**
   ```bash
   cd backend
   # 가상환경 활성화 후 실행
   .\venv\Scripts\activate
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

   # 또는 한 줄로 실행
   .\venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

5. **Flutter 앱 실행**
   ```bash
   cd client
   flutter pub get
   
   # 1. 사용할 수 있는 에뮬레이터 확인
   flutter emulators
   
   # 2. 에뮬레이터 실행 (예: Pixel_9)
   flutter emulators --launch Pixel_9
   
   # 3. 특정 디바이스로 앱 실행
   flutter run -d chrome
   flutter run -d windows
   flutter run -d emulator-5554  # 실행된 에뮬레이터 ID
   ```
