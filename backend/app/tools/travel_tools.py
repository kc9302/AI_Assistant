from typing import List, Dict, Any
import os
from langchain_core.tools import tool
from app.services.travel import travel_knowledge_service, KNOWLEDGE_DIR

@tool
def search_travel_info(query: str = None, destination: str = None, location: str = None) -> str:
    """
    관련이 있는 여행 정보(일정, 숙소, 맛집 등)를 검색합니다.
    오사카 여행 계획이나 예약 정보가 필요할 때 유용합니다.
    """
    # LLM might use 'destination' or 'location' as kwarg instead of 'query'
    search_query = query or destination or location
    if not search_query:
        return "검색어를 입력해주세요. (예: '비행기 시간', '호텔 주소')"

    text = (search_query or "").lower()
    wants_logistics = any(
        k in text
        for k in (
            "flight", "airline", "ticket", "boarding", "gate", "itinerary",
            "항공", "비행", "항공편", "편명", "탑승", "게이트", "예약번호",
            "hotel", "숙소", "호텔", "주소", "체크인", "체크아웃",
        )
    )
    source_filter = None
    if wants_logistics:
        source_filter = os.path.normpath(os.path.join(KNOWLEDGE_DIR, "logistics.md"))

    results = travel_knowledge_service.search(search_query, k=5, source_filter=source_filter)
    if not results:
        return f"'{search_query}'에 대한 검색 결과가 없습니다."
        
    formatted = []
    for i, res in enumerate(results):
        formatted.append(f"[{i+1}] {res['content']}\n(출처: {res['metadata'].get('source', '알 수 없음')})")
        
    return "\n\n".join(formatted)

travel_tools = [search_travel_info]
