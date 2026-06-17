# src/agentic/tutor_memories.py
import uuid
import json
from sqlalchemy import text as sa_text
from language_tutor.tools.database_manager import engine

# Static Namespace UUID used to isolate your conversational session logs
SESSION_UUID = str(uuid.uuid5(uuid.NAMESPACE_DNS, "user_session_universal_001"))

def fetch_chat_history(num_messages: int = 5) -> str:
    """
    Retrieves the last persistent conversation turns from long-term memory.
    Pure-Python implementation completely free of smolagents decorators.
    """
    try:
        with engine.connect() as conn:
            # Select past rows ordered descending to get the newest, then reverse to read chronologically
            result = conn.execute(sa_text("""
                SELECT message FROM chat_history 
                WHERE session_id = :session_id 
                ORDER BY id DESC 
                LIMIT :limit
            """), {"session_id": SESSION_UUID, "limit": num_messages * 2})
            
            rows = result.fetchall()
            if not rows:
                return "Long-term chat history database is currently empty for this session."
                
            history_blocks = []
            for row in rows[::-1]:
                try:
                    # Handle both pre-parsed strings and raw database json rows cleanly
                    msg_data = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                    inner_data = msg_data.get("data", {})
                    role = inner_data.get("type", "unknown").upper()
                    content = inner_data.get("content", "")
                    history_blocks.append(f"[{role}]: {content}")
                except Exception:
                    continue
                    
            return "\n".join(history_blocks)
    except Exception as e:
        return f"Database Error reading chat history: {str(e)}"

def save_chat_turn_to_db(role: str, content: str):
    """Internal utility to push a new conversational turn into long-term storage."""
    try:
        # Formats text payload to match your standard app schema layout
        payload = json.dumps({
            "data": {
                "type": "human" if role == "user" else "ai",
                "content": content
            }
        })
        with engine.begin() as conn:
            conn.execute(sa_text("""
                INSERT INTO chat_history (session_id, message) 
                VALUES (:session_id, :message)
            """), {"session_id": SESSION_UUID, "message": payload})
    except Exception as e:
        print(f"⚠️ [Memory Log Failure]: Could not persist turn to PostgreSQL: {e}")
