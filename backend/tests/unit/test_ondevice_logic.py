import os
import sys
from datetime import datetime, timezone, timedelta

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.agent.prompts import FunctionGemmaPromptBuilder
from app.agent.llm import get_local_llm
import json

def test_ondevice_router():
    print("\n--- Testing Local Router (270M) ---")
    llm = get_local_llm()
    if not llm:
        print("Local LLM not available.")
        return

    queries = [
        "오늘 일정 뭐 있어?",
        "다음 주 월요일 저녁 7시에 강남역에서 친구랑 저녁 약속 잡아줘"
    ]
    
    for query in queries:
        prompt = FunctionGemmaPromptBuilder.build_router_prompt(query)
        print(f"\nUser: {query}")
        response = llm.invoke(prompt)
        print(f"Assistant: {response}")

def test_ondevice_executor():
    print("\n--- Testing Local Executor (270M) ---")
    llm = get_local_llm()
    if not llm:
        print("Local LLM not available.")
        return

    # Scenario: Specific calendar registration
    intent = "내일 오후 4시에 [WS] Inc 캘린더에 회의 일정을 잡겠습니다."
    cal_context = "Available Calendars:\n- [WS] Inc. (ID: ws_inc_calendar_id)\n- primary (ID: primary)"
    time_str = "Current Time(Asia/Seoul): 2025-12-24 14:00:00 Wednesday"
    
    prompt = FunctionGemmaPromptBuilder.build_chat_prompt(intent, time_str=time_str, context=cal_context)
    print(f"\nIntent: {intent}")
    response = llm.invoke(prompt)
    print(f"Assistant: {response}")

if __name__ == "__main__":
    test_ondevice_router()
    test_ondevice_executor()
