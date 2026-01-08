# 문제 해결 (Troubleshooting)

- **Q: "Google Token is invalid (invalid_grant)" 오류가 발생합니다.**
  - **A:** 보안 정책이나 만료로 인해 토큰이 무효화된 상태입니다. `backend` 폴더에서 `python scripts/reauth.py`를 실행하여 다시 로그인하세요.
- **Q: 8000 포트가 이미 사용 중이라는 오류(`OSError: [WinError 10048]`)가 발생합니다.**
  - **A:** 기존 서버 프로세스가 종료되지 않은 경우입니다. 아래 명령어로 해당 포트를 점유 중인 프로세스를 강제 종료하세요:
    ```powershell
    # Windows (PowerShell)
    Stop-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess -Force
    
    # Windows (CMD)
    Get-NetTCPConnection -LocalPort 8000 | ForEach-Object {Stop-Process -Id $_.OwningProcess -Force}

    ```
- **Q: 응답 속도가 너무 느립니다.**
  - **A:** 
    1. `gpt-oss:20b`와 같은 대형 모델은 추론에 시간이 소요됩니다. 시스템 사양에 따라 `LLM_MODEL`을 `llama3.1:8b`로 변경하면 속도가 향상됩니다.
    2. **[권장]** 에이전트의 각 단계(Router, Planner 등)마다 모델을 새로 로드하느라 느려지는 경우, `.env` 파일의 `LLM_KEEP_ALIVE`를 `5m` (5분) 정도로 설정하면 모델이 메모리에 상주하여 연속적인 요청에 대해 수 초 이내로 빠르게 응답합니다.
- **Q: "오사카 비행기" 질문에 정보를 찾을 수 없다고 답변합니다.**
  - **A:** 여행 정보 색인(Index)이 생성되지 않았거나 최신화되지 않은 경우입니다. 백엔드 폴더에서 다음 명령어를 실행하여 지식 베이스를 다시 인덱싱하세요:
    ```powershell
    cd backend
    $env:PYTHONPATH="."
    python scripts/index_travel.py
    ```
- **Q: "Invalid JSON output" 또는 "OUTPUT_PARSING_FAILURE" 오류가 발생합니다.**
  - **A:** 사용 중인 모델이 구조화된 출력(Structured Output) 형식을 엄격히 지키지 못하는 경우입니다. 백엔드는 현재 `extract_json` 기능을 통해 이를 보정하고 있으며, **v1.3.1-fix부터는 빈 응답을 안전하게 처리하여 서버 크래시를 방지**합니다. 사용자에게는 "죄송합니다. 일시적인 문제가 발생했습니다. 잠시 후 다시 시도해 주세요."라는 친절한 메시지가 표시되며, 기술적인 오류 내용은 서버 로그에만 기록됩니다. 현상이 지속될 경우 `Prompt`에 더 명확한 지시를 주거나 모델을 `gpt-oss:20b`급 이상으로 업그레이드하는 것을 권장합니다.
- **Q: Ollama와 LM Studio 중 무엇을 사용해야 하나요?**
  - **A:** 현재 시스템은 **Ollama**를 통한 단일 모델(`gpt-oss:20b`) 구성에 최적화되어 있습니다. 기존의 LM Studio 분리 방식은 툴 호출(Tool Call) 실패 문제를 해결하기 위함이었으나, 현재는 수동 파싱(Manual Parsing) 로직 도입으로 Ollama 단일 환경에서도 안정적으로 툴 호출이 가능합니다. 가능하면 Ollama 사용을 권장합니다.
