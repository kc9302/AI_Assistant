import re
import logging

logger = logging.getLogger(__name__)

def extract_json(text: str) -> str:
    """Finds the first '{' and last '}' and returns the substring."""
    if not text:
        return ""
    text = text.strip()

    match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Try to cut off anything after the first complete JSON object
    match_all = re.finditer(r"({.*})", text, re.DOTALL)
    for m in match_all:
        candidate = m.group(1).strip()
        if candidate.count("{") == candidate.count("}"):
            return candidate

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start:end+1].strip()
    return ""
