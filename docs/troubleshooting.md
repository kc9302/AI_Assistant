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

  - **A:** 시스템 사양에 따라 `LLM_MODEL_PLANNER`를 `llama3.1:8b`보다 가벼운 모델로 변경하여 테스트해 보세요.
- **Q: Ollama 서버를 구분하는 이유가 무엇인가요?**
  - **A:** 초기에는 Ollama를 통해 툴 사용 기능을 구현하려 했으나, Ollama 환경에서 `tool use` 관련하여 404 에러가 지속적으로 발생했습니다. 이 문제를 해결하기 위해 LM Studio 환경을 구축하여 툴 사용을 지원하게 되었습니다. 따라서 특정 툴 사용 모델은 LM Studio 서버를 통해 작동하도록 구분하고 있습니다.
