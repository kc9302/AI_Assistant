from langchain_core.tools import tool
from app.core.google_auth import get_calendar_service
from datetime import datetime, timedelta, timezone
import json
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

def _get_selected_calendars(service) -> List[Dict[str, str]]:
    """사용자가 관리(쓰기 이상)할 수 있는 캘린더 목록을 반환합니다."""
    try:
        calendar_list = service.calendarList().list(minAccessRole='reader').execute()
        owned_and_writer_calendars = []
        for item in calendar_list.get('items', []):
            # 'owner' 또는 'writer' 권한이 있는 캘린더만 필터링
            if item.get('accessRole') in ['owner', 'writer']:
                owned_and_writer_calendars.append({
                    'id': item['id'],
                    'summary': item.get('summary', 'No Title')
                })
        
        # 관리 가능한 캘린더가 없으면 primary를 기본값으로 사용
        return owned_and_writer_calendars if owned_and_writer_calendars else [{'id': 'primary', 'summary': 'Primary'}]
    except Exception as e:
        logger.error(f"[CALENDAR] 캘린더 목록 조회 실패: {e}")
        return [{'id': 'primary', 'summary': 'Primary'}]

def _fetch_events_from_calendars(
    service,
    calendars: List[Dict[str, str]],
    time_min: str,
    time_max: Optional[str] = None,
    max_results: int = 250
) -> List[Dict[str, Any]]:
    """여러 캘린더에서 일정을 조회하고 병합"""
    all_events = []
    
    for cal in calendars:
        try:
            kwargs = {
                "calendarId": cal['id'],
                "timeMin": time_min,
                "singleEvents": True,
                "orderBy": "startTime",
                "maxResults": max_results,
            }
            if time_max:
                kwargs["timeMax"] = time_max
                
            events_result = service.events().list(**kwargs).execute()
            items = events_result.get("items", [])
            
            # 각 이벤트에 캘린더 정보 추가
            for item in items:
                item["_calendarName"] = cal['summary']
                
            all_events.extend(items)
        except Exception as e:
            logger.error(f"[CALENDAR] {cal['summary']} 조회 실패: {e}")
            continue

    # 시간순 정렬
    all_events.sort(key=lambda x: x.get("start", {}).get("dateTime") or x.get("start", {}).get("date") or "")
    return all_events

def _format_events(events: List[Dict[str, Any]], empty_message: str, label: Optional[str] = None) -> str:
    """이벤트 목록을 보기 좋은 문자열로 변환"""
    if not events:
        return empty_message

    lines = []
    if label:
        lines.append(f"--- {label} ---")
        
    for ev in events:
        start = ev["start"].get("dateTime") or ev["start"].get("date")
        summary = ev.get("summary", "(제목 없음)")
        cal_name = ev.get("_calendarName", "")
        location = ev.get("location", "")
        
        # ISO 형식에서 시간 부분만 간단히 추출 (선택 사항)
        # 예: 2025-12-24T10:00:00+09:00 -> 10:00
        display_time = start
        if 'T' in start:
            try:
                dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                display_time = dt.strftime('%Y-%m-%d %H:%M')
            except:
                pass
        
        line = f"- {display_time} | {summary}"
        if cal_name:
            line += f" ({cal_name})"
        if location:
            line += f" @ {location}"
        lines.append(line)

    return "\n".join(lines)

@tool
def list_calendars() -> str:
    """사용자의 Google Calendar 목록을 조회합니다."""
    service = get_calendar_service()
    if not service: return "Google Calendar 인증에 실패했습니다."
    
    calendars = _get_selected_calendars(service)
    lines = [f"- {cal['summary']} (ID: {cal['id']})" for cal in calendars]
    return "선택된 캘린더 목록:\n" + "\n".join(lines)

@tool
def list_today_events(calendar_id: Optional[str] = None) -> str:
    """
    오늘 일정을 조회합니다.
    Args:
        calendar_id: 특정 캘린더 ID만 조회할 경우 사용 (기본값 None이면 선택된 모든 캘린더 조회)
    """
    service = get_calendar_service()
    if not service: return "Google Calendar 인증에 실패했습니다."
    
    if calendar_id:
        calendars = [{'id': calendar_id, 'summary': f'ID: {calendar_id}'}]
    else:
        calendars = _get_selected_calendars(service)
        
    kst = timezone(timedelta(hours=9))
    now_kst = datetime.now(kst)
    start = now_kst.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    
    events = _fetch_events_from_calendars(
        service=service,
        calendars=calendars,
        time_min=start.isoformat(),
        time_max=end.isoformat()
    )
    
    label = f"캘린더({calendar_id})" if calendar_id else "선택된 모든 캘린더"
    return _format_events(events, f"오늘 {label}에 등록된 일정이 없습니다.", label)

@tool
def list_events_on_date(date: str, calendar_id: Optional[str] = None) -> str:
    """
    특정 날짜의 일정을 조회합니다.
    Args:
        date: 조회할 날짜 (YYYY-MM-DD 형식, 예: '2025-12-25')
        calendar_id: 특정 캘린더 ID만 조회할 경우 사용
    """
    service = get_calendar_service()
    if not service: return "Google Calendar 인증에 실패했습니다."
    
    if calendar_id:
        calendars = [{'id': calendar_id, 'summary': f'ID: {calendar_id}'}]
    else:
        calendars = _get_selected_calendars(service)

    try:
        kst = timezone(timedelta(hours=9))
        target_date = datetime.strptime(date, "%Y-%m-%d")
        start = datetime(target_date.year, target_date.month, target_date.day, tzinfo=kst)
        end = start + timedelta(days=1)
    except Exception:
        return "날짜 형식이 올바르지 않습니다. 'YYYY-MM-DD' 형식으로 입력해주세요."
    
    events = _fetch_events_from_calendars(
        service=service,
        calendars=calendars,
        time_min=start.isoformat(),
        time_max=end.isoformat()
    )
    
    label = f"캘린더({calendar_id})" if calendar_id else "선택된 모든 캘린더"
    return _format_events(events, f"{date}의 {label}에는 일정이 없습니다.", label)

@tool
def list_upcoming_events(max_results: int = 10, calendar_id: Optional[str] = None) -> str:
    """
    다가오는 일정을 조회합니다.
    Args:
        max_results: 가져올 최대 일정 개수 (기본 10)
        calendar_id: 특정 캘린더 ID만 조회할 경우 사용
    """
    service = get_calendar_service()
    if not service: return "Google Calendar 인증에 실패했습니다."
    
    if calendar_id:
        calendars = [{'id': calendar_id, 'summary': f'ID: {calendar_id}'}]
    else:
        calendars = _get_selected_calendars(service)

    now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    
    events = _fetch_events_from_calendars(
        service=service,
        calendars=calendars,
        time_min=now,
        max_results=max_results
    )
    
    label = f"캘린더({calendar_id})" if calendar_id else "선택된 모든 캘린더"
    return _format_events(events[:max_results], "다가올 일정이 없습니다.", label)

@tool
def list_weekly_events(calendar_id: Optional[str] = None) -> str:
    """
    이번 주(오늘부터 7일간)의 일정을 조회합니다.
    Args:
        calendar_id: 특정 캘린더 ID만 조회할 경우 사용
    """
    service = get_calendar_service()
    if not service: return "Google Calendar 인증에 실패했습니다."
    
    if calendar_id:
        calendars = [{'id': calendar_id, 'summary': f'ID: {calendar_id}'}]
    else:
        calendars = _get_selected_calendars(service)
        
    kst = timezone(timedelta(hours=9))
    start = datetime.now(kst).replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=7)
    
    events = _fetch_events_from_calendars(
        service=service,
        calendars=calendars,
        time_min=start.isoformat(),
        time_max=end.isoformat()
    )
    
    label = f"캘린더({calendar_id})" if calendar_id else "선택된 모든 캘린더"
    return _format_events(events, f"이번 주 {label}에 예정된 일정이 없습니다.", label)

@tool
def create_event(
    summary: str,
    start_time: str,
    end_time: Optional[str] = None,
    calendar_id: str = "primary",
    description: str = "",
    location: str = ""
) -> str:
    """
    새로운 일정을 생성합니다.
    Args:
        summary: 일정 제목
        start_time: 시작 시간 (ISO 형식, 예: '2025-12-24T15:00:00')
        end_time: 종료 시간 (ISO 형식, 예: '2025-12-24T16:00:00'). 미지정 시 1시간으로 자동 설정.
        calendar_id: 저장할 캘린더 ID (기본 'primary')
        description: 일정 설명 (옵션)
        location: 장소 (옵션)
    """
    service = get_calendar_service()
    if not service: return "Google Calendar 인증에 실패했습니다."
    
    try:
        # 종료 시간이 없으면 시작 시간 + 1시간으로 설정
        if not end_time:
            try:
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                end_dt = start_dt + timedelta(hours=1)
                end_time = end_dt.isoformat()
            except ValueError:
                return f"❌ 시작 시간({start_time}) 형식이 잘못되었습니다. ISO 형식을 사용해주세요."

        event = {
            'summary': summary,
            'start': {'dateTime': start_time, 'timeZone': 'Asia/Seoul'},
            'end': {'dateTime': end_time, 'timeZone': 'Asia/Seoul'},
        }
        if description: event['description'] = description
        if location: event['location'] = location
        
        created_event = service.events().insert(calendarId=calendar_id, body=event).execute()
        return json.dumps({"status": "success", "summary": summary, "htmlLink": created_event.get('htmlLink'), "eventId": created_event.get('id')})
    except Exception as e:
        return f"❌ 일정 생성 중 오류 발생: {str(e)}"

@tool
def delete_event(
    event_id: Optional[str] = None, 
    calendar_id: str = "primary", 
    summary: Optional[str] = None, 
    date: Optional[str] = None
) -> str:
    """
    일정을 삭제합니다. event_id 또는 summary와 date를 사용하여 대상을 특정합니다.
    Args:
        event_id: 삭제할 이벤트의 고유 ID (옵션)
        calendar_id: 해당 이벤트가 속한 캘린더 ID (기본 'primary')
        summary: 삭제할 이벤트의 제목 (event_id가 없을 때 필요, 옵션)
        date: 삭제할 이벤트가 있는 날짜 (YYYY-MM-DD 형식, event_id가 없을 때 필요, 옵션)
    """
    service = get_calendar_service()
    if not service:
        return "Google Calendar 인증에 실패했습니다."

    if not event_id:
        if not summary or not date:
            return "❌ 일정을 삭제하려면 `event_id` 또는 `summary`와 `date`가 필요합니다."

        try:
            kst = timezone(timedelta(hours=9))
            target_date = datetime.strptime(date, "%Y-%m-%d")
            time_min = datetime(target_date.year, target_date.month, target_date.day, tzinfo=kst).isoformat()
            time_max = (datetime(target_date.year, target_date.month, target_date.day, tzinfo=kst) + timedelta(days=1)).isoformat()
        except ValueError:
            return f"❌ 날짜 형식이 올바르지 않습니다. '{date}'는 'YYYY-MM-DD' 형식이어야 합니다."

        try:
            events_result = service.events().list(
                calendarId=calendar_id,
                q=summary,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True
            ).execute()
            
            found_events = events_result.get('items', [])

            if not found_events:
                return f"❌ '{date}'에 '{summary}'라는 제목의 일정을 찾을 수 없습니다."
            
            if len(found_events) > 1:
                event_infos = [
                    f"- 제목: {event.get('summary', '(제목 없음)')}, 시작: {event['start'].get('dateTime') or event['start'].get('date')}, ID: {event['id']}"
                    for event in found_events
                ]
                return f"🤔 여러 개의 일정이 발견되었습니다. 어떤 일정을 삭제하시겠습니까?\n" + "\n".join(event_infos)
            
            event_id = found_events[0]['id']
            logging.info(f"일정 검색 성공: '{summary}' -> event_id: {event_id}")

        except Exception as e:
            logging.error(f"일정 검색 중 오류 발생: {e}")
            return f"❌ 일정 검색 중 오류가 발생했습니다: {e}"

    try:
        logging.info(f"캘린더({calendar_id})에서 이벤트({event_id}) 삭제 시도...")
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        return f"✓ 일정(ID: {event_id})이 성공적으로 삭제되었습니다."
    except Exception as e:
        logging.error(f"일정 삭제({event_id}) 실패: {e}")
        return f"❌ 일정 삭제 중 오류가 발생했습니다: {e}"

@tool
def get_event(event_id: str, calendar_id: str = "primary") -> str:
    """
    특정 이벤트 ID를 사용하여 단일 일정을 조회합니다.
    Args:
        event_id: 조회할 이벤트의 고유 ID
        calendar_id: 해당 이벤트가 속한 캘린더 ID (기본 'primary')
    """
    service = get_calendar_service()
    if not service:
        return json.dumps({"status": "error", "message": "Google Calendar 인증에 실패했습니다."})

    try:
        event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        # Return key details as JSON
        return json.dumps({
            "status": "success",
            "eventId": event.get('id'),
            "summary": event.get('summary', '(제목 없음)'),
            "start": event['start'].get('dateTime') or event['start'].get('date'),
            "end": event['end'].get('dateTime') or event['end'].get('date'),
            "location": event.get('location', ''),
            "description": event.get('description', ''),
            "htmlLink": event.get('htmlLink')
        })
    except Exception as e:
        logger.error(f"일정 조회(ID: {event_id}) 실패: {e}")
        return json.dumps({"status": "error", "message": f"❌ 일정 조회 중 오류 발생: {str(e)}"})
