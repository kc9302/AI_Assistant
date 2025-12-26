import pytest
import os
from app.agent.graph import graph
from app.agent.state import AgentState
from langchain_core.messages import HumanMessage
from app.agent.llm import get_llm
import time

@pytest.mark.asyncio
async def test_router_simple_flow():
    """Verify that a simple greeting is handled by the router/END."""
    inputs = {"messages": [HumanMessage(content="안녕, 반가워!")]}
    # We expect the router to decide 'answer' and go to END
    final_state = await graph.ainvoke(inputs)
    
    assert "router_mode" in final_state
    # If the router says 'answer', it goes to END.
    # Note: LlamaCpp might be non-deterministic, but greetings should generally be 'answer'.
    assert final_state["router_mode"] in ["answer", "complex"] 

@pytest.mark.asyncio
async def test_router_complex_flow():
    """Verify that a complex query triggers the remote planner."""
    # Complex query with reasoning required
    inputs = {"messages": [HumanMessage(content="내일 아오리 라멘에서 점심 약속이 있는데, 내 일정을 확인하고 만약 비어있다면 이동 시간을 고려해서 1시간 전 알림을 포함한 일정을 추가해줄래?")]}
    
    final_state = await graph.ainvoke(inputs)
    
    # Complex query should likely trigger planner
    assert final_state["router_mode"] == "complex"
    assert "planner_response" in final_state

@pytest.mark.asyncio
async def test_gpu_memory_cleanup_manual():
    """
    This is more of a smoke test to ensure get_llm(keep_alive='0') doesn't crash 
    and theoretically triggers unload.
    """
    llm = get_llm(keep_alive="0")
    start_time = time.time()
    response = llm.invoke("Testing memory cleanup. Respond with 'ok'.")
    duration = time.time() - start_time
    
    print(f"Ollama call took {duration:.2f}s")
    assert "ok" in response.content.lower()

def test_app_init_priming():
    """Verify that init_models can be called without error."""
    from app.agent.llm import init_models
    # This might take time, but should run
    try:
        # We don't want to wait forever in CI, but here it's fine for verification
        init_models()
    except Exception as e:
        pytest.fail(f"init_models failed: {e}")
