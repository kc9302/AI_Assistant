from langchain_core.tools import tool
from app.core.google_auth import get_calendar_service
from datetime import datetime, timedelta, timezone
import json
import logging
from typing import List, Dict, Any, Optional
from app.core.datetime_utils import now_utc

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
def list_events(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    calendar_id: Optional[str] = None,
    max_results: int = 50
) -> str:
    """
    일정 목록을 조회합니다. 날짜 범위를 지정하여 특정 기간의 일지만 가져올 수 있습니다.
    Args:
        start_date: 시작 날짜 (YYYY-MM-DD 형식). 미지정 시 오늘 기준.
        end_date: 종료 날짜 (YYYY-MM-DD 형식). 미지정 시 시작 날짜의 다음날(즉, 해당 일자 하루) 조회.
        calendar_id: 특정 캘린더 ID만 조회할 경우 사용.
        max_results: 가져올 최대 일정 개수 (기본 50).
    """
    service = get_calendar_service()
    if not service: return "Google Calendar 인증에 실패했습니다."
    
    if calendar_id:
        calendars = [{'id': calendar_id, 'summary': f'ID: {calendar_id}'}]
    else:
        calendars = _get_selected_calendars(service)
        
    kst = timezone(timedelta(hours=9))
    
    try:
        if start_date:
             s_dt = datetime.strptime(start_date, "%Y-%m-%d")
             start = datetime(s_dt.year, s_dt.month, s_dt.day, tzinfo=kst)
        else:
             start = datetime.now(kst).replace(hour=0, minute=0, second=0, microsecond=0)
             start_date = start.strftime("%Y-%m-%d")
             
        if end_date:
             e_dt = datetime.strptime(end_date, "%Y-%m-%d")
             # Strict Boundary: If end_date is provided, we set it to the very start of that day (00:00:00)
             # This means list_events(start='2024-01-01', end='2024-01-02') will ONLY show Jan 1st events.
             end = datetime(e_dt.year, e_dt.month, e_dt.day, tzinfo=kst)
        else:
             # Default to 1 day range if only start_date is given or both are None
             end = start + timedelta(days=1)
             end_date = end.strftime("%Y-%m-%d")
             
    except Exception:
        return "날짜 형식이 올바르지 않습니다. 'YYYY-MM-DD' 형식으로 입력해주세요."
    
    events = _fetch_events_from_calendars(
        service=service,
        calendars=calendars,
        time_min=start.isoformat(),
        time_max=end.isoformat(),
        max_results=max_results
    )
    
    # FILTERING: If it's a single day request (end_date = start_date + 1 day),
    # explicitly filter list items to match the starting date to avoid edge-case leakage.
    is_single_day = False
    try:
        if (end - start).days == 1:
            is_single_day = True
    except:
        pass

    if is_single_day:
        filtered_events = []
        for ev in events:
            ev_start = ev["start"].get("dateTime") or ev["start"].get("date")
            if ev_start.startswith(start_date):
                filtered_events.append(ev)
        events = filtered_events

    date_range_str = f"{start_date}"
    if end_date and end_date != (start + timedelta(days=1)).strftime("%Y-%m-%d"):
        # Show range only if it's more than 1 day
        date_range_str += f" ~ {end_date}"
        
    label = f"캘린더({calendar_id})" if calendar_id else "선택된 모든 캘린더"
    empty_msg = f"{date_range_str} 기간에 {label}에 등록된 일정이 없습니다."
    
    return _format_events(events, empty_msg, label)

@tool
def create_event(
    summary: str,
    start_time: str,
    end_time: Optional[str] = None,
    calendar_id: str = "primary",
    description: str = "",
    location: str = "",
    thread_id: Optional[str] = None
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
        thread_id: 세션 추적용 ID (옵션)
    """
    if thread_id:
        verification_tag = f"\n\n[ThreadID: {thread_id}]"
        description = (description + verification_tag).strip()
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

        # Expert Recommendation: Check for duplicates before creation
        # Look for events with same summary and start time on the target calendar
        try:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            # If naïve, assume KST (since user is in Korea context)
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=timezone(timedelta(hours=9)))
            
            # Format to RFC3339 with 'Z' as expected by Google API often, or keep offset
            check_start = (start_dt - timedelta(minutes=1)).isoformat()
            check_end = (start_dt + timedelta(minutes=1)).isoformat()

            # Ensure 'Z' format if offset is +00:00, otherwise keep offset
            if check_start.endswith("+00:00"): check_start = check_start.replace("+00:00", "Z")
            if check_end.endswith("+00:00"): check_end = check_end.replace("+00:00", "Z")

            existing_events = service.events().list(
                calendarId=calendar_id,
                timeMin=check_start,
                timeMax=check_end,
                singleEvents=True,
                q=summary
            ).execute().get('items', [])
            
            for e in existing_events:
                if e.get('summary') == summary:
                    e_start = e.get('start', {}).get('dateTime') or e.get('start', {}).get('date')
                    # Simple check: string match or logic match
                    if e_start and (e_start.startswith(start_time) or start_time in e_start):
                         logger.info(f"Duplicate event detected: '{summary}' at {start_time} already exists on {calendar_id}.")
                         return f"⚠️ 이미 동일한 일정('{summary}')이 해당 시간대에 존재합니다. 중복 등록을 방지했습니다."
        except Exception as e:
            logger.warning(f"Duplicate check failed (Safe Fail): {e}")
            # Proceed to create event even if check fails

        event = {
            'summary': summary,
            'start': {'dateTime': start_time, 'timeZone': 'Asia/Seoul'},
            'end': {'dateTime': end_time, 'timeZone': 'Asia/Seoul'},
        }
        if description: event['description'] = description
        if location: event['location'] = location
        
        created_event = service.events().insert(calendarId=calendar_id, body=event).execute()
        event_id = created_event.get('id')
        
        # Immediate verification call to ensure it's on Google server
        try:
            # 1. Direct ID verification
            verified_event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
            
            # 2. Deep verification: Search for the thread_id tag in recent events to ensure sync
            is_deep_verified = False
            if thread_id and verified_event:
                # Search specifically for the tag in the last hour's events
                time_min = (now_utc() - timedelta(hours=1)).isoformat().replace("+00:00", "Z")
                search_res = service.events().list(
                    calendarId=calendar_id, 
                    q=thread_id, 
                    timeMin=time_min,
                    singleEvents=True
                ).execute()
                
                found_events = search_res.get('items', [])
                if any(e.get('id') == event_id for e in found_events):
                    is_deep_verified = True
                    logger.info(f"Deep Verified: Event {event_id} found in search with ThreadID tag.")

            if verified_event:
                logger.info(f"Verified event '{summary}' (ID: {event_id}) on calendar '{calendar_id}'")
                return json.dumps({
                    "status": "success", 
                    "verified": True,
                    "deep_verified": is_deep_verified,
                    "summary": summary, 
                    "calendar_id": calendar_id,
                    "htmlLink": created_event.get('htmlLink'), 
                    "eventId": event_id
                }, ensure_ascii=False)
        except Exception as v_err:
            logger.warning(f"Immediate verification failed for event {event_id}: {v_err}")

        return json.dumps({
            "status": "success", 
            "verified": False,
            "summary": summary, 
            "calendar_id": calendar_id,
            "htmlLink": created_event.get('htmlLink'), 
            "eventId": event_id
        }, ensure_ascii=False)
    except Exception as e:
        return f"❌ 일정 생성 중 오류 발생: {str(e)}"

@tool
def delete_event(
    event_id: Optional[str] = None, 
    calendar_id: str = "primary", 
    summary: Optional[str] = None, 
    date: Optional[str] = None,
    thread_id: Optional[str] = None
) -> str:
    """
    일정을 삭제합니다. event_id 또는 summary와 date를 사용하여 대상을 특정합니다.
    Args:
        event_id: 삭제할 이벤트의 고유 ID (옵션)
        calendar_id: 해당 이벤트가 속한 캘린더 ID (기본 'primary')
        summary: 삭제할 이벤트의 제목 (event_id가 없을 때 필요, 옵션)
        date: 삭제할 이벤트가 있는 날짜 (YYYY-MM-DD 형식, event_id가 없을 때 필요, 옵션)
        thread_id: 특정 세션에서 생성된 일정을 찾아 삭제할 때 사용 (옵션)
    """
    service = get_calendar_service()
    if not service:
        return "Google Calendar 인증에 실패했습니다."

    # If neither ID nor Search params provided, but thread_id exists, try to find by tag
    if not event_id and not (summary and date) and thread_id:
        try:
            logger.info(f"Searching for most recent event with thread_id tag: {thread_id}")
            # Search last 12 hours for the tag
            time_min = (now_utc() - timedelta(hours=12)).isoformat().replace("+00:00", "Z")
            search_res = service.events().list(
                calendarId=calendar_id, 
                q=thread_id, 
                timeMin=time_min,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            items = search_res.get('items', [])
            if items:
                # Take the last one (most recent)
                latest = items[-1]
                event_id = latest['id']
                summary = latest.get('summary', 'Unknown')
                logger.info(f"Found event '{summary}' with tag {thread_id} via search.")
            else:
                return f"❌ 세션({thread_id}) 관련 등록된 일정을 찾을 수 없습니다."
        except Exception as e:
            logger.error(f"Search by thread_id failed: {e}")

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

@tool
def verify_calendar_registrations(thread_id: str) -> str:
    """
    구글 서버에 해당 ThreadID 태그가 달린 일정이 실제로 동기화되었는지 검증합니다.
    (등록 성공 리포트를 받았으나 캘린더에서 보이지 않을 때 사용)
    """
    service = get_calendar_service()
    if not service:
        return json.dumps({"status": "error", "message": "Google Calendar 인증에 실패했습니다."})
    
    calendars = _get_selected_calendars(service)
    results = []
    
    # 최근 1시간 내의 일정을 검색 (ThreadID 태그 포함)
    kst = timezone(timedelta(hours=9))
    time_min = (datetime.now(kst) - timedelta(hours=1)).isoformat()
    query = f"[ThreadID: {thread_id}]"
    
    for cal in calendars:
        try:
            res = service.events().list(
                calendarId=cal['id'],
                q=query,
                timeMin=time_min,
                singleEvents=True
            ).execute()
            
            items = res.get('items', [])
            for item in items:
                results.append({
                    "summary": item.get('summary'),
                    "calendar": cal.get('summary', 'Unknown'),
                    "status": "Deep Verified",
                    "id": item.get('id')
                })
        except Exception as e:
            logger.error(f"검증 중 캘린더({cal['id']}) 에러: {e}")
            continue
            
    return json.dumps({"status": "success", "results": results}, ensure_ascii=False)
