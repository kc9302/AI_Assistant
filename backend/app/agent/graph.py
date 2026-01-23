import asyncio
from langgraph.graph import StateGraph, END
import logging
from langchain_core.messages import SystemMessage
from langgraph.prebuilt import ToolNode
from app.agent.state import AgentState
from app.agent.llm import get_llm
from app.core.settings import settings
from app.tools.calendar import (
    list_calendars,
    list_events,
    create_event,
    delete_event,
    _get_selected_calendars
)
from app.tools.memory_tools import memory_tools
from app.tools.travel_tools import travel_tools
from app.tools.meeting_tools import summarize_meeting_notes # Added
from app.tools.calendar import verify_calendar_registrations # Added

logger = logging.getLogger(__name__)

from app.services.memory import memory_service

# List of tools
tools = [
    list_calendars,
    list_events,
    create_event,
    delete_event,
    summarize_meeting_notes, # Added
    verify_calendar_registrations # Added
] + memory_tools + travel_tools

from langchain_core.output_parsers import PydanticOutputParser
from app.agent.schemas import PlannerResponse, ExecutorResponse, RouterResponse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
import time
import re
from datetime import datetime, timedelta
import json # Added import
from app.core.google_auth import get_calendar_service # Added import
from app.services.context_manager import context_manager # Added import
from app.core.utils import extract_json # Added import
from app.core.datetime_utils import now_kst

TRAVEL_ROUTER_HINTS = (
    "osaka", "오사카", "간사이", "일본",
    "비행", "항공", "항공편", "항공권", "항공사", "편명", "탑승", "게이트",
    "출발", "도착", "환승", "경유", "수하물", "예약번호", "pnr",
    "flight", "airline", "booking", "ticket", "boarding", "gate", "itinerary",
    "여행", "여정", "숙소", "호텔", "렌터카", "투어",
)
TRAVEL_ROUTER_REGEX = (
    re.compile(r"\b(kix|itm|nrt|hnd|icn|gmp)\b", re.IGNORECASE),
    re.compile(r"\b(e-?ticket|eticket)\b", re.IGNORECASE),
)
CALENDAR_ONLY_HINTS = (
    "캘린더", "calendar", "일정", "스케줄", "회의", "미팅", "약속",
    "오늘 일정", "내일 일정", "이번 주 일정", "주간 일정", "월간 일정",
    "today schedule", "tomorrow schedule", "weekly schedule",
)
CALENDAR_FORCE_HINTS = (
    "일정", "캘린더", "스케줄", "미팅", "회의", "약속",
    "schedule", "calendar", "meeting", "appointment",
)
CALENDAR_CREATE_HINTS = (
    "추가", "등록", "만들", "잡아", "예약", "생성",
    "add", "create", "book", "set up", "schedule",
)

def is_travel_query(message: str) -> bool:
    if not message:
        return False
    text = message.lower()
    has_travel_hint = any(hint in text for hint in TRAVEL_ROUTER_HINTS) or any(
        pattern.search(text) for pattern in TRAVEL_ROUTER_REGEX
    )
    has_calendar_hint = any(hint in text for hint in CALENDAR_ONLY_HINTS)

    if has_calendar_hint and not has_travel_hint:
        return False
    return has_travel_hint

def is_calendar_query(message: str) -> bool:
    if not message:
        return False
    text = message.lower()
    if any(hint in text for hint in CALENDAR_ONLY_HINTS):
        return True
    return any(hint in text for hint in CALENDAR_FORCE_HINTS)

def is_calendar_create_query(message: str) -> bool:
    if not message:
        return False
    text = message.lower()
    return any(hint in text for hint in CALENDAR_CREATE_HINTS)

def is_calendar_list_query(message: str) -> bool:
    return is_calendar_query(message) and not is_calendar_create_query(message)

def extract_calendar_name(message: str) -> str | None:
    if not message:
        return None
    match = re.search(r"\[[^\]]+\]", message)
    if match:
        return match.group(0)
    return None

def calendar_intent_from_message(message: str) -> str:
    text = (message or "").lower()
    calendar_name = extract_calendar_name(message or "")
    if "오늘" in text or "today" in text:
        intent = "List events today"
    elif "내일" in text or "tomorrow" in text:
        intent = "List events tomorrow"
    elif "모레" in text or "day after tomorrow" in text:
        intent = "List events day after tomorrow"
    elif "이번 주" in text or "이번주" in text or "this week" in text or "주간" in text or "weekly" in text:
        intent = "List events this week"
    elif "다음 주" in text or "다음주" in text or "next week" in text:
        intent = "List events next week"
    else:
        intent = "List events"
    if calendar_name:
        intent += f" for calendar {calendar_name}"
    return intent

def normalize_travel_search_query(intent: str, last_user_message: str, args: dict) -> dict:
    """
    Ensure travel search uses a specific query rather than a vague destination-only lookup.
    """
    flight_hints = (
        "flight", "airline", "ticket", "boarding", "gate", "pnr",
        "비행", "항공", "항공편", "항공권", "항공사", "편명", "탑승", "게이트", "예약번호",
    )
    intent_text = (intent or "").lower()
    user_text = (last_user_message or "").lower()
    wants_flight = any(h in intent_text for h in flight_hints) or any(h in user_text for h in flight_hints)

    dest = args.get("destination") or args.get("location")
    query = args.get("query")

    def _looks_garbled(text: str) -> bool:
        if not text:
            return True
        has_hangul = any("\uac00" <= ch <= "\ud7a3" for ch in text)
        has_ascii = any("a" <= ch.lower() <= "z" or ch.isdigit() for ch in text)
        if not has_hangul and not has_ascii:
            return True
        # If most characters are non-alnum/non-Hangul, treat as garbled.
        valid = sum(1 for ch in text if ch.isalnum() or ("\uac00" <= ch <= "\ud7a3"))
        return valid < max(3, len(text) // 5) or "?" in text

    def _english_flight_query(destination: str | None) -> str:
        if destination:
            return f"{destination} flight number and time"
        return "flight number and time"

    def _english_hotel_query(destination: str | None) -> str:
        if destination:
            return f"{destination} hotel address and check-in time"
        return "hotel address and check-in time"

    def _needs_english(text: str) -> bool:
        return any("\uac00" <= ch <= "\ud7a3" for ch in text)

    if not query:
        if last_user_message and not _looks_garbled(last_user_message):
            if wants_flight:
                args["query"] = _english_flight_query(dest) if _needs_english(last_user_message) else last_user_message
            elif any(k in last_user_message.lower() for k in ["호텔", "숙소", "주소", "체크인", "체크아웃"]):
                args["query"] = _english_hotel_query(dest) if _needs_english(last_user_message) else last_user_message
            else:
                args["query"] = last_user_message
        elif dest and wants_flight:
            args["query"] = _english_flight_query(dest)
        elif dest:
            args["query"] = f"{dest} travel info"
    else:
        if _looks_garbled(query):
            if last_user_message and not _looks_garbled(last_user_message):
                args["query"] = _english_flight_query(dest) if wants_flight else last_user_message
            elif dest and wants_flight:
                args["query"] = _english_flight_query(dest)
            elif dest:
                args["query"] = f"{dest} travel info"
        elif wants_flight and dest:
            query_l = query.lower()
            if "flight" not in query_l and "비행" not in query_l and "항공" not in query_l:
                args["query"] = f"{dest} flight time {query}"
    return args

def normalize_list_events_dates(last_user_message: str, intent: str, args: dict) -> dict:
    if not last_user_message and not intent:
        return args
    text = f"{last_user_message} {intent or ''}".lower()
    has_explicit_date = bool(re.search(r"\b\d{4}-\d{2}-\d{2}\b", text)) or bool(
        re.search(r"\d{1,2}\s*월\s*\d{1,2}\s*일", text)
    )
    if has_explicit_date:
        return args

    target_offset = None
    if "오늘" in text or "today" in text:
        target_offset = 0
    elif "내일" in text or "tomorrow" in text:
        target_offset = 1
    elif "모레" in text or "day after tomorrow" in text:
        target_offset = 2

    if target_offset is None:
        return args

    current_kst = now_kst()
    target_date = (current_kst + timedelta(days=target_offset)).date()
    start_date = target_date.strftime("%Y-%m-%d")
    end_date = (target_date + timedelta(days=1)).strftime("%Y-%m-%d")
    if args.get("start_date") != start_date or args.get("end_date") != end_date:
        logger.info(f"Guardrail corrected list_events dates to {start_date} -> {end_date}.")
    args["start_date"] = start_date
    args["end_date"] = end_date
    return args

def get_current_time_str():
    current_kst = now_kst()
    return current_kst.strftime('%Y-%m-%d %H:%M:%S %A')

def get_date_references():
    """Returns a formatted string of relative date references for prompts."""
    current_kst = now_kst()
    today_str = current_kst.strftime('%Y-%m-%d')
    tomorrow_str = (current_kst + timedelta(days=1)).strftime('%Y-%m-%d')
    day_after_tomorrow_str = (current_kst + timedelta(days=2)).strftime('%Y-%m-%d')
    
    # Calculate next week's dates (Monday to Sunday)
    # weekday(): Monday=0, Tuesday=1, ..., Sunday=6
    days_until_next_monday = (7 - current_kst.weekday()) if current_kst.weekday() != 0 else 7
    next_monday = current_kst + timedelta(days=days_until_next_monday)
    next_week_dates = {
        "월요일": next_monday.strftime('%Y-%m-%d'),
        "화요일": (next_monday + timedelta(days=1)).strftime('%Y-%m-%d'),
        "수요일": (next_monday + timedelta(days=2)).strftime('%Y-%m-%d'),
        "목요일": (next_monday + timedelta(days=3)).strftime('%Y-%m-%d'),
        "금요일": (next_monday + timedelta(days=4)).strftime('%Y-%m-%d'),
        "토요일": (next_monday + timedelta(days=5)).strftime('%Y-%m-%d'),
        "일요일": (next_monday + timedelta(days=6)).strftime('%Y-%m-%d'),
    }
    
    ref_str = f"""DATE REFERENCE (Use these for relative date queries):
- 오늘 (Today): {today_str}
- 내일 (Tomorrow): {tomorrow_str}
- 2일 뒤 (2 days later): {day_after_tomorrow_str}
- 다음 주 월요일 (Next Monday): {next_week_dates['월요일']}
- 다음 주 화요일 (Next Tuesday): {next_week_dates['화요일']}
- 다음 주 수요일 (Next Wednesday): {next_week_dates['수요일']}
- 다음 주 목요일 (Next Thursday): {next_week_dates['목요일']}
- 다음 주 금요일 (Next Friday): {next_week_dates['금요일']}
- 다음 주 토요일 (Next Saturday): {next_week_dates['토요일']}
- 다음 주 일요일 (Next Sunday): {next_week_dates['일요일']}"""
    return ref_str

# Setup parsers
base_router_parser = PydanticOutputParser(pydantic_object=RouterResponse)
base_planner_parser = PydanticOutputParser(pydantic_object=PlannerResponse)
base_executor_parser = PydanticOutputParser(pydantic_object=ExecutorResponse)


def fix_json_with_llm(json_str: str, error: str, parser):
    """Custom fallback fixer for malformed JSON using the 27B model."""
    logger.info("Attempting to fix malformed JSON with Remote LLM...")
    llm = get_llm(model=settings.LLM_MODEL_PLANNER, format="json", is_complex=True)
    
    prompt = f"""The following text was expected to be a valid JSON but parsing failed. 
Error: {error}
Raw Text: 
{json_str}

Please extract and fix the JSON. Respond ONLY with the fixed JSON object.
"""
    try:
        response = llm.invoke(prompt)
        fixed_content = extract_json(response.content)
        return parser.parse(fixed_content)
    except Exception as e:
        logger.error(f"JSON Fixing failed: {e}")
        raise e

def router_node(state: AgentState, config):
    """
    Initial routing node.
    """
    thread_id = config.get("configurable", {}).get("thread_id", "default")
    profile = memory_service.get_user_profile(thread_id=thread_id)
    user_info = profile.get("user", {})
    facts = profile.get("facts", {})
    context_str = f"\nUser: {user_info}\nFacts: {facts}" if user_info or facts else ""
    time_str = f"Current Time(Asia/Seoul): {get_current_time_str()}"

    messages = state["messages"]
    last_user_message = next((m.content for m in reversed(messages) if isinstance(m, HumanMessage)), "")
    
    lower_user_message = last_user_message.lower()
    if is_calendar_query(last_user_message) and not is_travel_query(last_user_message):
        # Keywords that indicate we need complex reasoning/summary
        complex_keywords = ["회의록", "녹취록", "정리", "요약", "meeting notes", "transcript", "summary", "action items"]
        if not any(kw in lower_user_message for kw in complex_keywords):
            logger.info("Router short-circuit: calendar query -> simple")
            return {"router_mode": "simple"}

    system_prompt = f"""[Identity]
You are a STERN AI ROUTER. You ONLY output JSON. NO CHAT.

[Rules]
1. Categorize request into:
   - 'answer': Simple chat or Q&A using provided facts.
   - 'simple': Single calendar action.
   - 'complex': Reasoning or Meeting Summary.
2. {time_str}
3. {context_str}

[Output Format]
{base_router_parser.get_format_instructions()}
"""

    prompt = [SystemMessage(content=system_prompt), HumanMessage(content=last_user_message)]
    
    logger.info(f"Invoking Router ({settings.LLM_MODEL_ROUTER})...")
    start_t = time.time()
    try:
        primary_llm = get_llm(model=settings.LLM_MODEL_ROUTER, format="json")
        fallback_llm = get_llm(model=settings.LLM_MODEL_ROUTER, format="")
        modern_llm = primary_llm.with_fallbacks([fallback_llm])
        
        response = modern_llm.invoke(prompt)
        content = response.content
        json_str = extract_json(content)
        if not json_str:
             logger.warning("Router returned empty or invalid JSON. Defaulting to 'complex'. Content: " + str(content[:100]))
             # Ensure we don't return an empty string/message
             return {"router_mode": "complex"}
        
        try:
            parsed = base_router_parser.parse(json_str)
        except Exception as parse_err:
            logger.warning(f"Router JSON parse failed. Attempting fix... Error: {parse_err}")
            parsed = fix_json_with_llm(json_str, str(parse_err), base_router_parser)
                
        logger.info(f"Router Decision: {parsed.mode} in {time.time()-start_t:.2f}s")
        if is_travel_query(last_user_message) and parsed.mode in ("answer", "simple"):
            logger.info("Router override: travel query -> complex")
            return {"router_mode": "complex"}
        if is_calendar_query(last_user_message) and parsed.mode == "answer":
            logger.info("Router override: calendar query -> simple")
            return {"router_mode": "simple"}
        return {"router_mode": parsed.mode}
    except Exception as e:
        logger.error(f"Routing failed: {e}")
        return {"router_mode": "complex"}

def _should_suppress_travel_facts(message: str) -> bool:
    if not message:
        return False
    text = message.lower()
    calendar_only = (
        "캘린더", "calendar", "일정", "스케줄", "회의", "미팅", "약속",
        "오늘 일정", "내일 일정", "이번 주 일정", "주간 일정", "월간 일정",
        "today schedule", "tomorrow schedule", "weekly schedule",
    )
    travel_only = (
        "여행", "여정", "오사카", "간사이", "항공", "비행", "호텔", "숙소",
        "flight", "airline", "ticket", "itinerary", "osaka",
    )
    has_calendar = any(h in text for h in calendar_only)
    has_travel = any(h in text for h in travel_only)
    return has_calendar and not has_travel


def _filter_travel_facts(facts: dict) -> dict:
    travel_keys = {
        "travel_destination",
        "date_of_travel",
        "travel_dates",
        "flight_details",
        "flight_info",
        "accommodation",
        "hotel",
        "destination",
    }
    return {k: v for k, v in facts.items() if k not in travel_keys}

def _is_registration_confirmation(message: str) -> bool:
    if not message:
        return False
    lowered = message.lower()
    keywords = [
        "등록", "진행", "해줘", "해주세요", "해 줘", "해 주세요",
        "yes", "confirm", "ok", "okay"
    ]
    return any(k in lowered for k in keywords)


def planner(state: AgentState, config):
    """The planner node using Remote LLM with Structured Output."""
    from app.services.memory import memory_service
    thread_id = config.get("configurable", {}).get("thread_id", "default")
    profile = memory_service.get_user_profile(thread_id=thread_id)
    user_info = profile.get("user", {})
    facts = profile.get("facts", {})
    messages = state["messages"]
    last_user_msg = next((m.content for m in reversed(messages) if isinstance(m, HumanMessage)), "")
    if facts and _should_suppress_travel_facts(last_user_msg):
        facts = _filter_travel_facts(facts)
    context_str = f"\nUser Information: {json.dumps(user_info, ensure_ascii=False)}\nUser Preferences/Facts: {json.dumps(facts, ensure_ascii=False)}" if user_info or facts else ""
    time_str = f"Current Time(Asia/Seoul): {get_current_time_str()}"
    date_ref_str = get_date_references()

    pending_events = state.get("pending_calendar_events") or []
    if state.get("meeting_workflow_step") == "review" and pending_events:
        if _is_registration_confirmation(last_user_msg):
            assistant_msg = "일정 등록을 진행할게요."
            return {
                "messages": [AIMessage(content=assistant_msg)],
                "planner_response": PlannerResponse(
                    mode="execute",
                    assistant_message=assistant_msg,
                    intent_description="Confirm and register all pending_calendar_events",
                    needs_confirmation=False,
                    language="ko",
                ),
                "mode": "execute",
                "intent_summary": "Confirm and register all pending_calendar_events",
                "needs_confirmation": False,
                "pending_calendar_events": pending_events,
            }
    
    # Check if we just came from a tool execution
    has_tool_result = any(isinstance(m, AIMessage) and m.tool_calls for m in reversed(messages))
    
    # More robust check for ToolMessage in history
    from langchain_core.messages import ToolMessage
    last_tool_msg = next((m for m in reversed(messages) if isinstance(m, ToolMessage)), None)
    is_current_tool_result = bool(last_tool_msg and messages and messages[-1] is last_tool_msg)

    # If a calendar tool just ran in the current turn, return its output directly.
    if (
        last_tool_msg
        and messages
        and messages[-1] is last_tool_msg
        and last_tool_msg.name in {
            "list_events",
            "list_calendars",
            "summarize_meeting_notes",
        }
    ):
        if last_tool_msg.name == "summarize_meeting_notes":
            try:
                result_data = json.loads(last_tool_msg.content)
                summary_text = result_data.get("summary", "")
                events = [item for item in result_data.get("action_items", []) if item.get("is_calendar_event")]
                
                if events:
                    event_list_str = "\n".join([f"- {e.get('suggested_calendar_title')} ({e.get('suggested_start_time')})" for e in events])
                    assistant_msg = f"📋 **회의록 요약**\n\n{summary_text}\n\n📅 **발견된 일정 ({len(events)}개)**:\n{event_list_str}\n\n이 일정들을 캘린더에 등록하시겠습니까?"
                    return {
                        "messages": [AIMessage(content=assistant_msg)],
                        "planner_response": PlannerResponse(
                            mode="plan",
                            assistant_message=assistant_msg,
                            intent_description="Summarize meeting and ask for calendar registration",
                            needs_confirmation=True,
                            language="ko"
                        ),
                        "mode": "plan",
                        "intent_summary": "Meeting summary confirmation",
                        "needs_confirmation": True,
                        "pending_calendar_events": events,
                        "last_meeting_summary": summary_text,
                        "meeting_workflow_step": "review"
                    }
                else:
                    # FALLBACK: If tool result is empty or not helpful, explain and ask for natural answer
                    logger.warn("summarize_meeting_notes returned no events. Forcing natural summary.")
                    summary_prompt = [
                        SystemMessage(content="A tool was executed to summarize meeting notes but returned empty data. Summarize the conversation history for the user and ask for the specific meeting content if it was missing. DO NOT OUTPUT JSON. Answer in Korean."),
                        HumanMessage(content=f"Last tool result: {last_tool_msg.content}")
                    ]
                    summary_res = get_llm().invoke(summary_prompt)
                    return {
                        "messages": [summary_res],
                        "mode": "plan",
                        "intent_summary": "Ask for meeting content clarification"
                    }
            except Exception as e:
                logger.error(f"Error parsing meeting summary result: {e}")

        # Fast-Path: If tool result is meeting summary, the assistant_msg is already well-formatted.
        # Just use it directly instead of calling LLM again for a generic summary.
        if last_tool_msg.name == "summarize_meeting_notes":
            # (Handled in the block above already)
            pass
        else:
            logger.info(f"Summarizing tool result for user...")
            # Use a simple template-based summary if possible, or a very short LLM call
            summary_prompt = [
                SystemMessage(content="Summarize this tool result for the user in 1-2 friendly Korean sentences. NO JSON. IMPORTANT: Keep the original event summaries EXACTLY as they are (e.g., preserve brackets like [MemberName])."),
                HumanMessage(content=f"Tool: {last_tool_msg.name}\nOutput: {str(last_tool_msg.content)}")
            ]
            summary_res = get_llm().invoke(summary_prompt)
            return {
                "messages": [summary_res],
                "mode": "plan",
                "intent_summary": f"Summarize {last_tool_msg.name}"
            }
    
    logger.info(f"Invoking Remote Planner ({settings.LLM_MODEL_PLANNER}) - JSON Mode")
    remote_llm = get_llm(model=settings.LLM_MODEL_PLANNER, format="json", is_complex=True) # Enable Dual GPU for Reasoning
    # structured_llm = remote_llm.with_structured_output(PlannerResponse) # Removed for OSS compatibility
    
    system_prompt = f"""[Identity]
You are a PROFESSIONAL PLANNER. YOU ONLY OUTPUT JSON.

[Task]
1. Respond to user or decide to execute a tool.
2. Modes: 'plan' (direct answer), 'execute' (need tool).
3. {time_str}
4. {date_ref_str}
5. {context_str}

[Tools]
{[t.name for t in tools]}

[Recent Memory]
- Facts: {json.dumps(facts, ensure_ascii=False)}
- History: {json.dumps(profile.get("history", []), ensure_ascii=False)}

[Crucial Rules]
- When extracting calendar events, ALWAYS use absolute dates (YYYY-MM-DD) in the 'intent_description' to help the Executor. Use the 'Current Time' below as reference.
- Meeting Notes -> MUST set 'mode': 'execute' and 'intent_description': 'Summarize meeting and extract calendar events'.
- Calendar Queries -> MUST set 'mode': 'execute'.
- Respond in {state.get("language", "Korean")}.
- When describing a successful registration, say ONLY something like "[Event Name]을(를) [Calendar Name]에 [Time]에 추가했습니다." (No "Double-checked", no technical details).
- **REGISTRATION STATUS**: NEVER claim "I have registered" or "Added to calendar" until you see a `ToolMessage` with `status: success` from `create_event`.
- **WORKFLOW**: Current Meeting Workflow Step: {state.get('meeting_workflow_step', 'None')}. 
    - If 'review', use a numbered list for events (e.g., "1. [Meeting] at 10:00") and ask "Would you like to register all, or just specific ones?".
    - If user says "Proceed" or "Yes" during 'review', set `mode`: 'execute' and `intent_description`: 'Confirm and register all pending_calendar_events'.
    - If 'registration_in_progress', you MUST execute `verify_calendar_registrations` with the current thread_id.
    - If tool result from `verify_calendar_registrations` is present, summarize ALL results (요약 + 등록 결과 + Deep Verified 상태) and set `meeting_workflow_step` to 'completed'.
- **CALENDAR LIST**: When summarizing `list_events`, DO NOT summarize. Output the list of events EXACTLY as they appear in the tool result. Keep all brackets like `[Name]` and all prefixes. DO NOT change a single character of the event summaries.
- **STRICT DATE FILTERING**: If the user asks for "today" (오늘) or a specific date, IGNORE any item in the tool result that does not match that specific date. For example, if today is 2026-01-22 and the tool result contains 2026-01-23, EXCLUDE it from your summary.
- **CLEAN UI**: NEVER show `eventId` or `calendar_id` in the `assistant_message`.

[Output Format]
{base_planner_parser.get_format_instructions()}
"""
    # If we have tool results, the planner must likely summarize (mode='plan')
    if is_current_tool_result:
        tool_data = str(last_tool_msg.content)
        # TRUNCATION: Limit to 4000 chars to avoid context window blowup
        if len(tool_data) > 4000:
             logger.info(f"Truncating large tool result in Planner: {len(tool_data)} -> 4000 chars")
             tool_data = tool_data[:4000] + "\n\n...(Results truncated for brevity)..."
             
        logger.info(f"Planner received tool result ({len(tool_data)} chars).")
        system_prompt += f"\n\nCRITICAL: A tool was just executed with the following result:\n{tool_data}\n\nINSTRUCTION: The answer is likely in the text above. READ CAREFULLY. Use 'mode': 'plan' and summarize the information for the user immediately. DO NOT call the same tool again with the same query."
    
    # Repeat language rule at the very bottom with more force
    system_prompt += "\n\nFINAL COMMAND: Ensure 'language' matches the user's language and 'assistant_message' is in THAT language."

    # Inject Recent Events Context
    thread_id = config.get("configurable", {}).get("thread_id", "default")
    recent_events = context_manager.get_recent_events(thread_id)
    if recent_events:
        recent_events_str = "\n".join([f"- ID: {e['event_id']}, Summary: {e['summary']}, Created: {e['created_at']}" for e in recent_events])
        system_prompt += f"\n\n[RECENTLY CREATED EVENTS (Use these IDs for deletion/updates)]:\n{recent_events_str}\n"

    # Adding format instructions
    system_prompt += f"\n\nRESPONSE FORMAT:\nRespond ONLY in valid JSON. \n{base_planner_parser.get_format_instructions()}"

    prompt_messages = [SystemMessage(content=system_prompt)] + [m for m in messages if not isinstance(m, SystemMessage)]
    
    # Add a final context-aware language hint
    is_ko = any(ord(char) > 0x1100 for char in last_user_msg)
    lang_hint = "Korean" if is_ko else "English"
    language_code = "ko" if is_ko else "en"
    prompt_messages.append(HumanMessage(content=f"[SYSTEM HINT: Output language must be {lang_hint}. OUTPUT JSON ONLY.]"))
    
    logger.info(f"Submitting to Remote Planner...")
    start_t = time.time()
    try:
        # Modern LangChain Pattern: Fallback from JSON mode to Normal mode automatically
        # format="json" may fail or return empty on some local models. 
        # .with_fallbacks handles the switch if the first call raises an exception.
        primary_llm = get_llm(model=settings.LLM_MODEL_PLANNER, format="json", is_complex=True)
        fallback_llm = get_llm(model=settings.LLM_MODEL_PLANNER, format="", is_complex=True)
        
        modern_llm = primary_llm.with_fallbacks([fallback_llm])
        
        response = modern_llm.invoke(prompt_messages)
        content = response.content
        
        if not content or not content.strip():
             # If even fallback returned empty, try one last time with fresh fallback instance
             logger.warning("Modern LLM returned empty content. Final manual retry...")
             response = fallback_llm.invoke(prompt_messages)
             content = response.content

        json_str = extract_json(content)
        if not json_str:
            logger.warning(f"Planner returned non-JSON content. Using raw content for parsing.")
            json_str = content

        try:
            parsed = base_planner_parser.parse(json_str)
        except Exception as parse_err:
            logger.warn(f"Planner JSON parse failed: {parse_err}. Raw content: {json_str}. Attempting fix...")
            
            # FALLBACK for Deletion: If parsing fails but user wants deletion, force a delete action
            if last_user_msg and any(kw in last_user_msg for kw in ["삭제", "취소", "delete", "cancel", "remove"]):
                logger.info("Planner fallback: Deletion intent detected despite parse failure. Forcing 'execute' mode.")
                parsed = PlannerResponse(
                    mode="execute",
                    intent_description="Delete the most recent event from memory.",
                    assistant_message="네, 방금 등록한 일정을 삭제하도록 하겠습니다.",
                    language=language_code
                )
            else:
                try:
                    parsed = fix_json_with_llm(json_str, str(parse_err), base_planner_parser)
                except:
                    # Final fallback: if everything fails, return a plan mode response to avoid complete crash
                    logger.error("All JSON parsing and fixing failed. Using emergency plan response.")
                    parsed = PlannerResponse(
                        mode="plan",
                        assistant_message="죄송합니다. 요청을 이해했지만 처리하는 중에 기술적인 문제가 발생했습니다. (JSON 파싱 오류)",
                        language=language_code
                    )
        
        if is_calendar_list_query(last_user_msg) and not is_current_tool_result:
            logger.info("Planner override: calendar list query -> execute")
            parsed.mode = "execute"
            parsed.intent_description = calendar_intent_from_message(last_user_msg)
            parsed.assistant_message = "일정을 확인할게요." if is_ko else "I'll check your schedule."
            parsed.language = language_code
            parsed.needs_confirmation = False

        # If the model still tries to execute despite having results, and it's a simple list, force plan
        if is_current_tool_result and parsed.mode == "execute":
             logger.warn("Model attempted to execute again immediately after tool call. Forcing 'plan' mode to avoid loop.")
             parsed.mode = "plan"
             
             # If assistant_message is generic or still says "Searching...", try to force a summary
             if any(x in parsed.assistant_message.lower() for x in ["검색", "확인", "search", "check"]):
                 summary_prompt = [
                     SystemMessage(content="You previously tried to search but we are in a loop. Summarize the following tool result for the user in natural language. DO NOT OUTPUT JSON. Answer directly to the user."),
                     HumanMessage(content=f"Tool result to summarize: {str(last_tool_msg.content)}")
                 ]
                 summary_res = get_llm().invoke(summary_prompt)
                 parsed.assistant_message = summary_res.content
                 logger.info(f"Forced natural summary generated: {parsed.assistant_message[:100]}...")

        logger.info(f"Planner complete in {time.time()-start_t:.2f}s. Mode: {parsed.mode}")
        
        # If mode is execute, we don't want to show the assistant's internal reasoning/draft to the user.
        final_assistant_msg = parsed.assistant_message
        
        # UI Policy: Simple registration message
        if "추가했습니다" in final_assistant_msg and ("Double" in final_assistant_msg or "Verified" in final_assistant_msg):
            # Clean up if the model still outputs verify text
            import re
            final_assistant_msg = re.sub(r"\(Double-checked.*?\)", "", final_assistant_msg).strip()
            final_assistant_msg = re.sub(r"\(Verified.*?\)", "", final_assistant_msg).strip()

        updates = {
            "messages": [AIMessage(content=final_assistant_msg)], 
            "planner_response": parsed,
            "mode": parsed.mode,
            "intent_summary": parsed.intent_description,
            "needs_confirmation": parsed.needs_confirmation
        }

        if parsed.mode == "execute":
             if not parsed.intent_description or len(parsed.intent_description) < 10:
                  parsed.intent_description = parsed.assistant_message
             
             # PERSISTENCE: If user is providing meeting notes, save them to state
             if any(kw in last_user_msg.lower() for kw in ["회의록", "정리", "요약", "meeting", "transcript"]):
                  if len(last_user_msg) > 50:
                       updates["raw_meeting_notes"] = last_user_msg
                       logger.info(f"Persisted raw_meeting_notes to state ({len(last_user_msg)} chars)")
             
             # CONFIRMATION: If user says 'Yes' to registration, ensure the intent is mapped correctly
             if any(kw in last_user_msg.lower() for kw in ["응", "그래", "해줘", "좋아", "yes", "confirm", "등록"]):
                  # Check if we were just asking for confirmation (last message from assistant)
                  last_assistant_msg = next((m.content for m in reversed(messages) if isinstance(m, AIMessage)), "")
                  if "등록하시겠습니까" in last_assistant_msg or "register" in last_assistant_msg.lower():
                       parsed.intent_description = "Confirm and register all pending_calendar_events"
                       updates["intent_summary"] = parsed.intent_description
                       logger.info("Planner override: User confirmed registration.")

        logger.info(f"Final AI Response (Planner): {final_assistant_msg}")
        
        updates["messages"] = [AIMessage(content=final_assistant_msg)]
        return updates
    except Exception as e:
        logger.error(f"Planner encounterd critical error: {type(e).__name__}: {e}")
        # Log more context if possible
        try:
             logger.error(f"Last user message that caused error: {last_user_msg[:500]}...")
        except: pass
        
        friendy_msg = "죄송합니다. 요청을 처리하는 중에 문제가 발생했습니다. (모델 응답 지연 또는 오류)"
        return {"messages": [AIMessage(content=friendy_msg)], "mode": "plan"}

def executor_node(state: AgentState, config):
    intent = state.get("intent_summary") or next((m.content for m in reversed(state["messages"]) if isinstance(m, HumanMessage)), "List my events today")
    messages = state["messages"]
    messages = state["messages"]
    last_user_message = next((m.content for m in reversed(messages) if isinstance(m, HumanMessage)), "")
    
    date_ref_str = get_date_references()

    # Generate tool signatures
    tool_signatures = []
    for t in tools:
        args_schema = t.args_schema.schema() if t.args_schema else {}
        tool_signatures.append(f"- {t.name}: {t.description}\n  Args: {json.dumps(args_schema.get('properties', {}), ensure_ascii=False)}")
    tool_sigs_str = "\n".join(tool_signatures)

    pending_events = state.get('pending_calendar_events') or []
    logger.info(f"[DEBUG] executor_node - START - intent: {intent}, pending_events count: {len(pending_events)}")

    # --- RECOVERY LOGIC: If state is lost but intent is confirmation, try re-extracting from history ---
    if (not pending_events or len(pending_events) == 0) and 'pending_calendar_events' in (intent or ""):
         logger.info("[RECOVERY] pending_events is empty but intent suggests confirmation. Searching history...")
         from langchain_core.messages import ToolMessage
         for m in reversed(messages):
             if isinstance(m, ToolMessage) and m.name == "summarize_meeting_notes":
                 try:
                     res = json.loads(m.content)
                     pending_events = [item for item in res.get("action_items", []) if item.get("is_calendar_event")]
                     logger.info(f"[RECOVERY] Successfully re-extracted {len(pending_events)} events from ToolMessage.")
                     break
                 except Exception as e:
                     logger.error(f"[RECOVERY] Failed to parse ToolMessage: {e}")
    
    if not pending_events:
        pending_events = []

    system_prompt = f"""You are a Tool-Calling Expert. Generate the exact tool call for the intent.
Current Time(Asia/Seoul): {get_current_time_str()}

{date_ref_str}

Available tools:
{tool_sigs_str}

CRITICAL RULES FOR ARGUMENTS:
- When a tool requires 'calendar_id', you MUST look up the user-provided calendar name in the 'Calendar Name to ID Mapping' and use the corresponding 'id'.
    - If the name is not in the mapping, use 'primary'.
    - **Verify the ID matches the mapping EXACTLY. Do NOT truncate the domain (e.g., keep '@group.calendar.google.com').**
- ALWAYS use 'summary' for the event title, NEVER 'subject' or 'title'.

CALENDAR SELECTION RULES:
- **list_events**: 
    - **CRITICAL**: To view ALL calendars, DO NOT include 'calendar_id' in the arguments. Omit it entirely.
    - Only specify 'calendar_id' if the user explicitly mentions a specific calendar name (e.g., "[WS] Inc.", "work calendar").
    - Examples:
        - "오늘 일정 알려줘" → {{"start_date": "...", "end_date": "..."}} (NO calendar_id)
        - "[WS] Inc. 캘린더의 일정 보여줘" → {{"start_date": "...", "end_date": "...", "calendar_id": "wickedstorm.kr@gmail.com"}}
- **create_event**:
    - If user mentions a specific calendar, use that calendar_id.
    - Otherwise, use 'primary' or let Guardrail handle it.

TEMPORAL RULES:
- ALWAYS use the absolute YYYY-MM-DD from the 'DATE REFERENCE' above for 'start_date' and 'end_date'.
- For a single day view (e.g., "today", "tomorrow"), 'start_date' MUST be that day and 'end_date' MUST be 'start_date' + 1 day (the next day 00:00:00). This ensures the tool correctly filters for that specific day.

EVENT RULES:
- 'create_event': Use 'summary', 'start_time', 'end_time', 'calendar_id', 'description', 'location'.
    - **CRITICAL**: Use ISO 8601 format for times (e.g., '2026-01-08T10:00:00').
    - **RELATIVE DATES**: Use the 'DATE REFERENCE' table provided above.
        - Always double-check that the calculated date is in the FUTURE.
- 'delete_event': Use 'event_id'.
    - **CRITICAL**: 'event_id' is NOT the same as 'calendar_id'.
    - **NEVER** use an email-like string (e.g., '...@group.calendar.google.com') as an 'event_id'.
    - Look for the 'event_id' in the '[RECENTLY CREATED EVENTS]' section if the user refers to "that event" or "the event I just created".

EXAMPLES:
1. Intent: "내일 오전 10시에 '회의' 일정 추가해줘"
   Response: {{"proposed_action": {{"tool": "create_event", "args": {{"summary": "회의", "start_time": "2026-01-08T10:00:00Z", "end_time": "2026-01-08T11:00:00Z"}}}}, "reasoning": "Create event as requested."}}
2. Intent: "오늘 일정 보여줘"
   Response: {{"proposed_action": {{"tool": "list_events", "args": {{"start_date": "2026-01-16", "end_date": "2026-01-17"}}}}, "reasoning": "List all events for today."}}
3. Intent: "[WS] Inc. 캘린더 일정 보여줘"
   Response: {{"proposed_action": {{"tool": "list_events", "args": {{"start_date": "2026-01-16", "end_date": "2026-01-17", "calendar_id": "wickedstorm.kr@gmail.com"}}}}, "reasoning": "Specified calendar."}}
4. Intent: "방금 만든 일정 삭제해줘"
   Response: {{"proposed_action": {{"tool": "delete_event", "args": {{}}}}, "reasoning": "Delete the most recent event from memory."}}
5. Intent: "그거 취소해줘"
   Response: {{"proposed_action": {{"tool": "delete_event", "args": {{}}}}, "reasoning": "Referring to previous event. System will fill ID from context."}}

6. Intent: "Summarize meeting and extract calendar events" (based on provided notes)
   Response: {{"proposed_action": {{"tool": "summarize_meeting_notes", "args": {{"meeting_notes": "FULL_TEXT_FROM_HISTORY"}}}}, "reasoning": "Extract structured data from the meeting history."}}
   **CRITICAL**: You MUST provide the full meeting text in 'meeting_notes'. 
   - Check 'PENDING_RAW_NOTES' below. If it contains the meeting text, USE IT.
   - Otherwise, find the original text in the message history. DO NOT leave it empty.

PENDING_RAW_NOTES: {state.get('raw_meeting_notes', 'None')}

Intent: {intent}

PENDING EVENTS: {json.dumps(pending_events, ensure_ascii=False)}

7. Intent: "Confirm and register all pending_calendar_events" (with PENDING EVENTS provided)
   PENDING EVENTS: [{{"suggested_calendar_title": "미팅 A", "suggested_start_time": "2026-01-20T10:00:00"}}, {{"suggested_calendar_title": "미팅 B", "suggested_start_time": "2026-01-21T14:00:00"}}]
   Response: {{"proposed_actions": [
       {{"tool": "create_event", "args": {{"summary": "미팅 A", "start_time": "2026-01-20T10:00:00", "end_time": "2026-01-20T11:00:00"}}}},
       {{"tool": "create_event", "args": {{"summary": "미팅 B", "start_time": "2026-01-21T14:00:00", "end_time": "2026-01-21T15:00:00"}}}}
   ], "reasoning": "Register all extracted events as confirmed."}}

CRITICAL: If 'intent' is 'Confirm and register all pending_calendar_events', you MUST generate multiple tool calls to 'create_event' for EACH item in 'PENDING EVENTS'.
"""

    profile = memory_service.get_user_profile()
    user_info = profile.get("user", {})
    facts = profile.get("facts", {})
    
    # Fetch available calendars and create a name-to-id mapping
    calendar_name_to_id_map = {}
    try:
        service = get_calendar_service()
        if service:
            # _get_selected_calendars returns structured data
            calendars = _get_selected_calendars(service)
            for cal in calendars:
                calendar_name_to_id_map[cal['summary']] = cal['id']
    except Exception as e:
        logger.error(f"Failed to get calendar map for executor: {e}")
        # Fallback if map creation fails
        calendar_name_to_id_map = {"primary": "primary"} # Ensure at least primary is available

    # --- RECENT EVENTS CONTEXT INJECTION ---
    # --- RECENT EVENTS CONTEXT INJECTION ---
    thread_id = config.get("configurable", {}).get("thread_id", "default")
    recent_events = context_manager.get_recent_events(thread_id)
    recent_events_str = ""
    if recent_events:
         recent_events_str = "\n\n[RECENTLY CREATED EVENTS (Use these IDs for deletion)]:\n" + "\n".join([f"- Title: '{e['summary']}', ID: {e['event_id']}, Created: {e['created_at']}" for e in recent_events])
         system_prompt += recent_events_str

    context_str = f"User: {user_info}\nFacts: {facts}\n\nCalendar Name to ID Mapping: {json.dumps(calendar_name_to_id_map, ensure_ascii=False)}" + recent_events_str

    # Adding format instructions
    system_prompt += f"\n\nRESPONSE FORMAT:\nRespond ONLY in valid JSON. \n{base_executor_parser.get_format_instructions()}"

    executor_model = settings.LLM_MODEL_EXECUTOR or settings.LLM_MODEL_PLANNER
    
    primary_llm = get_llm(model=executor_model, format="json", is_complex=True)
    fallback_llm = get_llm(model=executor_model, format="", is_complex=True)
    modern_llm = primary_llm.with_fallbacks([fallback_llm])
    
    prompt = [SystemMessage(content=system_prompt), HumanMessage(content=f"Follow intent: {intent}")]
    
    logger.info(f"Invoking Remote Executor ({executor_model}) - Prompt Length: {len(system_prompt)}")
    logger.info(f"[DEBUG] executor_node - PENDING EVENTS in prompt: {json.dumps(pending_events, ensure_ascii=False)}")
    try:
        response = modern_llm.invoke(prompt)
        content = response.content
        json_str = extract_json(content)
        if not json_str:
             json_str = content
        
        try:
            parsed = base_executor_parser.parse(json_str)
        except Exception as parse_err:
             logger.warn(f"Executor JSON parse failed: {parse_err}. Attempting fix...")
             parsed = fix_json_with_llm(json_str, str(parse_err), base_executor_parser)

        if parsed.proposed_action:
             logger.info(f"Executor Decision: {parsed.proposed_action.tool}({parsed.proposed_action.args})")
        elif parsed.proposed_actions:
             logger.info(f"Executor Decision: Multiple ({len(parsed.proposed_actions)} actions)")
        # The original code had a return here, but the guardrails and toolcall creation were after it.
        # This implies the return was meant to be after the guardrails.
        # I will keep the guardrails and toolcall creation, and move the return to the end of the function.
    except Exception as e:
        logger.error(f"Executor failed with error type {type(e).__name__}: {e}")
        # Re-raise the exception to trigger the retry logic in main.py
        # Only catch and return friendly message if we're sure it's not a temporary GPU/Model issue
        if "rate limit" in str(e).lower() or "timeout" in str(e).lower() or "connection" in str(e).lower():
            raise e # Let main.py handle the retry
        
        # If it's a persistent logic error, we still want to inform the user but maybe still retry once
        raise e 

    if parsed:
        # --- GUARDRAIL: Fix ID Hallucination (Calendar ID vs Event ID) ---
        if parsed.proposed_action:
            if parsed.proposed_action.tool == "delete_event":
                eid = parsed.proposed_action.args.get("event_id")
                
                # 1. Triggers: Explicit "Recent" intent or suspicious ID format
                recent_keywords = ["방금", "just", "recent", "금방", "그 일정", "that event"]
                is_recent_intent = any(k in intent.lower() for k in recent_keywords)
                is_suspicious_id = (isinstance(eid, str) and len(eid) < 15) or (not eid)
                
                # 2. Action: Force Context Lookup
                if (is_recent_intent or is_suspicious_id) and recent_events:
                    corrected_id = recent_events[0]['event_id']
                    parsed.proposed_action.args["event_id"] = corrected_id
                    
                    ctx_cal_id = recent_events[0].get('calendar_id')
                    if ctx_cal_id:
                         parsed.proposed_action.args['calendar_id'] = ctx_cal_id
                         logger.info(f"Guardrail auto-filled calendar_id: '{ctx_cal_id}' from context.")
                    
                    logger.info(f"Guardrail applied. Swapped ID to '{corrected_id}'.")
                
                elif is_suspicious_id and not recent_events:
                     logger.warning(f"Guardrail detected suspicious ID '{eid}' but NO recent events found in context to swap.")
        
        # --- GUARDRAIL: Fix Calendar ID Truncation ---
        if parsed.proposed_action and "calendar_id" in parsed.proposed_action.args:
            cal_id = parsed.proposed_action.args["calendar_id"]
            # Check if this ID is valid (exists in map values)
            # We need to flatten the map values to check existence
            valid_ids = list(calendar_name_to_id_map.values())
            if cal_id and cal_id not in valid_ids and cal_id != "primary":
                # Check for partial match (truncation)
                for full_id in valid_ids:
                    if cal_id and full_id.startswith(cal_id) and "@" in full_id:
                        parsed.proposed_action.args["calendar_id"] = full_id
                        logger.info(f"Guardrail auto-corrected truncated calendar_id: '{cal_id}' -> '{full_id}'")
                        break
        # -----------------------------------------------------------------
        # --- GUARDRAIL: Improve travel search specificity ---
        if parsed.proposed_action and parsed.proposed_action.tool == "search_travel_info":
            parsed.proposed_action.args = normalize_travel_search_query(
                intent=intent,
                last_user_message=last_user_message,
                args=parsed.proposed_action.args,
            )
        # -----------------------------------------------------------------
        # --- GUARDRAIL: Match calendar name from user request ---
        if parsed.proposed_action and parsed.proposed_action.tool == "create_event":
            # Check if user mentioned a specific calendar name in their request
            matched_calendar = None
            for cal_name, cal_id in calendar_name_to_id_map.items():
                # Check both in the user message and the intent
                if cal_name in last_user_message or cal_name in intent:
                    matched_calendar = (cal_name, cal_id)
                    logger.info(f"Guardrail detected calendar mention: '{cal_name}' in user request")
                    break
            
            if matched_calendar:
                cal_name, cal_id = matched_calendar
                parsed.proposed_action.args["calendar_id"] = cal_id
                logger.info(f"Guardrail overriding calendar_id: '{cal_name}' -> {cal_id}")
            else:
                # If no specific calendar mentioned, check if there's already a calendar_id set
                current_cal_id = parsed.proposed_action.args.get("calendar_id", "primary")
                logger.info(f"No calendar mentioned in request. Using: {current_cal_id}")
        # -----------------------------------------------------------------

        from langchain_core.messages import ToolCall
        
        all_actions = []
        if parsed.proposed_actions:
            all_actions.extend(parsed.proposed_actions)
        elif parsed.proposed_action:
            all_actions.append(parsed.proposed_action)
        
        logger.info(f"[EXECUTOR] all_actions count: {len(all_actions)}")

        for action in all_actions:
            if action.tool == "list_events":
                action.args = normalize_list_events_dates(last_user_message, intent, action.args)

        if not all_actions:
             logger.warning("[EXECUTOR] No actions found in parsed response!")
             return {"messages": [AIMessage(content="도구 명령을 생성하는 데 실패했습니다.")], "mode": "plan"}

        # First, determine if user mentioned a specific calendar
        user_specified_calendar_id = None
        lower_user_msg = last_user_message.lower()
        lower_intent = intent.lower()
        
        for cal_name, cal_id in calendar_name_to_id_map.items():
            cal_name_lower = cal_name.lower()
            if cal_name_lower in lower_user_msg or cal_name_lower in lower_intent:
                user_specified_calendar_id = cal_id
                logger.info(f"User specified calendar detected in batch (case-insensitive): '{cal_name}' -> {cal_id}")
                break
        
        # Special case: Meeting registrations default to [WS] Inc. if no other calendar specified
        ws_calendar_id = calendar_name_to_id_map.get("[WS] Inc.")
        is_meeting_reg = (intent == 'Confirm and register all pending_calendar_events') or ("Summarize meeting" in intent)
        
        logger.info(f"CALENDAR_MAP: {json.dumps(calendar_name_to_id_map, ensure_ascii=False)}")
        tool_calls = []
        for i, action in enumerate(all_actions):
            # Apply calendar_id logic for create_event
            if action.tool == "create_event":
                logger.info(f"[Action {i}] Original args: {action.args}")
                if user_specified_calendar_id:
                    # User explicitly mentioned a calendar - use it
                    action.args["calendar_id"] = user_specified_calendar_id
                    logger.info(f"[Action {i}] Overriding with user-specified calendar: {user_specified_calendar_id}")
                elif is_meeting_reg and ws_calendar_id:
                    # Meeting registration without explicit calendar - default to [WS] Inc.
                    action.args["calendar_id"] = ws_calendar_id
                    logger.info(f"[Action {i}] Meeting registration - defaulting to '[WS] Inc.' ({ws_calendar_id})")
                else:
                    # No special handling - keep whatever the LLM decided (or default to primary)
                    current_cal = action.args.get("calendar_id", "primary")
                    logger.info(f"[Action {i}] No override needed. Using: {current_cal}")

                # --- DATE CORRECTION LOGIC ---
                # Force override date if user explicitly mentioned "Next Week Day"
                # This fixes LLM hallucination where it ignores the cheat sheet.
                current_kst = now_kst()
                
                # Re-calculate next week dates locally to be 100% sure
                days_until_next_monday = (7 - current_kst.weekday()) if current_kst.weekday() != 0 else 7
                next_monday = current_kst + timedelta(days=days_until_next_monday)
                next_week_map = {
                    "월요일": next_monday,
                    "화요일": next_monday + timedelta(days=1),
                    "수요일": next_monday + timedelta(days=2), # This will be 21st if today is 16th (Fri) -> Mon(19) -> Wed(21)
                    "목요일": next_monday + timedelta(days=3),
                    "금요일": next_monday + timedelta(days=4),
                    "토요일": next_monday + timedelta(days=5),
                    "일요일": next_monday + timedelta(days=6),
                }

                user_msg_lower = last_user_message.lower()
                for day_name, correct_date in next_week_map.items():
                    # Patterns: "다음 주 수요일", "다음주 수요일"
                    if f"다음 주 {day_name}" in last_user_message or f"다음주 {day_name}" in last_user_message:
                        original_start = action.args.get("start_time", "")
                        
                        # Parse original time part (HH:MM:SS) if possible
                        time_part = "10:00:00" # Default
                        if "T" in original_start:
                            time_part = original_start.split("T")[1]
                        
                        new_start = f"{correct_date.strftime('%Y-%m-%d')}T{time_part}"
                        
                        # Adjust end time accordingly (keep duration)
                        original_end = action.args.get("end_time", "")
                        if original_end and "T" in original_end:
                             # Calculate duration from original
                             try:
                                 orig_s = datetime.fromisoformat(original_start.replace('Z', '+00:00'))
                                 orig_e = datetime.fromisoformat(original_end.replace('Z', '+00:00'))
                                 duration = orig_e - orig_s
                                 new_end = (datetime.fromisoformat(new_start) + duration).isoformat()
                             except:
                                 # Fallback: 1 hour
                                 new_end = (datetime.fromisoformat(new_start) + timedelta(hours=1)).isoformat()
                        else:
                             new_end = (datetime.fromisoformat(new_start) + timedelta(hours=1)).isoformat()

                        action.args["start_time"] = new_start
                        action.args["end_time"] = new_end
                        logger.info(f"[Action {i}] DATE CORRECTION: 'Next {day_name}' detected. Forced date to {new_start[:10]}.")
                        break

                # Pass thread_id for verification
                action.args["thread_id"] = thread_id
                logger.info(f"[Action {i}] Final args to tool: {action.args}")

            if action.tool == "delete_event":
                if user_specified_calendar_id:
                    action.args["calendar_id"] = user_specified_calendar_id
                action.args.setdefault("thread_id", thread_id)

            if action.tool == "delete_event":
                # If ID is missing, try to fill from memory
                if not action.args.get("event_id"):
                    logger.info(f"[Action {i}] Empty delete_event - checking memory for thread_id={thread_id}")
                    recent = context_manager.get_recent_events(thread_id, limit=1)
                    if recent:
                        action.args["event_id"] = recent[0]["event_id"]
                        action.args["calendar_id"] = recent[0].get("calendar_id", "primary")
                        logger.info(f"[Action {i}] Injected recent event from memory: {recent[0]['summary']} ({action.args['event_id']})")
                    else:
                        # Fallback: Pass thread_id to the tool itself for a search-based delete
                        action.args["thread_id"] = thread_id
                        logger.info(f"[Action {i}] No memory found. Passing thread_id to tool for search.")
            tool_calls.append(ToolCall(
                name=action.tool,
                args=action.args,
                id=f"exec_{len(messages)}_{i}"
            ))
        
        logger.info(f"[EXECUTOR] Generated {len(tool_calls)} tool calls.")
            
        # If we successfully registered pending events, clear them from state
        # Ensure we always have content even if tool_calls exist, to avoid "empty model output" errors
        updates = {"messages": [AIMessage(content="일정 작업을 수행합니다...", tool_calls=tool_calls)]}
        if intent == 'Confirm and register all pending_calendar_events':
            updates["pending_calendar_events"] = None # Clear state
            
        return updates

def route_after_router(state: AgentState):
    """Routes based on router's decision."""
    # Always go through planner for superior temporal reasoning and intent processing.
    return "planner"

def route_planner(state: AgentState):
    if state.get("mode") == "execute":
        return "executor"
    return END

def route_tools(state: AgentState):
    """Routes based on whether the last message has tool calls."""
    last_message = state["messages"][-1]
    logger.info(f"--- ROUTE_TOOLS ---")
    logger.info(f"Last message type: {type(last_message)}")
    logger.info(f"Last message content: {last_message.content}")
    logger.info(f"Has 'tool_calls' attr: {hasattr(last_message, 'tool_calls')}")
    if hasattr(last_message, 'tool_calls'):
        logger.info(f"Value of 'tool_calls': {last_message.tool_calls}")

    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        logger.info(f"Decision: Routing to 'tools'")
        return "tools"
    
    logger.info(f"Decision: Routing to END")
    return END

def chatbot(state: AgentState):
    """Simple LLM node that can emit tool calls for unit tests."""
    llm = get_llm()
    llm_with_tools = llm.bind_tools(tools)
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}

def tool_with_logging(state: AgentState, config):
    """Execution node for tools with result logging and state updates."""
    tool_node = ToolNode(tools)
    result = tool_node.invoke(state)
    
    # 1. Iterate through ALL tool messages generated in this step
    # LangGraph result['messages'] contains the new ToolMessage objects
    from langchain_core.messages import ToolMessage
    new_messages = [m for m in result["messages"] if isinstance(m, ToolMessage)]
    
    registration_results = state.get("registration_results") or []
    verification_results = state.get("verification_results") or []
    current_step = state.get("meeting_workflow_step", "None")
    
    thread_id = config.get("configurable", {}).get("thread_id", "default")

    def _resolve_calendar_id_from_tool_call(tool_call_id: str | None) -> str | None:
        if not tool_call_id:
            return None
        for msg in reversed(state["messages"]):
            if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
                for call in msg.tool_calls:
                    if call.get("id") == tool_call_id:
                        return call.get("args", {}).get("calendar_id")
        return None

    for tool_msg in new_messages:
        logger.info(f"Processing Tool Result: {tool_msg.name}")
        content = tool_msg.content
        
        # --- Handle create_event result ---
        if tool_msg.name == "create_event":
            try:
                data = json.loads(content)
                calendar_id = data.get("calendar_id") or data.get("calendarId")
                if not calendar_id:
                    calendar_id = _resolve_calendar_id_from_tool_call(getattr(tool_msg, "tool_call_id", None))
                if not calendar_id:
                    calendar_id = "primary"
                res_entry = {
                    "summary": data.get("summary", "Unknown"),
                    "status": data.get("status", "error"),
                    "eventId": data.get("eventId"),
                    "calendar_id": calendar_id,
                    "error": data.get("error")
                }
                
                if res_entry["status"] == "success":
                    # Add to context memory for deletion/deep verification
                    context_manager.add_event(
                        thread_id=thread_id,
                        event_id=data["eventId"],
                        summary=data.get("summary", "Unknown"),
                        calendar_id=calendar_id
                    )
                
                registration_results.append(res_entry)
            except Exception as e:
                logger.error(f"Failed to parse create_event result: {e}")

        # --- Handle verify_calendar_registrations result ---
        elif tool_msg.name == "verify_calendar_registrations":
            try:
                data = json.loads(content)
                verification_results = data.get("results", [])
                logger.info(f"Verification completed: {len(verification_results)} items verified.")
            except Exception as e:
                logger.error(f"Failed to parse verification result: {e}")

    # 2. Update workflow state
    updates = {
        "messages": result["messages"],
        "registration_results": registration_results,
        "verification_results": verification_results
    }
    
    # If we just registered and verified, we might be 'completed'
    # The planner will make the final call on 'completed', but we provide the data.
    
    return updates

def get_graph(checkpointer=None):
    logger.info("--- get_graph with checkpointer support loaded. ---")
    # Define the graph
    workflow = StateGraph(AgentState)

    workflow.add_node("router", router_node)
    workflow.add_node("planner", planner)
    workflow.add_node("executor", executor_node)
    workflow.add_node("tools", tool_with_logging)

    workflow.set_entry_point("router")

    workflow.add_conditional_edges("router", route_after_router, {"executor": "executor", "planner": "planner", END: END})
    workflow.add_conditional_edges("planner", route_planner, {"executor": "executor", END: END})
    workflow.add_conditional_edges("executor", route_tools, {"tools": "tools", END: END})
    workflow.add_edge("tools", "planner") # After tool execution, go to planner for final response

    if checkpointer:
        return workflow.compile(checkpointer=checkpointer)
    else:
        # Fallback for non-async contexts or when no checkpointer is provided
        return workflow.compile()

# Default compiled graph for tests and simple usage
graph = get_graph()

