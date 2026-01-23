import os
import sys
import asyncio
from typing import Literal
from pydantic import BaseModel, Field

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

# Mock settings
os.environ["LLM_BASE_URL"] = "http://192.168.0.100:11434"
os.environ["LLM_MODEL"] = "gpt-oss-safeguard"

from langchain_ollama import ChatOllama

class TestResponse(BaseModel):
    mood: Literal["happy", "sad"] = Field(description="The mood of the text")
    reason: str = Field(description="Why this mood was chosen")

async def test_structured_output():
    print(f"Testing with_structured_output on {os.environ['LLM_MODEL']}...")
    llm = ChatOllama(
        base_url=os.environ["LLM_BASE_URL"],
        model=os.environ["LLM_MODEL"],
        temperature=0
    )
    
    try:
        # Attempt to create structured LLM
        structured_llm = llm.with_structured_output(TestResponse)
        print("✅ SUCCESS: structured_llm created.")
        
        print("Invoking structured LLM...")
        try:
            result = await structured_llm.ainvoke("I am having a wonderful day!")
            print(f"✅ SUCCESS: Result: {result}")
        except Exception as e:
            print(f"❌ FAILED during invoke: {e}")
            
    except Exception as e:
        print(f"❌ FAILED to create structured_llm: {e}")

if __name__ == "__main__":
    asyncio.run(test_structured_output())
