from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import Response
from fastapi.responses import JSONResponse
import time
import json
from contextlib import asynccontextmanager
from app.core.settings import settings
from app.core.logging import setup_logging
import logging
from langchain_core.messages import HumanMessage
import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

# Setup Logging
setup_logging()
logger = logging.getLogger(__name__)

# Define lifespan event handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting up...")
    from app.agent.llm import init_models
    import threading
    # Run priming in a separate thread to not block startup
    threading.Thread(target=init_models).start()
    yield
    logger.info("Application shutting down...")

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

# Global Exception Handler to Catch Unhandled Exceptions
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception during request to {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "An internal server error occurred.", "detail": str(exc)},
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response Logging Middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Read request body
    body = await request.body()
    # Replace body in request so it can be read again by the actual route
    async def receive():
        return {"type": "http.request", "body": body}
    request._receive = receive

    # Log request
    try:
        if body:
            parsed_body = json.loads(body)
            logger.info(f">>> REQUEST: {request.method} {request.url.path} Body: {json.dumps(parsed_body, ensure_ascii=False)}")
        else:
            logger.info(f">>> REQUEST: {request.method} {request.url.path} (No Body)")
    except Exception:
        logger.info(f">>> REQUEST: {request.method} {request.url.path} (Body Binary/Raw: {len(body)} bytes)")

    response = await call_next(request)
    
    # Capture response body
    response_body = b""
    async for chunk in response.body_iterator:
        response_body += chunk
    
    # Log response
    duration = time.time() - start_time
    try:
        if response_body:
            parsed_res = json.loads(response_body)
            logger.info(f"<<< RESPONSE: {response.status_code} ({duration:.2f}s) Body: {json.dumps(parsed_res, ensure_ascii=False)}")
        else:
            logger.info(f"<<< RESPONSE: {response.status_code} ({duration:.2f}s) (No Body)")
    except Exception:
        logger.info(f"<<< RESPONSE: {response.status_code} ({duration:.2f}s) (Body Binary/Raw: {len(response_body)} bytes)")

    return Response(content=response_body, status_code=response.status_code, headers=dict(response.headers), media_type=response.media_type)

@app.get("/")
def read_root():
    return {"message": "Welcome to FunctionGemma Agent Backend"}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/status")
def status():
    import requests
    ollama_connected = False
    try:
        # Quick check to see if Ollama is reachable
        # OLLAMA_HOST is typically just the base URL (e.g., http://localhost:11434)
        response = requests.get(settings.OLLAMA_HOST, timeout=2)
        if response.status_code == 200:
            ollama_connected = True
    except:
        ollama_connected = False

    return {
        "status": "ok", 
        "ollama_host": settings.OLLAMA_HOST, 
        "ollama_model": settings.OLLAMA_MODEL,
        "ollama_connected": ollama_connected,
        "google_api_configured": bool(settings.GOOGLE_API_KEY),
        "version": "debug-1-check"
    }

@app.post("/api/chat")
async def chat(body: dict):
    """
    Chat endpoint for the Flutter app.
    Request body: { "messages": [ ... ] } or { "message": "user input" }
    """
    from app.agent.graph import get_graph
    
    # Normalize input
    user_input = body.get("message")
    mode = body.get("mode", "plan")
    thread_id = body.get("thread_id") # Get thread_id from client

    # Auto-generate thread_id if missing (for new sessions)
    if not thread_id:
        import uuid
        thread_id = str(uuid.uuid4())
        logger.info(f"Generated new thread_id: {thread_id}")

    if user_input:
        inputs = {"messages": [HumanMessage(content=user_input)], "mode": mode, "needs_confirmation": False}
    else:
        # Should handle list of messages format too if needed
        return {"error": "Invalid input format. Expected 'message' field."}
        
    # Run the graph
    try:
        config = {"configurable": {"thread_id": thread_id}}
        
        logger.info(f"Invoking graph for thread_id={thread_id}. Message: {user_input[:100]}...")
        
        async with aiosqlite.connect("./checkpoints.db") as conn:
            if not hasattr(conn, "is_alive"):
                conn.is_alive = lambda: True
            checkpointer = AsyncSqliteSaver(conn)
            graph = get_graph(checkpointer=checkpointer)
            final_state = await graph.ainvoke(inputs, config=config)
        
        # Extract the last AI message
        ai_message = final_state["messages"][-1]
        
        # New: Get structured data from state if available (from planner)
        mode = final_state.get("mode", "plan")
        needs_confirmation = final_state.get("needs_confirmation", False)
        
        logger.info(f"Graph execution complete. Model Result -> Mode: {mode}, ConfReq: {needs_confirmation}")
        
        if thread_id:
            from app.services.memory import memory_service, memory_analyzer
            memory_service.save_session(thread_id, final_state["messages"])
            # In a real app, this would be a background task (e.g., FastAPI's BackgroundTasks)
            import asyncio
            asyncio.create_task(memory_analyzer.analyze_and_update(final_state["messages"]))

        logger.info(f"Final Response to Client: {ai_message.content[:200]}...")
        
        return {
            "response": ai_message.content,
            "mode": mode,
            "needs_confirmation": needs_confirmation,
            "thread_id": thread_id,
            "confirmation_id": final_state.get("confirmation_id")
        }
    except Exception as e:
        logger.exception(f"Graph execution failed for thread_id={thread_id}")
        return {"error": str(e)}

@app.post("/api/unload")
async def unload_model():
    """
    Forcefully unloads the LLM from memory by sending a keep-alive of 0.
    """
    try:
        from app.agent.llm import get_llm
        # Invoke with empty prompt and keep_alive=0 to trigger unload
        llm = get_llm(keep_alive="0")
        # Generate a dummy request to trigger the keep-alive setting
        # We use a very simplified call or just access the client if possible.
        # LangChain's ChatOllama doesn't expose a direct 'unload' method, 
        # but invoking it with a specific keep_alive setting updates the model state.
        # We'll use a fast check. However, invoking with "" might return empty string or error.
        # Better approach: Just use requests to hit the Ollama API directly for unload if this fails.
        # But let's try the langchain way first for consistency.
        
        # Actually, simpler: just invoke with a 0 keep_alive.
        llm.invoke("Hi") 
        return {"status": "success", "message": "Model unload instruction sent (processed payload with keep_alive=0)."}
    except Exception as e:
        logger.error(f"Error unloading model: {e}")
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
