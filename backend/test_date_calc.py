from datetime import datetime, timedelta, timezone

kst = timezone(timedelta(hours=9))
now = datetime.now(kst)

# Calculate next week's Monday
days_until_next_monday = (7 - now.weekday()) if now.weekday() != 0 else 7
next_monday = now + timedelta(days=days_until_next_monday)

print(f"현재 시각: {now.strftime('%Y-%m-%d %H:%M (%A)')}")
print(f"현재 요일 번호: {now.weekday()} (0=Monday, 6=Sunday)")
print(f"\n다음 주:")
print(f"  월요일: {next_monday.strftime('%Y-%m-%d')}")
print(f"  화요일: {(next_monday + timedelta(days=1)).strftime('%Y-%m-%d')}")
print(f"  수요일: {(next_monday + timedelta(days=2)).strftime('%Y-%m-%d')}")
print(f"  목요일: {(next_monday + timedelta(days=3)).strftime('%Y-%m-%d')}")
print(f"  금요일: {(next_monday + timedelta(days=4)).strftime('%Y-%m-%d')}")
print(f"  토요일: {(next_monday + timedelta(days=5)).strftime('%Y-%m-%d')}")
print(f"  일요일: {(next_monday + timedelta(days=6)).strftime('%Y-%m-%d')}")

print(f"\n✅ 테스트: '다음 주 수요일'은 {(next_monday + timedelta(days=2)).strftime('%Y-%m-%d')}이어야 합니다.")
