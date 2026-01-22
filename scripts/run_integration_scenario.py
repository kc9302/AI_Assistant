import json

import httpx


thread_id = "it-scenario-20260122-2"
messages = [
    "안녕",
    "다음 주 수요일에 '팀 점심 식사' 일정을 오후 2시에 '[WS] Inc.' 캘린더에 추가해줘.",
    "오늘 일정 알려줘",
    "방금 등록한 일정 삭제 해줘",
    "우리 숙소 주소랑 체크인 시간 확인해줄래?",
    "오사카 가는 비행기 편명하고 시간 알려줘",
    '''아래 녹취록 정리 좀 해주고, 여기서 정해진 일정들은 전부 내 캘린더에 등록해줘:

"김철수: 자, 다들 오셨나요? 오늘 주간 회의 시작하겠습니다. 벌써 1월 22일이네요. 이영희: 네, 일단 상반기 마케팅 캠페인 계획안부터 좀 볼까요? (중략...) 박지민: 아, 그리고 제가 다음 주 월요일에 홍보 대행사랑 미팅을 잡았어요. 오후 2시쯤 될 것 같은데 제가 주도해서 진행하겠습니다. 김철수: 좋습니다. 그전에 이번 주 금요일 오전 10시에는 우리 팀원들 다 모여서 성과 지표(KPI) 진행 상황을 좀 다시 봐야 할 것 같아요. 이건 필수 참여입니다. 이영희: 알겠습니다. 그럼 다음 달 1일에 진행하기로 한 프로젝트 킥오프 미팅 전까지는 준비가 다 되겠네요. 박지민: 네, 마케팅 계획 검토해서 그때 최종 공유하겠습니다."'''
]


def main() -> None:
    results = []
    with httpx.Client(timeout=240.0) as client:
        for idx, message in enumerate(messages, start=1):
            payload = {"message": message, "thread_id": thread_id}
            print(f"\n[STEP {idx}] {message}")
            try:
                response = client.post("http://127.0.0.1:8000/api/chat", json=payload)
                response.raise_for_status()
                data = response.json()
                results.append(data)
                print(json.dumps(data, ensure_ascii=False, indent=2))
            except Exception as exc:
                err = {"error": str(exc), "step": idx}
                results.append(err)
                print(json.dumps(err, ensure_ascii=False, indent=2))

    print("\n[SUMMARY]")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
