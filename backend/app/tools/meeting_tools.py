from langchain_core.tools import tool
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import json
import logging
from typing import Optional, Dict, Any, List

from app.agent.llm import get_llm
from app.agent.prompts.meeting_prompts import MEETING_SUMMARY_SYSTEM_PROMPT, MEETING_SUMMARY_FEW_SHOT

logger = logging.getLogger(__name__)

class SummarizeMeetingNotesInput(BaseModel):
    meeting_notes: str = Field(description="요약할 회의록 원문")
    meeting_title: str = Field(default="", description="회의 제목 (선택)")
    meeting_date: str = Field(default="", description="회의 날짜 (YYYY-MM-DD, 선택)")

@tool
def summarize_meeting_notes(
    meeting_notes: str,
    meeting_title: str = "",
    meeting_date: str = ""
) -> str:
    """
    회의록 원문을 입력받아 핵심 내용을 요약하고, 참석자, 주요 안건, 결정 사항, 액션 아이템(일정 포함)을 추출합니다.
    """
    if not meeting_notes or len(meeting_notes.strip()) < 10:
        logger.warning(f"[MEETING_TOOL] Received empty or very short meeting_notes: '{meeting_notes}'")
        return json.dumps({
            "summary": "입력된 회의록 내용이 너무 적거나 없습니다. 회의록 전문을 입력해 주세요.",
            "action_items": []
        }, ensure_ascii=False)

    now = datetime.now()
    current_date = meeting_date or now.strftime("%Y-%m-%d")
    current_weekday = ["월", "화", "수", "목", "금", "토", "일"][now.weekday()]
    
    # Few-shot 예시의 날짜들을 동적으로 계산 (예시용)
    today_date = current_date
    next_monday = now + timedelta(days=(7 - now.weekday()))
    next_monday_date = next_monday.strftime("%Y-%m-%d")
    this_friday = now + timedelta(days=(4 - now.weekday()))
    this_friday_date = this_friday.strftime("%Y-%m-%d")

    system_prompt = MEETING_SUMMARY_SYSTEM_PROMPT.format(
        current_date=current_date,
        current_weekday=current_weekday
    )
    
    few_shot = MEETING_SUMMARY_FEW_SHOT.format(
        today_date=today_date,
        next_monday_date=next_monday_date,
        this_friday_date=this_friday_date
    )

    full_prompt = f"{system_prompt}\n\n{few_shot}\n\n입력: \"{meeting_notes}\"\n\n출력:"

    try:
        llm = get_llm(keep_alive="5m")
        response = llm.invoke(full_prompt)
        
        # JSON 추출
        content = response.content if hasattr(response, 'content') else str(response)
        
        # Simple JSON extraction (Manual JSON Parsing mentioned in dev history)
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "{" in content:
            start = content.find("{")
            end = content.rfind("}") + 1
            content = content[start:end]
        
        # Validate JSON
        result = json.loads(content)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"[MEETING_TOOL] 요약 중 오류 발생: {e}")
        return json.dumps({
            "error": f"회의록 요약 중 오류가 발생했습니다: {str(e)}",
            "summary": "요약 실패",
            "action_items": []
        }, ensure_ascii=False)
