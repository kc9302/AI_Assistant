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
    list_today_events,
    list_events_on_date,
    list_upcoming_events,
    list_weekly_events,
    create_event,
    delete_event,
    _get_selected_calendars
)
from app.tools.memory_tools import memory_tools
from app.tools.travel_tools import travel_tools

logger = logging.getLogger(__name__)

from app.services.memory import memory_service

# List of tools
tools = [
    list_calendars,
    list_today_events,
    list_events_on_date,
    list_upcoming_events,
    list_weekly_events,
    create_event,
    delete_event
] + memory_tools + travel_tools

from langchain_core.output_parsers import PydanticOutputParser
from app.agent.schemas import PlannerResponse, ExecutorResponse, RouterResponse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
import time
import re
from datetime import datetime, timedelta, timezone
import json # Added import
from app.core.google_auth import get_calendar_service # Added import
from app.services.context_manager import context_manager # Added import
from app.core.utils import extract_json # Added import

TRAVEL_ROUTER_HINTS = (
    "비행", "항공", "항공편", "편명", "출발", "도착", "탑승", "예약번호",
    "flight", "airline", "booking", "ticket",
    "오사카", "간사이", "호텔", "숙소",
)

def is_travel_query(message: str) -> bool:
    if not message:
        return False
    text = message.lower()
    return any(hint in text for hint in TRAVEL_ROUTER_HINTS)

def get_current_time_str():
    kst = timezone(timedelta(hours=9))
    now = datetime.now(kst)
    return now.strftime('%Y-%m-%d %H:%M:%S %A')

# Setup parsers
base_router_parser = PydanticOutputParser(pydantic_object=RouterResponse)
base_planner_parser = PydanticOutputParser(pydantic_object=PlannerResponse)
base_executor_parser = PydanticOutputParser(pydantic_object=ExecutorResponse)


def fix_json_with_llm(json_str: str, error: str, parser):
    """Custom fallback fixer for malformed JSON using the 27B model."""
    logger.info("Attempting to fix malformed JSON with Remote LLM...")
    llm = get_llm(model=settings.OLLAMA_MODEL_PLANNER)
    
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

def router_node(state: AgentState):
    """
    Initial routing node. Tries Local (270M) first, falls back to Remote (27B).
    """
    profile = memory_service.get_user_profile()
    facts = profile.get("facts", {})
    context_str = f"\nUser Context: {facts}" if facts else ""
    time_str = f"Current Time(Asia/Seoul): {get_current_time_str()}"

    messages = state["messages"]
    last_user_message = next((m.content for m in reversed(messages) if isinstance(m, HumanMessage)), "")
    
    system_prompt = f"""You are an AI Assistant Router. Categorize the user request into 'simple', 'complex', or 'answer'.
{time_str}
{context_str}

Respond ONLY in JSON. {base_router_parser.get_format_instructions()}

- 'answer': General chat, greetings, questions about yourself, or questions that can be answered directly using 'User Facts' or 'Past Conversations'.
- 'simple': A single, clear calendar action (e.g., "Add meeting", "List events").
- 'complex': Requests requiring reasoning, multi-step actions, or searching deep into past session details.

Example 1: "Hi" -> {{"mode": "answer", "reasoning": "Simple greeting"}}
Example 2: "내 이름이 뭐야?" -> {{"mode": "answer", "reasoning": "Asking about personal info already in context"}}
Example 3: "Create a meeting tomorrow at 3pm" -> {{"mode": "simple", "reasoning": "Single tool call"}}
Example 4: "Check my schedule for next week and find a 1h slot for tennis" -> {{"mode": "complex", "reasoning": "Requires schedule analysis"}}
"""

    llm = get_llm(model=settings.OLLAMA_MODEL_PLANNER)
    prompt = [SystemMessage(content=system_prompt), HumanMessage(content=last_user_message)]
    
    logger.info("Invoking Router (27B)...")
    start_t = time.time()
    try:
        response = llm.invoke(prompt)
        content = response.content
        logger.debug(f"Raw Router Output: {content}")
        json_str = extract_json(content)
        
        try:
            parsed = base_router_parser.parse(json_str)
        except Exception as parse_err:
            parsed = fix_json_with_llm(json_str, str(parse_err), base_router_parser)
                
        logger.info(f"Router Decision: {parsed.mode} in {time.time()-start_t:.2f}s")
        if is_travel_query(last_user_message) and parsed.mode in ("answer", "simple"):
            logger.info("Router override: travel query -> complex")
            return {"router_mode": "complex"}
        return {"router_mode": parsed.mode}
    except Exception as e:
        logger.error(f"Routing failed: {e}")
        return {"router_mode": "complex"}

def planner(state: AgentState):
    """The planner node using Remote LLM with Structured Output."""
    from app.services.memory import memory_service
    profile = memory_service.get_user_profile()
    facts = profile.get("facts", {})
    context_str = f"\nKeep in mind these user preferences: {json.dumps(facts)}" if facts else ""
    time_str = f"Current Time(Asia/Seoul): {get_current_time_str()}"

    messages = state["messages"]
    
    # Check if we just came from a tool execution
    has_tool_result = any(isinstance(m, AIMessage) and m.tool_calls for m in reversed(messages))
    last_message = messages[-1]
    is_tool_message = hasattr(last_message, "content") and any(m.type == "tool" for m in messages[-2:] if hasattr(m, "type")) # Simplified check
    
    # More robust check for ToolMessage in history
    from langchain_core.messages import ToolMessage
    last_tool_msg = next((m for m in reversed(messages) if isinstance(m, ToolMessage)), None)
    
    remote_llm = get_llm(model=settings.OLLAMA_MODEL_PLANNER)
    structured_llm = remote_llm.with_structured_output(PlannerResponse)
    
    system_prompt = f"""You are a Versatile AI Assistant Planner. 
{time_str}
{context_str}

Analyze the conversation and determine the next step:
1. 'plan': Respond directly to the user (chat, greeting, answering from 'User Facts'/'Past Conversations') or ask for missing information.
2. 'execute': Perform a specific tool action (calendar operations or retrieving detailed session history).

Use 'plan' if you can answer the user's question directly using the provided 'User Facts' or 'Past Conversations' summaries.
Only use 'execute' if you strictly need a tool to fulfill the request.

Available tools: {[t.name for t in tools]}

LANGUAGE RULES:
- If the user's latest query is in Korean, you MUST set 'language': 'ko' and respond in Korean.
- If the user's latest query is in English, you MUST set 'language': 'en' and respond in English.
- This applies STRICTLY to the 'assistant_message' field.

LONG-TERM KNOWLEDGE:
- User Facts: {json.dumps(facts, ensure_ascii=False)}
- Past Conversations (Summaries): {json.dumps(profile.get("history", []), ensure_ascii=False)}

SELECTIVE MEMORY & KNOWLEDGE RETRIEVAL RULES:
1. If the request is about your upcoming Osaka trip and the current context lacks details (e.g., flight times, hotel names, specific itinerary), use 'execute' and call 'search_travel_info'.
2. If the request requires specific details from a past conversation (e.g., "What was the name of the place we talked about?"), set 'mode': 'execute' and call 'retrieve_past_session'.
3. If 'User Facts', 'Past Conversations' summaries, or search results already provide enough context, do NOT call tools. Just respond.
4. Use 'search_travel_info' for external travel documents, and 'retrieve_past_session' for specific past chats.

EXAMPLES OF SEARCH DECISIONS:
- User: "When is my flight to Osaka?" -> Mode: 'execute', Tool: 'search_travel_info', Intent: "Check flight schedule to Osaka"
- User: "Where is my hotel?" -> Mode: 'execute', Tool: 'search_travel_info', Intent: "Check hotel address in Osaka"
- User: "What did we say about the budget last time?" -> Mode: 'execute', Tool: 'retrieve_past_session', Intent: "Fetch previous chat about budget"
- User: "Hi there!" -> Mode: 'plan', message: "Hello! How can I help you today?"
"""
    # If we have tool results, the planner must likely summarize (mode='plan')
    if last_tool_msg:
        tool_data = str(last_tool_msg.content)
        logger.info(f"Planner received tool result ({len(tool_data)} chars).")
        system_prompt += f"\n\nCRITICAL: A tool was just executed with the following result:\n{tool_data}\n\nINSTRUCTION: The answer is likely in the text above. READ CAREFULLY. Use 'mode': 'plan' and summarize the information for the user immediately. DO NOT call the same tool again with the same query."
    
    # Repeat language rule at the very bottom with more force
    system_prompt += "\n\nFINAL COMMAND: Ensure 'language' matches the user's language and 'assistant_message' is in THAT language."

    # Inject Recent Events Context
    recent_events = context_manager.get_recent_events(state.get("configurable", {}).get("thread_id", "default"))
    if recent_events:
        recent_events_str = "\n".join([f"- ID: {e['event_id']}, Summary: {e['summary']}, Created: {e['created_at']}" for e in recent_events])
        system_prompt += f"\n\n[RECENTLY CREATED EVENTS (Use these IDs for deletion/updates)]:\n{recent_events_str}\n"

    prompt_messages = [SystemMessage(content=system_prompt)] + [m for m in messages if not isinstance(m, SystemMessage)]
    
    # Add a final context-aware language hint
    last_user_msg = next((m.content for m in reversed(messages) if isinstance(m, HumanMessage)), "")
    is_ko = any(ord(char) > 0x1100 for char in last_user_msg)
    lang_hint = "Korean" if is_ko else "English"
    prompt_messages.append(HumanMessage(content=f"[SYSTEM HINT: Output language must be {lang_hint}]"))
    
    logger.info(f"Invoking Remote Planner ({settings.OLLAMA_MODEL_PLANNER}) with Structured Output")
    start_t = time.time()
    try:
        parsed = structured_llm.invoke(prompt_messages)
        
        # If the model still tries to execute despite having results, and it's a simple list, force plan
        if last_tool_msg and parsed.mode == "execute":
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
        logger.info(f"Final AI Response (Planner): {parsed.assistant_message}")
        
        return {
            "messages": [AIMessage(content=parsed.assistant_message)],
            "planner_response": parsed,
            "mode": parsed.mode,
            "intent_summary": parsed.intent_description,
            "needs_confirmation": parsed.needs_confirmation
        }
    except Exception as e:
        logger.error(f"Planner error: {e}")
        return {"messages": [AIMessage(content=f"Error in planning: {e}")], "mode": "plan"}

def executor_node(state: AgentState, config):
    """Transforms intent into tool calls using Structured Output fallback."""
    intent = state.get("intent_summary") or next((m.content for m in reversed(state["messages"]) if isinstance(m, HumanMessage)), "List my events today")
    messages = state["messages"]
    time_str = f"Current Time(Asia/Seoul): {get_current_time_str()}"
    
    system_prompt = f"""You are a Tool-Calling Expert. Generate the exact tool call for the intent.
{time_str}
Available tools: {[t.name for t in tools]}

CRITICAL RULES FOR ARGUMENTS:
- When a tool requires 'calendar_id', you MUST look up the user-provided calendar name in the 'Calendar Name to ID Mapping' and use the corresponding 'id'.
    - If the name is not in the mapping, use 'primary'.
    - **Verify the ID matches the mapping EXACTLY. Do NOT truncate the domain (e.g., keep '@group.calendar.google.com').**
- 'create_event': Use 'summary' (Title), 'start_time' (ISO), 'end_time' (ISO).
- 'delete_event': Use 'event_id'.
    - **CRITICAL**: 'event_id' is NOT the same as 'calendar_id'.
    - **NEVER** use an email-like string (e.g., '...@group.calendar.google.com') as an 'event_id'.
    - Look for the 'event_id' in the '[RECENTLY CREATED EVENTS]' section if the user refers to "that event" or "the event I just created".
- ALWAYS use 'summary' for the event title, NEVER 'subject' or 'title'.
Intent: {intent}
"""

    profile = memory_service.get_user_profile()
    facts = profile.get("facts", {})
    
    # Fetch available calendars and create a name-to-ID mapping
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
    thread_id = config.get("configurable", {}).get("thread_id", "default")
    recent_events = context_manager.get_recent_events(thread_id)
    recent_events_str = ""
    if recent_events:
         recent_events_str = "\n\n[RECENTLY CREATED EVENTS (Use these IDs for deletion)]:\n" + "\n".join([f"- Title: '{e['summary']}', ID: {e['event_id']}, Created: {e['created_at']}" for e in recent_events])
         system_prompt += recent_events_str

    context_str = f"User Context: {facts}\n\nCalendar Name to ID Mapping: {json.dumps(calendar_name_to_id_map, ensure_ascii=False)}" + recent_events_str

    llm = get_llm(model=settings.OLLAMA_MODEL_PLANNER).with_structured_output(ExecutorResponse)
    prompt = [SystemMessage(content=system_prompt), HumanMessage(content=f"Follow intent: {intent}")]
    
    logger.info("Invoking Remote Executor (27B) - Structured Output...")
    try:
        parsed = llm.invoke(prompt)
        logger.info(f"Executor Decision: {parsed.proposed_action.tool}({parsed.proposed_action.args})")
        # The original code had a return here, but the guardrails and toolcall creation were after it.
        # This implies the return was meant to be after the guardrails.
        # I will keep the guardrails and toolcall creation, and move the return to the end of the function.
    except Exception as e:
        logger.error(f"Executor failed: {e}")
        return {"messages": [AIMessage(content=f"Tool execution failed: {e}")], "mode": "plan"}

    if parsed:
        # --- GUARDRAIL: Fix ID Hallucination (Calendar ID vs Event ID) ---
        if parsed.proposed_action.tool == "delete_event":
            eid = parsed.proposed_action.args.get("event_id", "")
            
            # 1. Triggers: Explicit "Recent" intent or suspicious ID format
            recent_keywords = ["방금", "just", "recent", "금방", "그 일정", "that event"]
            is_recent_intent = any(k in intent.lower() for k in recent_keywords)
            is_suspicious_id = "@" in eid or len(eid) > 50 # Calendar IDs are usually emails
            
            # 2. Action: Force Context Lookup
            if (is_recent_intent or is_suspicious_id) and recent_events:
                corrected_id = recent_events[0]['event_id']
                parsed.proposed_action.args['event_id'] = corrected_id
                
                # Auto-fill calendar_id from context if available
                ctx_cal_id = recent_events[0].get('calendar_id')
                if ctx_cal_id:
                     parsed.proposed_action.args['calendar_id'] = ctx_cal_id
                     logger.info(f"Guardrail auto-filled calendar_id: '{ctx_cal_id}' from context.")
                
                logger.info(f"Guardrail applied. Swapped ID to '{corrected_id}'.")
            
            elif is_suspicious_id and not recent_events:
                 logger.warning(f"Guardrail detected suspicious ID '{eid}' but NO recent events found in context to swap.")
        
        # --- GUARDRAIL: Fix Calendar ID Truncation ---
        if "calendar_id" in parsed.proposed_action.args:
            cal_id = parsed.proposed_action.args["calendar_id"]
            # Check if this ID is valid (exists in map values)
            # We need to flatten the map values to check existence
            valid_ids = list(calendar_name_to_id_map.values())
            if cal_id not in valid_ids and cal_id != "primary":
                # Check for partial match (truncation)
                for full_id in valid_ids:
                    if full_id.startswith(cal_id) and "@" in full_id:
                        parsed.proposed_action.args["calendar_id"] = full_id
                        logger.info(f"Guardrail auto-corrected truncated calendar_id: '{cal_id}' -> '{full_id}'")
                        break
        # -----------------------------------------------------------------

        from langchain_core.messages import ToolCall
        tool_call = ToolCall(
            name=parsed.proposed_action.tool,
            args=parsed.proposed_action.args,
            id="exec_" + str(len(messages)),
        )
        return {"messages": [AIMessage(content="", tool_calls=[tool_call])]}
    else:
        return {"messages": [AIMessage(content="도구 명령을 생성하는 데 실패했습니다.")], "mode": "plan"}

def route_after_router(state: AgentState):
    """Routes based on router's decision."""
    mode = state.get("router_mode")
    if mode == "simple":
        return "executor"
    # Both 'complex' and 'answer' should go through planner for consistency
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
    """Execution node for tools with result logging."""
    tool_node = ToolNode(tools)
    result = tool_node.invoke(state)
    last_message = result["messages"][-1]
    logger.info(f"Tool Execution Result: {str(last_message.content)[:500]}...") # Log first 500 chars

    # --- Context Capture Hook ---
    try:
        if last_message.name == "create_event":
            import json
            content = last_message.content
            # Verify it's a success JSON
            try:
                data = json.loads(content)
                if data.get("status") == "success" and "eventId" in data:
                    thread_id = config.get("configurable", {}).get("thread_id", "default")
                    
                    # Try to get calendar_id from the tool call args
                    calendar_id = "primary"
                    try:
                        # The last message in state is the AIMessage that triggered this tool execution
                        if len(state["messages"]) >= 1:
                             tool_msg = state["messages"][-1]
                             if hasattr(tool_msg, "tool_calls") and tool_msg.tool_calls:
                                 # Assume the first tool call corresponds to this result (simplified)
                                 calendar_id = tool_msg.tool_calls[0]["args"].get("calendar_id", "primary")
                    except Exception as e:
                        logger.warn(f"Failed to extract calendar_id from tool call: {e}")

                    context_manager.add_event(
                        thread_id=thread_id,
                        event_id=data["eventId"],
                        summary=data.get("summary", "Unknown Event"),
                        calendar_id=calendar_id
                    )
            except json.JSONDecodeError:
                pass # Not a JSON response, ignore
    except Exception as e:
        logger.error(f"Context Capture Failed: {e}")
    # ----------------------------

    return result

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

