import re
import logging

logger = logging.getLogger(__name__)

def extract_json(text: str) -> str:
    """Finds the first '{' and last '}' and returns the substring."""
    if not text:
        return ""
    text = text.strip()
    
    # Try to cut off anything after the first complete JSON object
    match_all = re.finditer(r"({.*})", text, re.DOTALL)
    best_candidate = text
    for m in match_all:
        candidate = m.group(1).strip()
        if candidate.count("{") == candidate.count("}"):
            best_candidate = candidate
            break

    match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", best_candidate, re.DOTALL)
    if match:
        return match.group(1).strip()
    
    start = best_candidate.find("{")
    end = best_candidate.rfind("}")
    if start != -1 and end != -1:
        return best_candidate[start:end+1].strip()
    return best_candidate
