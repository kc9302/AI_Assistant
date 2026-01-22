from datetime import datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except Exception:
    ZoneInfo = None
    ZoneInfoNotFoundError = Exception


def _load_kst():
    if not ZoneInfo:
        return timezone(timedelta(hours=9))
    try:
        return ZoneInfo("Asia/Seoul")
    except ZoneInfoNotFoundError:
        return timezone(timedelta(hours=9))


_KST = _load_kst()


def now_kst() -> datetime:
    return datetime.now(_KST)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)
