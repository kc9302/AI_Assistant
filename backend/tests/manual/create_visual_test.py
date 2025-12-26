import asyncio
import os
import sys

# Add parent directory to sys.path
sys.path.append(os.getcwd())

from app.agent.graph import graph

async def main():
    prompt = "내일 오후 2시에 [Visual Test] Meeting for Browser Verification 제목으로 일정 등록해줘"
    print(f"Executing: {prompt}")
    inputs = {"messages": [("user", prompt)]}
    config = {"configurable": {"thread_id": "visual-test-session"}}
    
    final_state = await graph.ainvoke(inputs, config=config)
    messages = final_state.get("messages", [])
    if messages:
        print(f"AI Response: {messages[-1].content}")

if __name__ == "__main__":
    asyncio.run(main())
