import os
import json
import asyncio
import logging
from pathlib import Path
from app.services.memory import memory_analyzer, MemoryService, SESSIONS_DIR
from langchain_core.messages import messages_from_dict

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("DistillHistory")

async def distill_all_sessions():
    """
    Iterates through all session JSON files and runs MemoryAnalyzer on them.
    """
    if not os.path.exists(SESSIONS_DIR):
        logger.error(f"Sessions directory not found: {SESSIONS_DIR}")
        return

    logger.info("Starting batch history distillation...")
    
    # Walk through all subdirectories (dates)
    session_files = []
    for root, dirs, files in os.walk(SESSIONS_DIR):
        for file in files:
            if file.endswith(".json"):
                session_files.append(Path(root) / file)

    logger.info(f"Found {len(session_files)} session files.")

    for session_path in session_files:
        try:
            thread_id = session_path.stem
            logger.info(f"Processing session: {session_path}")
            
            with open(session_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                messages_dict = data.get("messages", [])
                if not messages_dict:
                    logger.warning(f"No messages found in {session_path}. Skipping.")
                    continue
                
                messages = messages_from_dict(messages_dict)
                
                # Manually inject thread_id into the last message's additional_kwargs
                # since the distillation script doesn't have the live context.
                if messages:
                    if not hasattr(messages[-1], "additional_kwargs"):
                        messages[-1].additional_kwargs = {}
                    messages[-1].additional_kwargs["thread_id"] = thread_id
                
                # Run analyzer
                await memory_analyzer.analyze_and_update(messages)
                
        except Exception as e:
            logger.error(f"Failed to process {session_path}: {e}")

    logger.info("Batch distillation complete.")

if __name__ == "__main__":
    asyncio.run(distill_all_sessions())
