from langchain_core.tools import tool
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import json
import logging
import re
from typing import Optional, Dict, Any, List

import dateparser

from app.agent.llm import get_llm
from app.agent.prompts.meeting_prompts import MEETING_SUMMARY_SYSTEM_PROMPT, MEETING_SUMMARY_FEW_SHOT
from app.core.datetime_utils import now_kst
from app.core.utils import extract_json

logger = logging.getLogger(__name__)

_TIME_HINT_RE = re.compile(r"(\d{1,2}\s*시|\d{1,2}:\d{2}|오전|오후|am|pm)", re.IGNORECASE)
_DATE_PATTERNS = [
    re.compile(r"(다음\s*주\s*(월|화|수|목|금|토|일)요일)"),
    re.compile(r"(이번\s*주\s*(월|화|수|목|금|토|일)요일)"),
    re.compile(r"(다음\s*달\s*\d{1,2}일)"),
    re.compile(r"(\d{1,2}\s*월\s*\d{1,2}\s*일)"),
    re.compile(r"(오늘|내일|모레)"),
]
_TIME_PATTERNS = [
    re.compile(r"(오전\s*\d{1,2}시(\s*\d{1,2}분)?)"),
    re.compile(r"(오후\s*\d{1,2}시(\s*\d{1,2}분)?)"),
    re.compile(r"(\d{1,2}:\d{2})"),
    re.compile(r"(\d{1,2}시(\s*\d{1,2}분)?)"),
]


def _parse_iso_datetime(value: str, tzinfo) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None and tzinfo:
        dt = dt.replace(tzinfo=tzinfo)
    return dt


def _relative_base(meeting_date: str, current_kst: datetime) -> datetime:
    if not meeting_date:
        return current_kst
    try:
        base = datetime.strptime(meeting_date, "%Y-%m-%d")
        return datetime(
            base.year,
            base.month,
            base.day,
            9,
            0,
            0,
            tzinfo=current_kst.tzinfo
        )
    except Exception:
        return current_kst


def _infer_meeting_date(meeting_notes: str, current_kst: datetime) -> str:
    if not meeting_notes:
        return ""

    match = re.search(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", meeting_notes)
    if match:
        year, month, day = match.groups()
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"

    match = re.search(r"(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일", meeting_notes)
    if match:
        year, month, day = match.groups()
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"

    match = re.search(r"(\d{1,2})\s*월\s*(\d{1,2})\s*일", meeting_notes)
    if match:
        month, day = match.groups()
        return f"{current_kst.year:04d}-{int(month):02d}-{int(day):02d}"

    return ""


def _normalize_meeting_date(
    meeting_date: str,
    meeting_notes: str,
    current_kst: datetime,
) -> str:
    candidate = (meeting_date or "").strip()
    if candidate:
        try:
            datetime.strptime(candidate, "%Y-%m-%d")
            return candidate
        except Exception:
            pass

    inferred = _infer_meeting_date(meeting_notes, current_kst)
    if inferred:
        return inferred

    return ""


def _extract_datetime_expression_from_sentence(sentence: str) -> str | None:
    date_match = None
    for pattern in _DATE_PATTERNS:
        match = pattern.search(sentence)
        if match:
            date_match = match.group(1)
            break
    if not date_match:
        return None

    time_match = None
    for pattern in _TIME_PATTERNS:
        match = pattern.search(sentence)
        if match:
            time_match = match.group(1)
            break

    if time_match:
        return f"{date_match} {time_match}"
    return date_match


def _collect_datetime_expressions(meeting_notes: str) -> List[Dict[str, str]]:
    if not meeting_notes:
        return []
    sentences = [s.strip() for s in re.split(r"[\n\.!?]", meeting_notes) if s.strip()]
    expressions = []
    for sentence in sentences:
        expr = _extract_datetime_expression_from_sentence(sentence)
        if expr:
            expressions.append({"sentence": sentence, "expr": expr})
    return expressions


def _keywords_from_item(item: Dict[str, Any]) -> List[str]:
    text = item.get("suggested_calendar_title") or item.get("task") or ""
    if not text:
        return []
    cleaned = re.sub(r"[\[\]\(\)\"']", " ", text)
    cleaned = re.sub(r"[^0-9A-Za-z가-힣\s]", " ", cleaned)
    tokens = [tok for tok in cleaned.split() if len(tok) >= 2]
    return list(dict.fromkeys(tokens))


def _match_expression_for_item(
    item: Dict[str, Any],
    expressions: List[Dict[str, str]],
    used_indices: set,
) -> str | None:
    keywords = _keywords_from_item(item)
    if keywords:
        for idx, entry in enumerate(expressions):
            if idx in used_indices:
                continue
            if any(keyword in entry["sentence"] for keyword in keywords):
                used_indices.add(idx)
                return entry["expr"]

    for idx, entry in enumerate(expressions):
        if idx in used_indices:
            continue
        used_indices.add(idx)
        return entry["expr"]

    return None


def _normalize_action_item_datetimes(
    action_items: List[Dict[str, Any]],
    meeting_date: str,
    current_kst: datetime,
    meeting_notes: str,
) -> List[Dict[str, Any]]:
    if not action_items:
        return action_items

    relative_base = _relative_base(meeting_date, current_kst)
    tzinfo = relative_base.tzinfo
    expressions = _collect_datetime_expressions(meeting_notes)
    used_indices: set = set()

    for item in action_items:
        if not isinstance(item, dict):
            continue

        expr = (item.get("datetime_expression") or "").strip()
        if not expr:
            expr = _match_expression_for_item(item, expressions, used_indices) or ""
            if expr:
                item["datetime_expression"] = expr
        if not expr:
            continue

        try:
            parsed = dateparser.parse(
                expr,
                languages=["ko"],
                settings={
                    "PREFER_DATES_FROM": "future",
                    "RELATIVE_BASE": relative_base,
                    "TIMEZONE": "Asia/Seoul",
                    "RETURN_AS_TIMEZONE_AWARE": True,
                },
            )
        except Exception as exc:
            logger.warning(f"[MEETING_TOOL] dateparser failed for '{expr}': {exc}")
            continue

        if not parsed:
            continue

        if not _TIME_HINT_RE.search(expr):
            parsed = parsed.replace(hour=9, minute=0, second=0, microsecond=0)

        if parsed.tzinfo and tzinfo:
            parsed = parsed.astimezone(tzinfo)
        elif tzinfo and parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=tzinfo)

        duration = None
        start_val = item.get("suggested_start_time")
        end_val = item.get("suggested_end_time")
        if start_val and end_val:
            try:
                start_dt = _parse_iso_datetime(start_val, tzinfo)
                end_dt = _parse_iso_datetime(end_val, tzinfo)
                delta = end_dt - start_dt
                if delta.total_seconds() > 0:
                    duration = delta
            except Exception:
                duration = None

        if duration is None:
            duration = timedelta(hours=1)

        item["suggested_start_time"] = parsed.strftime("%Y-%m-%dT%H:%M:%S")
        item["suggested_end_time"] = (parsed + duration).strftime("%Y-%m-%dT%H:%M:%S")
        item["due_date"] = parsed.strftime("%Y-%m-%d")

    return action_items

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
    대용량 회의록은 내부적으로 분할 처리하여 GPU 부하를 관리합니다.
    """
    if not meeting_notes or len(meeting_notes.strip()) < 10:
        logger.warning(f"[MEETING_TOOL] Received empty or very short meeting_notes: '{meeting_notes}'")
        return json.dumps({
            "summary": "입력된 회의록 내용이 너무 적거나 없습니다. 회의록 전문을 입력해 주세요.",
            "action_items": []
        }, ensure_ascii=False)

    # 1. Chunking Logic (Split by newline/paragraph if too long)
    # Roughly 1500 chars per chunk to avoid token limits on 20B model
    MAX_CHUNK_SIZE = 1500
    chunks = []
    if len(meeting_notes) > MAX_CHUNK_SIZE:
        lines = meeting_notes.split('\n')
        current_chunk = ""
        for line in lines:
            if len(current_chunk) + len(line) < MAX_CHUNK_SIZE:
                current_chunk += line + '\n'
            else:
                chunks.append(current_chunk.strip())
                current_chunk = line + '\n'
        if current_chunk:
            chunks.append(current_chunk.strip())
    else:
        chunks = [meeting_notes.strip()]

    logger.info(f"[MEETING_TOOL] Processing meeting notes in {len(chunks)} chunks.")

    current_kst = now_kst()
    meeting_date = _normalize_meeting_date(meeting_date, meeting_notes, current_kst)
    meeting_base = _relative_base(meeting_date, current_kst)
    current_date = meeting_date or meeting_base.strftime("%Y-%m-%d")
    current_weekday = ["월", "화", "수", "목", "금", "토", "일"][meeting_base.weekday()]
    
    today_date = current_date
    next_monday = meeting_base + timedelta(days=(7 - meeting_base.weekday()))
    next_monday_date = next_monday.strftime("%Y-%m-%d")
    this_friday = meeting_base + timedelta(days=(4 - meeting_base.weekday()))
    this_friday_date = this_friday.strftime("%Y-%m-%d")

    all_action_items = []
    all_summaries = []
    all_participants = set()
    all_topics = set()
    all_decisions = set()

    # 2. Iterative Processing
    for i, chunk in enumerate(chunks):
        logger.info(f"[MEETING_TOOL] Processing chunk {i+1}/{len(chunks)}...")
        
        system_prompt = MEETING_SUMMARY_SYSTEM_PROMPT.format(
            current_date=current_date,
            current_weekday=current_weekday
        )
        
        few_shot = MEETING_SUMMARY_FEW_SHOT.format(
            today_date=today_date,
            next_monday_date=next_monday_date,
            this_friday_date=this_friday_date
        )

        full_prompt = f"{system_prompt}\n\n{few_shot}\n\n입력 (Chunk {i+1}): \"{chunk}\"\n\n출력:"

        try:
            # Use is_complex=True to leverage Dual GPU and higher num_ctx
            llm = get_llm(keep_alive="5m", is_complex=True)
            response = llm.invoke(full_prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            json_str = extract_json(content) or content
            res_json = json.loads(json_str)
            
            all_summaries.append(res_json.get("summary", ""))
            all_participants.update(res_json.get("participants", []))
            all_topics.update(res_json.get("key_topics", []))
            all_decisions.update(res_json.get("decisions", []))
            all_action_items.extend(res_json.get("action_items", []))
            
        except Exception as e:
            logger.error(f"[MEETING_TOOL] Error processing chunk {i}: {e}")
            all_summaries.append(f"[Error in chunk {i}]")

    all_action_items = _normalize_action_item_datetimes(
        all_action_items,
        meeting_date=meeting_date,
        current_kst=current_kst,
        meeting_notes=meeting_notes,
    )

    # 3. Final Integration
    final_result = {
        "summary": " ".join(all_summaries),
        "participants": list(all_participants),
        "key_topics": list(all_topics),
        "decisions": list(all_decisions),
        "action_items": all_action_items
    }
    
    return json.dumps(final_result, ensure_ascii=False)
