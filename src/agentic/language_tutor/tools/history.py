# src/agentic/language_tutor/tools/history.py
from .database_manager import SessionLocal
from sqlalchemy import text

def update_agent_memory(agent_name: str, key: str, value: str) -> str:
    """Saves a specific token of information across agent execution states."""
    session = SessionLocal()
    try:
        query = text("""
            INSERT INTO agent_memory (agent_name, memory_key, memory_value, updated_at)
            VALUES (:name, :key, :val, NOW())
            ON CONFLICT (agent_name, memory_key)
            DO UPDATE SET memory_value = EXCLUDED.memory_value, updated_at = NOW();
        """)
        session.execute(query, {"name": agent_name, "key": key, "val": value})
        session.commit()
        return f"Memory updated: {key} = {value}"
    except Exception as e:
        session.rollback()
        return f"Error updating memory: {str(e)}"
    finally:
        session.close()

def get_shared_memory(key: str) -> str:
    """Retrieves a state token directly from the synchronized schema memory buffer."""
    session = SessionLocal()
    try:
        query = text("SELECT memory_value FROM agent_memory WHERE memory_key = :key ORDER BY updated_at DESC LIMIT 1")
        result = session.execute(query, {"key": key}).fetchone()
        return result[0] if result else "NOT_FOUND"
    finally:
        session.close()
