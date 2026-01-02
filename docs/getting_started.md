# 시작하기

### 사전 요구 사항 (Prerequisites)

이 앱은 **Ollama**를 모델 서버로 사용합니다. 최적의 성능을 위해 다음 모델들을 미리 다운로드해야 합니다:
```bash
ollama pull gemma3:27b        # Planner/Executor용 (고성능)
ollama pull gemma3:4b         # Router용 (빠른 반응속도)
ollama pull nomic-embed-text  # RAG 임베딩용 (필수)
```
> [!NOTE]
> 27B 모델 실행을 위해 최소 16GB 이상의 VRAM을 권장합니다. RAG 기능을 위해 `nomic-embed-text` 모델이 반드시 필요합니다.

### 설치 및 설정

1. **Backend 설정**
   ```bash
   cd backend
   python -m venv venv
   .\venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   ```

2. **?? ?? ??**
   `backend/.env.example`? ??? `backend/.env`? ?? ? ?? ?????.
   ```powershell
   copy backend\.env.example backend\.env
   ```
   ```text
   GOOGLE_API_KEY=your_google_ai_studio_api_key
   GOOGLE_CALENDAR_SCOPES=https://www.googleapis.com/auth/calendar
   OLLAMA_HOST=http://localhost:11434
   OLLAMA_MODEL=gemma3:27b
   OLLAMA_MODEL_PLANNER=gemma3:27b
   OLLAMA_KEEP_ALIVE=0
   ```

3. **Google OAuth ??**Google OAuth 설정**
   - [Google Cloud Console](https://console.cloud.google.com/)에서 **Google Calendar API**를 활성화합니다.
   - OAuth 2.0 클라이언트 ID를 생성하고 `credentials.json` 파일을 다운로드하여 `backend/` 폴더에 배치합니다.
   - 첫 실행 전 또는 인증 만료 시 아래 명령어로 인증을 수행합니다:
     ```bash
     python scripts/reauth.py
     ```

4. **Backend 실행**
   ```bash
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