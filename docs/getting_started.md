# 시작하기

### 사전 요구 사항 (Prerequisites)

이 앱은 **Ollama**를 모델 서버로 사용합니다. 최적의 성능을 위해 다음 모델들을 미리 다운로드해야 합니다:

### 설치 및 설정

0. **Flutter SDK 설치**
   
   Flutter는 별도로 설치해야 합니다. 다음 중 한 가지 방법을 선택하세요:
   
   **방법 1: winget 사용 (권장, Windows 11/10+)**
   ```powershell
   # Flutter SDK 설치
   winget install --id 9NKSQGP7F2NH
   ```
   
   **방법 2: Chocolatey 사용**
   ```powershell
   # Chocolatey가 설치되어 있다면
   choco install flutter
   ```
   
   **방법 3: 수동 설치**
   - [Flutter 공식 다운로드 페이지](https://docs.flutter.dev/get-started/install/windows)에서 SDK 다운로드
   - 압축 해제 후 원하는 위치에 배치 (예: `C:\src\flutter`)
   - 시스템 환경 변수 PATH에 `flutter\bin` 경로 추가
   
   **설치 확인:**
   ```powershell
   # 새 PowerShell 창을 열어서 실행
   flutter doctor
   ```
   
   > **중요**: 
   > - Flutter 설치 후 **새 터미널/PowerShell 창**을 열어야 PATH가 적용됩니다.
   > - `flutter doctor` 실행 후 Android toolchain, Chrome 등 추가 구성이 필요할 수 있습니다.
   > - `flutter` 명령어를 찾을 수 없다면 시스템을 재부팅하거나 수동으로 PATH를 확인하세요.

1. **uv 설치 (Windows)**
   ```powershell
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

2. **Backend 설치**
   ```powershell
   # 1) 의존성 설치 및 가상환경 동기화 (루트 디렉토리에서 실행)
   # .venv 가상환경이 없으면 자동으로 생성됩니다.
   uv sync

   # 2) 가상환경 활성화
   # Windows (Powershell)
   .venv\Scripts\activate
   # macOS/Linux
   source .venv/bin/activate
   ```

3. **환경변수 설정**
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

4. **Google OAuth 설정**
   - [Google Cloud Console](https://console.cloud.google.com/)에서 **Google Calendar API**를 활성화합니다.
   - OAuth 2.0 클라이언트 ID를 생성하고 `credentials.json` 파일을 다운로드하여 `backend/` 폴더에 배치합니다.
   - 첫 실행 전 또는 인증 만료 시 아래 명령어로 인증을 수행합니다:
     ```bash
     uv run python scripts/reauth.py
     ```
     *(브라우저 실행이 불가능한 환경에서는 콘솔에 인증 코드를 입력하는 방식으로 자동 전환됩니다.)*

5. **Backend 실행**
   ```powershell
   cd backend
   # 가상환경 활성화 후 실행 (루트의 .venv 사용)
   # ..\.venv\Scripts\activate
   
   # 또는 uv run을 사용하여 자동으로 가상환경 적용 및 실행
   uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

6. **Flutter 앱 실행**
   ```powershell
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
