import json
from datetime import datetime, timezone, timedelta

class FunctionGemmaPromptBuilder:
    """
    Builds specialized prompts for the FunctionGemma-270M on-device model.
    Based on Google's research and the 'ondevice' documentation.
    """
    
    @staticmethod
    def get_system_prompt():
        return (
            "You are a model that can do function calling with the following functions.\n"
            "IMPORTANT: When a user refers to a calendar by its name (e.g., '나만보여', '[WS] 근태'), "
            "you MUST use the corresponding calendar ID from the 'list_calendars' tool's output. "
            "Do NOT use the calendar name as the 'calendar_id' in your tool calls."
        )

    @staticmethod
    def get_tool_declarations():
        return [
            {
                "name": "list_calendars",
                "description": "사용자가 접근 가능한 모든 캘린더 목록을 조회할 때 사용한다.",
                "parameters": {"type": "object", "properties": {}}
            },
            {
                "name": "list_today_events",
                "description": "오늘의 일정을 조회할 때 사용한다.",
                "parameters": {"type": "object", "properties": {}}
            },
            {
                "name": "list_events_on_date",
                "description": "특정 날짜의 일정을 조회할 때 사용한다.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string", "description": "조회할 날짜 (YYYY-MM-DD)"}
                    },
                    "required": ["date"]
                }
            },
            {
                "name": "create_event",
                "description": "새로운 일정을 생성할 때 사용한다.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string", "description": "일정 제목"},
                        "start_time": {"type": "string", "description": "시작 시간 (ISO-8601 형식)"},
                        "end_time": {"type": "string", "description": "종료 시간 (ISO-8601 형식). 미지정 시 1시간으로 자동 설정."},
                        "calendar_id": {"type": "string", "description": "일정을 추가할 캘린더의 ID. 모를 경우, 먼저 'list_calendars'를 사용해 ID를 찾아야 한다."},
                        "description": {"type": "string", "description": "일정 설명 (옵션)"},
                        "location": {"type": "string", "description": "일정 장소 (옵션)"}
                    },
                    "required": ["summary", "start_time"]
                }
            },
            {
                "name": "delete_event",
                "description": "기존 일정을 삭제할 때 사용한다. 'event_id'만 사용하거나, 'summary'와 'date'를 함께 사용하여 대상을 특정해야 한다.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "event_id": {"type": "string", "description": "삭제할 이벤트의 고유 ID (옵션)"},
                        "calendar_id": {"type": "string", "description": "이벤트가 속한 캘린더 ID (기본 'primary', 옵션)"},
                        "summary": {"type": "string", "description": "삭제할 이벤트의 제목 (event_id가 없을 경우 사용)"},
                        "date": {"type": "string", "description": "삭제할 이벤트가 있는 날짜 (YYYY-MM-DD 형식, event_id가 없을 경우 사용)"}
                    }
                }
            }
        ]

    @staticmethod
    def get_few_shot_examples():
        # Note: The dates in these examples are relative to a hypothetical 'today' of 2025-12-24.
        return [
            {"user": "내 캘린더 목록 보여줘", "assistant": '{"proposed_action": {"tool": "list_calendars", "args": {}}}'},
            {"user": "오늘 일정 보여줘", "assistant": '{"proposed_action": {"tool": "list_today_events", "args": {}}}'},
            {"user": "내일 오후 3시에 회의 잡아줘", "assistant": '{"proposed_action": {"tool": "create_event", "args": {"summary": "회의", "start_time": "2025-12-25T15:00:00"}}}'},
            {"user": "내일 오후 4시에 [WS] Inc 캘린더에 회의 일정 등록", "assistant": '{"proposed_action": {"tool": "create_event", "args": {"summary": "회의", "start_time": "2025-12-25T16:00:00", "calendar_id": "ws_inc_id_example"}}}'},
            {"user": "어제 했던 '주간 보고' 일정 삭제해줘", "assistant": '{"proposed_action": {"tool": "delete_event", "args": {"summary": "주간 보고", "date": "2025-12-23"}}}'}
        ]

    @classmethod
    def build_chat_prompt(cls, user_input: str, time_str: str = "", context: str = ""):
        """
        Assembles a full chat prompt string in the format expected by FunctionGemma.
        """
        system = cls.get_system_prompt()
        tools = json.dumps(cls.get_tool_declarations(), ensure_ascii=False)
        examples = cls.get_few_shot_examples()
        
        prompt = f"<|system|>\n{system}\n{tools}\n\n{time_str}\n{context}\n\nRespond ONLY in JSON conforming to the schema.<|end|>\n"
        
        # Add examples
        for ex in examples:
            prompt += f"<|user|>\n{ex['user']}<|end|>\n<|assistant|>\n{ex['assistant']}<|end|>\n"
            
        # Add the actual request
        prompt += f"<|user|>\n{user_input}<|end|>\n<|assistant|>\n"
        
        return prompt

    @classmethod
    def build_router_prompt(cls, user_input: str, time_str: str = "", context: str = ""):
        """
        Specialized prompt for routing decisions using FunctionGemma.
        """
        system = "You are a Router. Categorize the user request into 'simple', 'complex', or 'answer'."
        prompt = f"<|system|>\n{system}\n{time_str}\n{context}\n\nRespond ONLY in JSON: {{\"mode\": \"simple\"|\"complex\"|\"answer\", \"reasoning\": \"...\"}}<|end|>\n"
        
        # Minimal examples for small model
        prompt += "<|user|>\n오늘 일정 뭐야?<|end|>\n<|assistant|>\n{\"mode\": \"simple\", \"reasoning\": \"Simple list request\"}<|end|>\n"
        prompt += "<|user|>\n내 캘린더 목록 보여줘<|end|>\n<|assistant|>\n{\"mode\": \"simple\", \"reasoning\": \"Simple list request for calendars\"}<|end|>\n"
        prompt += "<|user|>\n다음 주 일정 확인해서 테니스 레슨 빈 시간 찾아줘<|end|>\n<|assistant|>\n{\"mode\": \"complex\", \"reasoning\": \"Requires reasoning and schedule analysis\"}<|end|>\n"
        
        prompt += f"<|user|>\n{user_input}<|end|>\n<|assistant|>\n"
        return prompt
